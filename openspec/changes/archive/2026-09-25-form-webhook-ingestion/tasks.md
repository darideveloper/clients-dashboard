## 1. Model & migration changes

- [x] 1.1 Add `Order.tokens_used` (PositiveIntegerField default 0) with help text
- [x] 1.2 Make `OrganizationAddress.country` nullable (null=True, blank=True)
- [x] 1.3 Add `AppSettings.form_webhook_token` (CharField blank, help text) with admin exposure in `AppSettingsAdmin` fieldsets
- [x] 1.4 Add `FormWebhookEvent` model: `payload` JSONField, `order` FK (null, SET_NULL, related_name `form_webhook_events`), `token` CharField, `event` CharField, `execution_mode` CharField, `status` CharField with choices (rejected/created/updated/error), `handled_at` DateTimeField auto_now_add, `__str__`
- [x] 1.5 Relax token pool validation: remove over-assignment rejection from `InvitationCode.clean()` and `save()` (keep `current_use <= max_use`)
- [x] 1.6 Relax `AppSettings.clean()` so `total_tokens` may be reduced below `tokens_assigned` (negative availability allowed)
- [x] 1.7 Generate and apply migration(s) for the four model changes
- [x] 1.8 Add `ourlives/fixtures/ourlives/Project.json` with explicit PKs (`ourlens`=1, `ourplan`=2) matching the live DB, loadable by `base_loaddata` on fresh environments (idempotent upsert)
- [x] 1.9 Update `ourlives/docs/crm-erd.md` with the new/changed fields (tokens_used, country nullable, form_webhook_token, FormWebhookEvent)

## 2. Ingestion service

- [x] 2.1 Create `ourlives/ingestion.py` with a normalization module: `normalize_order_number` (collapse whitespace around dashes), `normalize_name` (lowercase + strip whitespace), `split_full_name` (first space = split point)
- [x] 2.2 Implement address parsing: `split_address(raw)` returning line1/line2/city/state/zip/country via right-anchored comma split (5- or 6-part tolerant)
- [x] 2.3 Implement country resolution: `resolve_country(label)` — normalized exact match, then alias map (Vatican City→Holy See, East Timor→Timor-Leste, Brunei→Brunei Darussalam, Swaziland→Eswatini, Macedonia→North Macedonia, Moldova→Moldova, Republic of, Côte d'Ivoire→Cote d'Ivoire, Cape Verde→Cabo Verde, Czech Republic→Czechia, Laos→Lao People's Democratic Republic, Micronesia→Micronesia, Federated States of, North Korea→Korea, Democratic People's Republic of, Palestine→Palestine, State of, Russia→Russian Federation, South Korea→Korea, Republic of, Syria→Syrian Arab Republic, Taiwan→Taiwan, Province of China, Tanzania→Tanzania, United Republic of, Vietnam→Viet Nam), returns Country or None
- [x] 2.4 Implement lookups: `resolve_currency(code)`, `resolve_product(region, tier)`, `resolve_code_type(bundle_name)` (Up to 5→up_to_5, Up to 20→up_to_20), default project lookup (`ourlens`)
- [x] 2.5 Implement match-or-create: `get_or_create_org(line1)` (normalized line1 match), `get_or_create_rep(email, name)`, `get_or_create_contact(org, email, name, phone, contact_type_code)`
- [x] 2.6 Implement `ingest(mapping)` orchestrator: build/update Order (raw order_number stored, normalized match for duplicates), set order_types (pilot/standard), flags, currency/pilot_currency, scans/cost vs pilot items, additional_information HTML strip
- [x] 2.7 Implement pilot items: region block selected by `pilot_currency`, create/replace OrderItems (product lookup, quantity, unit_price from region price field)
- [x] 2.8 Implement invitation-code auto-creation: for each non-empty code-N create InvitationCode (max_use=1, current_use=0, sequence = slot number N, code_type, order, org, project ourlens), add-only reconcile for existing order, accumulate `Order.tokens_used`
- [x] 2.9 Reconcile behavior: on existing order, refresh core fields + replace items + add only missing codes (never delete codes)
- [x] 2.10 Keep ingestion tolerant: missing/unknown keys ignored, blanks treated as absent, unresolved product logged without crashing the order

