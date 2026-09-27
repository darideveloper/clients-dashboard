## Why

Sales orders are captured on the public WordPress site ("Ourlens US Order Form V2", Formidable form_id 20), forwarded through n8n, and currently land nowhere — the CRM has all 16 models but no ingestion path, so every order must be re-entered by hand in admin. Today an n8n retry, a Formidable edit, or a mistyped company name produces duplicate/conflicting records, and invitation codes must be imported separately via CSV. This change makes the form data flow automatically into the CRM: webhook endpoint → match-or-create (auto-select existing Organization/Rep/Contact instead of duplicating) → Order/Items/InvitationCodes auto-populated → audited.

## What Changes

- **Dedicated Ourlens webhook endpoint** `POST /webhooks/ourlens/` (csrf_exempt) — a webhook dedicated to Ourlens order submissions that ingests the n8n payload `{token, event, mapping, webhookUrl, executionMode}`. All ingestion logic lives in this one webhook.
- **Shared-secret auth**: validate `body.token` against a new admin-editable `AppSettings.form_webhook_token`; reject with 403 on mismatch.
- **Both environments processed**: submissions are saved and processed regardless of `executionMode` — n8n `production` and `test` (dev/webhook-test) submissions both create/update rows; the mode is recorded on the audit event.
- **Auto-select (match-or-create) instead of duplicate**: Organization matched by normalized address `line1` (lowercase, stripped spaces) and created with `name = line1` when absent; Rep matched by email; Contacts matched by email within the order's org; created when absent.
- **Full payload mapping** to models: Order (order_number stored raw, matched normalized), Rep, Contacts (primary/invoice), OrganizationAddress (split from the flattened combo string, country via alias map, nullable fallback), Order types (pilot/standard), currencies, scan-credits path, pilot product path (region-by-pilot-currency → OrderItem), additional info (HTML stripped).
- **Invitation codes auto-populated** from `code-1..20`: one `InvitationCode` per non-empty code (max_use=1, current_use=0, sequence = slot number N), CodeType from "Up to 5/20 Additional Codes", linked to order + resolved org + the `ourlens` project — which is **always** the project for this webhook; `Order.tokens_used` records the count.
- **Idempotent re-submits**: existing order-number → reconcile core fields and add only missing codes; never deletes codes with real `current_use` history.
- **Token pool relaxation (BREAKING)**: `InvitationCode.clean()/save()` and `AppSettings.clean()` stop hard-rejecting pool over-assignment — availability may go negative (prepaid + negative IOU model). `current_use <= max_use` stays enforced.
- **Schema changes**: `OrganizationAddress.country` becomes nullable; `Order.tokens_used` (PositiveIntegerField default 0); new `FormWebhookEvent` audit model (raw payload, order FK, token/event/executionMode, status, handled_at) with read-only admin.
- **Admin**: expose `tokens_used` and the webhook-token field; audit list read-only, gated like `StripeEvent`.
- **Bruno workspace**: new `bruno/` workspace under the global **Clients Dashboard API** collection (`bruno/collections/clients/`), with an `ourlives-api/` app folder (the only app for now) exercising `POST /webhooks/ourlens/` — the webhook validates `body.token`, so the request sends the token in the JSON body referencing the `{{token}}` env var (`auth: none`, no `Authorization` header, a documented deviation from the vendored guide's DRF Token auth). Ships a `dev.bru.example` env template (`base_url`, webhook `token` with `@description`), a `docs` block on the request per the vendored `docs/django-bruno.md`, and a new `docs/django-bruno.local.md` noting the body-token auth deviation.

## Capabilities

### New Capabilities
- `form-webhook-ingestion`: The dedicated Ourlens webhook `/webhooks/ourlens/` — token auth, payload→model mapping (order number normalization, address split, name split, currency/product/code-type resolution, HTML strip), create-vs-reconcile-on-duplicate, and the `FormWebhookEvent` audit record + `AppSettings.form_webhook_token`. Both `production` and `test`/dev submissions are saved and processed. The `ourlens` project is the fixed default for all code creation in this webhook.
- `crm-auto-match`: Match-or-create auto-selection for Organization (normalized line1), Rep (email), Contacts (email within org), Country (alias map + nullable fallback), Product/Currency/CodeType label resolution — so repeat submissions reuse existing records instead of duplicating.
- `invitation-code-autocreate`: Auto-population of `InvitationCode` rows from `code-1..20` (CodeType by bundle, sequence, max_use=1, current_use=0, project `ourlens` — always this project, order + org links), `Order.tokens_used` population, and add-missing-codes reconcile on re-submit.

### Modified Capabilities
- `invitation-code-validation`: Requirement changes — pool over-assignment validation is relaxed so `total_tokens` availability may go negative; only `current_use <= max_use` remains enforced.
- `crm-orders`: Requirement changes — `Order.tokens_used` field added (default 0) to track auto-created codes per order.
- `crm-phase2-core-models`: Requirement changes — `OrganizationAddress.country` becomes nullable to tolerate unmatched country labels.

## Impact

- **Code**: `ourlives/models.py` (Order.tokens_used, OrganizationAddress.country nullable, FormWebhookEvent, AppSettings.form_webhook_token), `ourlives/views.py` + `urls.py` (new dedicated Ourlens endpoint + admin URLs), new `ourlives/ingestion.py` service, `ourlives/admin.py`, migrations, tests.
- **Fixtures**: new `ourlives/fixtures/ourlives/Project.json` (seeds the `ourlens` project — and `ourplan` — on every fresh environment via `base_loaddata`), so the webhook's fixed `ourlens` project always exists.
- **Config**: `AppSettings.form_webhook_token` must be set before production traffic flows.
- **Dependencies**: none new — stdlib + Django only; reuse existing fixtures (Currency, Product, CodeType, Country) + the new Project fixture.
- **External contract**: n8n workflow already posts the descriptive-key mapping (OL-86..95 format) to the dedicated Ourlens webhook; endpoint must tolerate the flattened combo fields and `"OL - 95"` order-number spacing.
- **Data**: existing `InvitationCode` rows untouched; existing orders with matching order-number get reconciled on next submission.
- **Docs**: extend `ourlives/docs/crm-erd.md`; ship a full Bruno workspace (`bruno/`) — global **Clients Dashboard API** collection with an `ourlives-api/` app folder exercising `/webhooks/ourlens/` in dev — following the vendored blueprint (`docs/django-bruno.md`), plus a new `docs/django-bruno.local.md` documenting the body-token auth deviation.