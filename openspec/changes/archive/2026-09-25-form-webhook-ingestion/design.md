## Context

Sales orders come from a public WordPress Formidable form ("Ourlens US Order Form V2", form_id 20) and are forwarded by n8n as a JSON POST. The Django app (`ourlives`) already has the full CRM schema (16 models, fixtures for Country/Currency/Product/CodeType/OrderType/ContactType) but **no ingestion path** — orders today are hand-entered in admin, and invitation codes are imported separately via CSV. The n8n payload uses 55 descriptive keys (verified against the live form field-by-field), with several flattened fields that must be un-flattened (address combo, name combos, order-number spacing, `code-1..20`).

Existing patterns to reuse: the Stripe webhook (`ourlives/views.py` `webhook`, csrf_exempt, read-only audit `StripeEvent`), the CSV import command (`import_invitation_codes` — token-pool bump logic), and the `ourlens` Project as the fixed code project (currently a manual DB row, moved to a `Project.json` fixture in this change — see D8a).

## Goals / Non-Goals

**Goals:**
- Auto-populate the CRM from form submissions: Order, Rep, Contacts, OrganizationAddress, OrderItem(s), InvitationCode(s) — with auto-select (match existing records) instead of blind duplication.
- Idempotent re-submits: same order-number reconciles the order and adds only missing codes.
- Token pool decoupled from order creation: availability may go negative (prepaid + negative IOU); `tokens_used` recorded per order.
- Full audit trail of raw payloads + processing status.
- Auth via shared secret (`body.token`); submissions are processed regardless of `executionMode` — both `production` and `test`/dev n8n webhooks create/update rows, with the mode recorded on the audit event.

**Non-Goals:**
- No new external dependencies; no Stripe billing changes (charges still via existing admin purchase flow).
- No support for the legacy raw-field-ID payload format (OL-85) — descriptive keys (OL-86+) are the contract.
- No form `update`-event rebuilds: reconcile never deletes codes/items wholesale (preserves `current_use` history).
- No automatic Stripe invoicing / metered billing (model A = prepaid + negative IOU).
- No expansion of the `Country` fixture — unknown labels are tolerated via nullable fallback.
- Out of scope: `submitted_at` (uses webhook receipt time), `ip_address` (n8n's IP, not submitter's — left null), `hcaptcha_verified` (result not forwarded — stays False), `form_entry_key` (payload carries no Formidable entry key — stays null).

## Decisions

### D1. Endpoint shape and flow
`POST /webhooks/ourlens/` under a new `webhooks/` mount (separate from `/stripe/`) — a webhook dedicated to Ourlens order submissions. csrf_exempt + `require_POST`. Flow: content-type check → parse body → validate `body.token` (403 on mismatch) → `ingest(mapping)` (both `production` and `test`/dev modes processed; mode passed through) → `FormWebhookEvent` audit row → 200.

Rationale: mirrors the Stripe webhook's defensive style; keeps Stripe and form concerns separate. Alternative (reusing `/stripe/webhook/`) rejected — it's signature-bound to Stripe semantics.