## 3. Webhook endpoint & audit

- [x] 3.1 Add `webhooks/` URL mount in `project/urls.py` and a dedicated Ourlens webhook URL pointing at `POST /webhooks/ourlens/`
- [x] 3.2 Implement `form_webhook` view: csrf_exempt + require_POST, JSON content-type check (400 otherwise), parse body, validate `body.token` vs `AppSettings.form_webhook_token` with `secrets.compare_digest` (403 on mismatch)
- [x] 3.3 Process submissions for both `production` and `test`/dev execution modes (record `execution_mode` on the audit row; no mode-based skipping)
- [x] 3.4 Call `ingest(mapping)` inside a transaction; record `FormWebhookEvent` (created/updated/rejected/error) with raw payload + order FK + metadata
- [x] 3.5 Handle processing exceptions: record status `error`, return 500, no partial writes
- [x] 3.6 Register `FormWebhookEvent` in admin: read-only (no add/change/delete), list filters on status/execution_mode, search on token/order number

## 4. Tests

- [x] 4.1 Tests for normalization/splitting helpers (order-number, name, address 5/6-part)
- [x] 4.2 Tests for match-or-create (org by normalized line1, rep/contact by email, create-when-missing)
- [x] 4.3 Tests for country alias map + nullable fallback
- [x] 4.4 Endpoint tests: 200 production create, 200 test/dev create, 403 bad token, 400 wrong content-type, execution_mode recorded on audit, duplicate order-number reconciles (no duplicate, no code loss)
- [x] 4.5 Invitation-code tests: auto-creation (max_use=1, sequence = slot number incl. a gap like OL-89's missing code-15, code_type, project always `ourlens` from fixture), add-only reconcile, tokens_used accumulation, creation succeeds when pool exhausted
- [x] 4.6 Pilot vs non-pilot order tests (region-by-pilot-currency items; scans/cost path; total-agreed-price ignored; blank pilot radio → standard; upgrade=Yes + pilot=No → standard with flag)
- [x] 4.7 Test that a fresh `base_loaddata` yields the `ourlens` project and codes link to it
- [x] 4.8 Admin tests: FormWebhookEvent read-only, AppSettings token field visible, tokens_used exposed

## 5. Docs & integration

- [x] 5.1 Document the n8n contract and endpoint in the repo (endpoint path, auth, executionMode, mapping keys, sample payload)
- [x] 5.2 Create `bruno/workspace.yml` (opencollection 1.0.0, workspace info `Clients Dashboard`, global collection `collections/clients`)
- [x] 5.3 Create `bruno/collections/clients/bruno.json` (version "1", name "Clients Dashboard API")
- [x] 5.4 Create `bruno/collections/clients/environments/dev.bru.example` (`base_url` = portless subdomain `https://clients-feature-ourlives-webhook.localhost`, `token` placeholder, each var with `@description`), confirming the `.gitignore` rule `bruno/collections/*/environments/*.bru` + `!.../*.bru.example` already exists at `.gitignore:51-52` (add only if absent)
- [x] 5.5 Create `bruno/collections/clients/ourlives-api/Webhooks/POST form.bru` — token in the JSON body via `"token": "{{token}}"` (`auth: none`, no Authorization header, no hard-coded token), request sample payload, and a `docs` block (200 with no response body / 403 bad token / 400 wrong content-type + request sample) per the vendored guide §6.4
- [x] 5.6 Create `docs/django-bruno.local.md` noting this webhook deviates from DRF Token auth — it validates `body.token` inside the JSON body instead of an `Authorization` header — and describing the global `clients` collection layout
- [x] 5.7 Verify no secrets committed (grep docs/ + bruno/ for sk_live/SECRET_KEY/PASSWORD/token placeholders) and `pull.sh --check` remains consistent if run