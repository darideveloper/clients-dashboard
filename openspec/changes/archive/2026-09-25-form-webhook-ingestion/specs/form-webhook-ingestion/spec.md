## ADDED Requirements

### Requirement: Dedicated Ourlens webhook endpoint
The system SHALL expose a dedicated webhook for Ourlens at `POST /webhooks/ourlens/` (csrf_exempt, POST-only) that accepts the n8n payload `{token, event, mapping, webhookUrl, executionMode}` and ingests a valid submission. All Ourlens form ingestion SHALL go through this one endpoint. The request body SHALL be parsed as JSON; a non-JSON or wrong-content-type body SHALL return 400.

#### Scenario: Valid production submission is ingested
- **WHEN** n8n POSTs a JSON body with `executionMode="production"` and a valid `token` to `/webhooks/ourlens/`
- **THEN** the system returns 200, creates/updates the Order and related rows, and records a `FormWebhookEvent` with status `created` or `updated`

#### Scenario: Wrong content type is rejected
- **WHEN** a request with `content-type: text/plain` (or unparsable JSON) hits the endpoint
- **THEN** the system returns 400 and creates no rows

#### Scenario: Empty or missing mapping is rejected
- **WHEN** the payload has no `mapping` object (or it is empty)
- **THEN** the system records the event with status `rejected` and returns 200 without creating rows (n8n does not retry)

### Requirement: Shared-secret token authentication
The system SHALL validate `body.token` against `AppSettings.form_webhook_token` before any processing. A missing or mismatched token SHALL be rejected.

#### Scenario: Valid token proceeds
- **WHEN** `body.token` equals `AppSettings.form_webhook_token`
- **THEN** the request proceeds to ingestion

#### Scenario: Missing or wrong token rejected
- **WHEN** `body.token` is missing or does not match the configured secret
- **THEN** the system returns 403 Forbidden and creates no rows

#### Scenario: Token comparison is timing-safe
- **WHEN** the token is compared
- **THEN** the comparison uses a constant-time comparison (e.g. `secrets.compare_digest`)

### Requirement: Both production and test/dev submissions are processed
The system SHALL save and process submissions regardless of `executionMode`. `production` and `test` (dev / n8n `webhook-test`) submissions both create/update rows, and the mode SHALL be recorded on the `FormWebhookEvent` for provenance.

#### Scenario: Test execution mode is ingested
- **WHEN** a valid token is sent with `executionMode="test"`
- **THEN** the system returns 200 and creates/updates Order, Rep, Contact, Address, Items, and Codes exactly as a production submission would, recording `execution_mode="test"` on the audit row

#### Scenario: Missing execution mode is still ingested
- **WHEN** a valid token is sent with no `executionMode` field
- **THEN** the system still processes the submission and records the mode as unknown/empty on the audit row

### Requirement: Order number stored raw and matched normalized
The system SHALL store `Order.order_number` exactly as submitted and detect duplicate orders by a normalized form of the number (whitespace collapsed around the dash, e.g. `"OL - 95"` and `"OL-95"` match).

#### Scenario: Order created from submission
- **WHEN** a new order-number is submitted
- **THEN** an Order is created with `order_number` stored verbatim

#### Scenario: Duplicate order-number reconciles instead of duplicating
- **WHEN** an order-number matching an existing order (normalized) is re-submitted
- **THEN** the existing Order is updated (reconciled) and no duplicate Order is created

### Requirement: Order fields populated from mapping
The system SHALL populate the Order from the mapping: `po_number`, `number_of_scans`, `cost_per_scan`, `is_upgrade_from_pilot`, `is_referral_order`, `referral_organisation`, `currency` (non-pilot) or `pilot_currency` (pilot), `order_types` (pilot/standard), and `additional_information` (stripped of HTML tags).

#### Scenario: Non-pilot order fields set
- **WHEN** a submission has `is-this-a-pilot-order="No"`, `currency="GBP"`, `po-number`, `number-of-scans`, `cost-per-scan`, and additional info with HTML
- **THEN** the Order stores those values, `order_types` contains `standard`, and `additional_information` contains the stripped text

#### Scenario: Pilot order fields set
- **WHEN** a submission has `is-this-a-pilot-order="Yes"` and `pilot-currency="GBP"`
- **THEN** the Order stores `pilot_currency`, `order_types` contains `pilot`, and scans/cost stay null

#### Scenario: Blank or missing pilot radio defaults to standard
- **WHEN** a submission omits or blanks `is-this-a-pilot-order` (with `currency` and scans/cost present)
- **THEN** the Order stores `order_types` containing `standard`