### D2. Auth: `AppSettings.form_webhook_token`
New admin-editable singleton field, compared against `body.token` with `secrets.compare_digest`. Rationale: admin-rotatable without redeploy, matches existing settings pattern. Alternatives considered: env var (rotation = redeploy), hard-coded sample token (insecure — it's in every sample payload).

### D3. Order-number: store raw, match normalized
Store exactly as submitted (`OL - 95`); for existence matching, compare with a normalized form (collapse whitespace around `-`: `OL-95`). Rationale: preserves what the sales team sees while making retries idempotent. `Order.order_number` stays unique on the raw value.

### D4. Match-or-create (auto-select) rules
- **Organization**: `name = address line1`; lookup key = `normalize(line1)` (lowercase, strip all whitespace). Existing → reuse; else create.
- **Rep**: match by unique `email`; missing → create, splitting the single name field on the **first space** (`"Demo Harry Judd"` → first=`Demo`, last=`Harry Judd`).
- **Contact**: match by email within the order's resolved org; missing → create. `ContactType` from context: primary block → `primary`, invoice block → `invoice`.
- **Country**: normalize label (lowercase, strip punctuation); exact match first, then an alias map for the form→fixture label gaps (verified against `Country.json`): Vatican City→Holy See, East Timor→Timor-Leste, Brunei→Brunei Darussalam, Swaziland→Eswatini, Macedonia→North Macedonia, Moldova→Moldova, Republic of, Côte d'Ivoire→Cote d'Ivoire, Cape Verde→Cabo Verde, Czech Republic→Czechia, Laos→Lao People's Democratic Republic, Micronesia→Micronesia, Federated States of, North Korea→Korea, Democratic People's Republic of, Palestine→Palestine, State of, Russia→Russian Federation, South Korea→Korea, Republic of, Syria→Syrian Arab Republic, Taiwan→Taiwan, Province of China, Tanzania→Tanzania, United Republic of, Vietnam→Viet Nam. Labels matching neither a fixture name nor an alias (e.g. Kosovo — not in fixture) → country `None` + audit flag.
- **Currency**: by `code` (USD/CAD/GBP/EUR/ZAR) for `Order.currency` (non-pilot) / `pilot_currency` (pilot).
- **Product** (pilot): pick the region block whose currency matches `pilot_currency` (US→USD, Canada→CAD, UK→GBP, South Africa→ZAR); Product name = `<Region> <Tier> Pilot` (e.g. `product-uk="Micro Pilot"` → `UK Micro Pilot`); `quantity` + `unit_price` (from the region's price field `gbp`/`us-dollars`/…) → one `OrderItem`.
- **CodeType**: by name from `how-many-additional-codes-do-you-require` (`Up to 5 Additional Codes` → `up_to_5`, `Up to 20 Additional Codes` → `up_to_20`).

Rationale: email/name-keyed lookups are the most stable natural keys available; normalization (lowercase/strip) makes "auto-select instead of create" robust to typos/case. Alternative (create-on-every-submission) rejected — defeats dedup.

### D5. Order type mapping
`is-this-a-pilot-order`: Yes → `order_types=[pilot]`; No → `[standard]`; blank/missing → treated as No → `[standard]` (key-tolerance: blanks are absent, and every order gets a defined type). `is-this-an-upgrade-from-a-pilot` → `is_upgrade_from_pilot` (does **not** force `[pilot]` — an upgrade order is a standard order with the flag set, as seen in OL-87); referral → `is_referral_order` + `referral_organisation`; `you-have-selected-yes-to-an-upgrade-from-a-pilot` is display-only info (ignored).

### D6. Pilot vs non-pilot price paths
- **Pilot=Yes**: region block by `pilot_currency` → OrderItem(s); `Order.pilot_currency` set; scans/cost stay null.
- **Pilot=No**: `Order.currency`, `number_of_scans`, `cost_per_scan`; no items. `total-agreed-price` ignored (computed property = scans × cost).
- **EUR pilot (no product block)**: the form's `pilot-currency` allows EUR, but no EUR region block exists (verified: form conditionals offer product selects only for USD/CAD/GBP/ZAR). A EUR pilot therefore produces **no OrderItem and no scans/cost** — the order is created with zero price, and the audit event records an `unresolved_product` flag so sales can price it later in admin. Rationale: dropping the submission would lose a real form entry; this keeps the order while flagging the gap.
Rationale: the form keeps these mutually exclusive (verified across all sample payloads); hybrid support would be dead code.

### D7. Address reconstruction
Split the flattened combo string on `, `. Parse from the right: last segment = country label, then zip, state, city; remaining left segments = `line1` (first) + `line2` (rest, joined). Tolerates 5-part addresses (empty line2). `line1` also seeds `Organization.name`. Rationale: `country` is always the trailing select value, so right-anchored parsing is robust.

### D8. Invitation code auto-population
For each non-empty `code-N` (regardless of the additional-codes toggle): create `InvitationCode(project=ourlens, organization=<resolved org>, order=<order>, code_type=<from bundle>, sequence=N, is_active=True, max_use=1, current_use=0)`. `sequence` is the form's slot number `N` (e.g. `code-16` → 16), preserving gaps like the missing `code-15` seen in OL-89. `Order.tokens_used` = count of codes created on this submission (accumulates on reconcile). Rationale: 1 code = 1 token (business rule), codes are always created so orders never fail for want of pool.

### D8a. The `ourlens` project is fixed and guaranteed (Option A)
This webhook is **dedicated to Ourlens**, so the code project is always `ourlens` — never parameterized, never user-chosen. To guarantee the row exists on every environment, a new `ourlives/fixtures/ourlives/Project.json` fixture seeds `ourlens` (and `ourplan`) via the existing `base_loaddata` path, so a fresh `migrate` + `base_loaddata` deploy has it without manual entry. Fixture uses explicit PKs (`ourlens`=1, `ourplan`=2) matching the live DB rows, so `loaddata` upserts idempotently. Rationale: hard-coding a name is only safe when the row is guaranteed; the fixture removes the current live-DB-manual-row dependency. Alternatives rejected: `AppSettings.default_code_project` FK (no multi-project routing today — YAGNI) and `get_or_create("ourlens")` at ingest (silently invents data).

### D9. Token pool relaxation (negative availability)
`InvitationCode.clean()/save()` and `AppSettings.clean()` drop the over-assignment rejection (`sum(max_use) <= total_tokens`). `current_use <= max_use` stays. Admin shows negative `tokens_available` in red. Rationale: order-creation decoupled from pool funding (prepaid + negative IOU). Alternative (auto-bump pool on webhook) rejected — would silently give away unpaid tokens.

### D10. Idempotency / reconcile-on-duplicate
On existing order-number: refresh core Order fields (org, rep, contacts, currency, scans/cost, flags, items — items replaced to match payload), then **add only missing** InvitationCodes (matched by code value); existing codes untouched. Never delete codes. Rationale: preserves real `current_use` history while converging on the latest submission.

### D11. Audit model `FormWebhookEvent`
Fields: `payload` (JSONField raw body), `order` (FK, null), `token`, `event`, `execution_mode`, `status` (rejected|created|updated|error), `handled_at`. Read-only admin gated like `StripeEvent` (no add/change/delete). Rationale: mirrors the existing Stripe audit pattern; gives debugging power over payloads.

### D12. Both production and test/dev submissions are processed
`executionMode` is **not** a gate: `production` and `test` (dev / n8n `webhook-test`) submissions are both saved and processed. The mode is recorded on the `FormWebhookEvent` (`execution_mode`) so test data remains distinguishable in the audit trail. Rationale: the client wants dev/test submissions to flow through the same pipeline end-to-end so the CRM reflects all form activity; `execution_mode` preserves provenance instead of discarding it.

### D13. HTML strip for `additional_information`
Strip tags (the form sends `<p>…</p>`) — stdlib `html` module, no dependency.

### D14. Bruno workspace (full integration)
Ship a git-native Bruno workspace so `/webhooks/ourlens/` is manually exercisable in dev, following the vendored blueprint `docs/django-bruno.md` (§2–5) and the reference project (`enredarte-dashboard/bruno/`). The workspace hosts a **global collection for the `clients` project** — named **Clients Dashboard API** — with a folder per app; `ourlives-api` is the only folder for now, and other apps (`core`, …) join later as endpoints appear:

```
bruno/
├── workspace.yml                                  # REQUIRED — opencollection 1.0.0
└── collections/clients/                           # global collection dir for the clients project
    ├── bruno.json                                 # version "1", name "Clients Dashboard API"
    ├── environments/dev.bru.example               # tracked template; real dev.bru gitignored
    └── ourlives-api/                              # app folder (the only one for now)
        └── Webhooks/
            └── POST form.bru                      # request + mandatory docs block
```

- **Workspace/collection naming**: workspace info `Clients Dashboard`, collection dir `clients` (`path: collections/clients`), collection `name` `Clients Dashboard API` (matches the repo `clients-dashboard`), app folder `ourlives-api` (other apps join later — YAGNI now).
- **Environment vars** (`dev.bru.example`): `base_url` = `https://clients-feature-ourlives-webhook.localhost` (portless subdomain from this repo dir name; fallback `http://localhost:8000` noted), `token` = webhook-token placeholder (`<paste-token-here>`). Each var carries a `@description('''…''')` per the blueprint §5. The real `dev.bru` holds a live token and is never committed.
- **Auth deviation from the blueprint**: the vendored guide's examples use `Authorization: Token {{token}}` (DRF). This webhook validates `body.token` instead — so the request uses `post { body: json }` with the token **inside the JSON body** (`"token": "{{token}}"`, referencing the env var — never a hard-coded literal, per §9), `auth: none`, and no `Authorization` header. Document this in the request's `docs` block and in a new `docs/django-bruno.local.md`.
- **`.gitignore`**: the rule `bruno/collections/*/environments/*.bru` + `!bruno/collections/*/environments/*.bru.example` (mirrors the reference project `:22-23` and is already present at `.gitignore:51-52`) keeps real tokens out of git while the template ships. Verify it exists; add only if absent.
- **`docs` block**: every `.bru` request carries expected status codes (`200` created/updated — with **no response body**; `403` bad token; `400` wrong content-type) and a **request** sample payload, per the blueprint §6.4. There is no serializer, so no fabricated response JSON — the 200 response is empty.

Rationale: the blueprint's workspace layout is the established convention in sibling projects; a workspace (not a bare collection) is required to open in Bruno 3.0+; a single global `clients` collection with per-app folders matches how the `clients` project aggregates apps, and keeps real tokens out of git. Alternatives rejected: a dedicated `ourlives-api` collection (diverges from the global `clients` collection convention), single bare `.bru` file (cannot be opened as a workspace; violates the vendored guide), and no Bruno at all (loses the manual dev workflow; we already vendored the docs).

## Risks / Trade-offs

- [Address split misparses free-text with commas in line1/line2] → Mitigation: right-anchored parse anchored on the trailing country select value; the audit log preserves the raw string for manual recovery.
- [Country label unmatchable → nullable country] → Mitigation: alias map covers known gaps; nullable fallback means the address is still saved; admin can patch country later.
- [Negative pool can grow unbounded] → Mitigation: `tokens_used` per order + red negative balance in admin = the "IOU" surface; charging remains manual/prepaid.
- [Reconcile could overwrite intentional admin edits (org/contacts)] → Mitigation: reconcile only applies values present in the payload; codes/items are additive; admin edits to order flags not in the form (e.g. billing flags) are untouched.
- [Product lookup misses (name drift between fixture and form)] → Mitigation: name = `<Region> <Tier> Pilot` derived from the form's own values; on no-match (incl. the EUR pilot case with no block), log to audit and skip the item rather than crash the order; the order is created zero-price and flagged for manual pricing.
- [FormWebhookEvent persists the shared-secret `body.token`] → Mitigation: audit rows are read-only, admin-only (same trust boundary as `AppSettings` itself); the token field is stored verbatim for traceability but never exposed outside admin. If this becomes a concern, rotate via `AppSettings.form_webhook_token`.
- [n8n contract changes (new/renamed keys)] → Mitigation: ingestion is key-tolerant (missing/unknown keys ignored, blanks treated as absent); unknown keys logged.

## Migration Plan

1. Add migrations: `Order.tokens_used`, `OrganizationAddress.country` nullable, `AppSettings.form_webhook_token`, `FormWebhookEvent`.
2. Add `ourlives/fixtures/ourlives/Project.json` (ourlens + ourplan); `base_loaddata` seeds it on the next deploy (upserts by PK — idempotent).
3. Deploy code + `migrate`; set `AppSettings.form_webhook_token` in admin **before** pointing n8n at production.
4. n8n config: point the workflow at `https://<host>/webhooks/ourlens/` (keep the existing descriptive-key mapping).
5. Smoke test: replay a sample OL-9x payload via curl → verify Order/Org/Contact/Address/Item/Codes + audit row; re-POST same payload → verify reconcile adds nothing.
6. Rollback: revert code + migration (data-safe: `tokens_used`/`country null`/audit rows are additive); remove the fixture file; point n8n back to the old target (none) — no data-loss path.

## Open Questions

1. Confirm `Contact` matching scope: email-within-resolved-org only (current) vs email-global.