#### Scenario: Upgrade from pilot does not force pilot type
- **WHEN** a submission has `is-this-an-upgrade-from-a-pilot="Yes"` but `is-this-a-pilot-order="No"`
- **THEN** the Order stores `is_upgrade_from_pilot=True` and `order_types` containing `standard`

#### Scenario: Upgrade and referral flags
- **WHEN** a submission has `is-this-an-upgrade-from-a-pilot="Yes"` and `is-this-an-order-following-a-referral="Yes"` with a referring organization name
- **THEN** the Order stores `is_upgrade_from_pilot=True`, `is_referral_order=True`, and the referral name

### Requirement: Pilot product items built by region
The system SHALL build OrderItem(s) for pilot orders from the region block matching `pilot_currency` (US→USD, Canada→CAD, UK→GBP, South Africa→ZAR): product looked up by `<Region> <Tier> Pilot` name, quantity and unit_price from the region's fields.

#### Scenario: UK pilot item created
- **WHEN** a pilot order has `pilot-currency="GBP"`, `product-uk="Micro Pilot"`, `quantity-uk="1"`, `gbp="995"`
- **THEN** one OrderItem is created with product `UK Micro Pilot`, quantity 1, unit_price 995.00, linked to the Order

#### Scenario: Region block chosen by pilot currency
- **WHEN** `pilot-currency="USD"` but the UK block is also filled
- **THEN** the item is built from the USD block only

#### Scenario: EUR pilot has no product block
- **WHEN** `pilot-currency="EUR"` (allowed by the form) and no region block is filled
- **THEN** the Order is created with no OrderItem and no scans/cost (zero price), and the audit event records that the product was unresolved

### Requirement: FormWebhookEvent audit record
The system SHALL record a `FormWebhookEvent` for every accepted request: `payload` (raw JSON), `order` (FK, nullable), `token`, `event`, `execution_mode`, `status` (`rejected`|`created`|`updated`|`error`), and `handled_at`.

#### Scenario: Successful ingestion creates audit row
- **WHEN** a submission (production or test) creates an order
- **THEN** a `FormWebhookEvent` is created with the raw payload, the order FK, the execution mode, and status `created`

#### Scenario: Error status on processing failure
- **WHEN** ingestion raises an unhandled error after token validation
- **THEN** the system records a `FormWebhookEvent` with status `error` and returns 500, leaving no partial audit ambiguity

#### Scenario: Audit rows are read-only in admin
- **WHEN** a staff user views `FormWebhookEvent` in admin
- **THEN** the records are visible but cannot be added, changed, or deleted

### Requirement: Admin exposes webhook configuration
The system SHALL expose `AppSettings.form_webhook_token` in the admin `AppSettings` change form.

#### Scenario: Token visible and editable by superuser
- **WHEN** a superuser opens the AppSettings admin
- **THEN** the webhook token field is shown and editable

### Requirement: Bruno workspace ships a request for the webhook
The system SHALL ship a git-native Bruno workspace (`bruno/`) with a global **Clients Dashboard API** collection containing an `ourlives-api/` app folder with a `Webhooks/POST form.bru` request for `POST /webhooks/ourlens/`. The request SHALL set `auth: none`, send the token in the JSON body via the `{{token}}` environment variable (never a hard-coded literal), include a request sample payload, and carry a `docs` block documenting the expected status codes (`200` created/updated with no response body, `403` bad token, `400` wrong content-type) and the body-token auth (not an `Authorization` header). The real environment file (`dev.bru`) SHALL be gitignored while the `dev.bru.example` template (with `base_url` and `token` vars, each with `@description`) is tracked.

#### Scenario: Workspace and collection layout created
- **WHEN** a fresh checkout runs the change's migration and deploy steps
- **THEN** `bruno/workspace.yml`, `bruno/collections/clients/bruno.json` (name "Clients Dashboard API"), and `bruno/collections/clients/ourlives-api/Webhooks/POST form.bru` exist

#### Scenario: Token sent in body, not hard-coded
- **WHEN** the `POST form.bru` request is inspected
- **THEN** the `post` block has `body: json` and `auth: none`, and the `body:json` block contains `"token": "{{token}}"` referencing the environment (no literal token, no `Authorization` header)

#### Scenario: Docs block lists webhook status codes
- **WHEN** a developer opens the `POST form.bru` request
- **THEN** its `docs` block notes the body-token auth and lists `200` (created/updated, empty body), `403` (bad token), and `400` (wrong content-type) with a request sample

#### Scenario: Real environment is gitignored, template tracked
- **WHEN** the repository is inspected
- **THEN** `dev.bru` is excluded by `.gitignore` (`bruno/collections/*/environments/*.bru`) and `dev.bru.example` is tracked (`!.../*.bru.example`)