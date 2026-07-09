## ADDED Requirements

### Requirement: Webhook endpoint accepts Stripe events

The system SHALL expose a POST endpoint at `/stripe/webhook/` that receives Stripe event payloads with CSRF protection disabled, verifies the `Content-Type` is `application/json`, and processes the request body as raw bytes.

#### Scenario: Valid Stripe event received

- **WHEN** Stripe sends a POST to `/stripe/webhook/` with `Content-Type: application/json` and a valid `Stripe-Signature` header
- **THEN** the system verifies the signature, processes the event, and returns HTTP 200

#### Scenario: Invalid signature

- **WHEN** a POST arrives at `/stripe/webhook/` with an invalid `Stripe-Signature` header
- **THEN** the system returns HTTP 400 and does not process the event

#### Scenario: Missing Stripe-Signature header

- **WHEN** a POST arrives at `/stripe/webhook/` without a `Stripe-Signature` header
- **THEN** the system returns HTTP 400 and does not process the event

#### Scenario: Wrong content type

- **WHEN** a POST arrives at `/stripe/webhook/` with a `Content-Type` other than `application/json`
- **THEN** the system returns HTTP 400 without attempting signature verification

### Requirement: Process checkout.session.completed event

The system SHALL extract `source` and `token_count` from the Checkout Session metadata in `checkout.session.completed` events, dispatch to the correct app handler based on `source`, and for ourlives-sourced events increment `AppSettings.total_tokens` atomically.

#### Scenario: Successful token increment for ourlives event

- **WHEN** a `checkout.session.completed` event arrives with metadata `{source: "ourlives", token_count: "100", app_settings_id: "1"}` (string values) and `AppSettings.total_tokens` is `200`
- **THEN** the event is dispatched to the ourlives handler, `AppSettings.total_tokens` becomes `300`, and a `StripeEvent` record is saved with `source="ourlives"` and the stripe event ID

#### Scenario: Unknown source

- **WHEN** a `checkout.session.completed` event arrives with metadata `{source: "unknown_app", token_count: "50"}`
- **THEN** the system returns HTTP 200, logs a warning, and does not process the event

#### Scenario: Unknown event type

- **WHEN** a webhook event arrives with a type other than `checkout.session.completed`
- **THEN** the system returns HTTP 200 without processing (acknowledged but ignored)

### Requirement: Idempotent webhook processing

The system SHALL skip processing of any webhook event whose `stripe_event_id` already exists in the `StripeEvent` model.

#### Scenario: Duplicate event

- **WHEN** a `checkout.session.completed` event arrives whose `id` already exists in `StripeEvent`
- **THEN** the system returns HTTP 200 without modifying `total_tokens` or creating a duplicate record

#### Scenario: First occurrence of event

- **WHEN** a webhook event arrives with a new `id` not in `StripeEvent`
- **THEN** the system processes the event normally and saves a new `StripeEvent` record

### Requirement: Atomic token increment with concurrency control

The system SHALL use `select_for_update()` within a database transaction when incrementing `AppSettings.total_tokens` to prevent race conditions.

#### Scenario: Concurrent webhook deliveries

- **WHEN** two webhook events for different checkout sessions arrive simultaneously
- **THEN** each event's token count is correctly added to `total_tokens` without lost updates

### Requirement: StripeEvent audit model

The system SHALL maintain a `StripeEvent` model recording each processed webhook event with its Stripe event ID, source app, token count, charged amount in cents, and timestamp. Model fields: `stripe_event_id` (`CharField(max_length=255, unique=True)`), `source` (`CharField(max_length=50)`), `token_count` (`PositiveIntegerField`), `amount_cents` (`PositiveIntegerField`, the amount from Stripe's event payload in smallest currency units), `handled_at` (`DateTimeField(auto_now_add=True)`).

#### Scenario: Event recorded

- **WHEN** a checkout completion event is successfully processed
- **THEN** a `StripeEvent` row is created with `stripe_event_id`, `source` from metadata, `token_count` from metadata, and `amount_cents` from the event payload

#### Scenario: Duplicate event ID rejected

- **WHEN** a webhook event is processed whose `stripe_event_id` already exists
- **THEN** the database unique constraint prevents duplicate insertion

### Requirement: StripeEvent read-only admin

The system SHALL expose `StripeEvent` records in the Django admin as a read-only list displaying `stripe_event_id`, `source`, `token_count`, `amount_cents`, and `handled_at`.

#### Scenario: Admin lists StripeEvent records

- **WHEN** an authenticated admin user navigates to the StripeEvent admin list
- **THEN** all processed webhook events are displayed with their stripe event ID, source app, token count, amount in cents, and timestamp

#### Scenario: StripeEvent is read-only

- **WHEN** an admin user views a StripeEvent detail or change form
- **THEN** all fields are read-only; the admin cannot create, edit, or delete StripeEvent records

### Requirement: Purchase view access control

The system SHALL enforce that the purchase view (`purchase_view`) and the `/stripe/create-checkout/` endpoint are only accessible to staff users with `has_module_perms("ourlives")`.

#### Scenario: ourlives user accesses purchase view

- **WHEN** a staff user with `ourlives.view_project` permission navigates to `/admin/ourlives/appsettings/purchase/`
- **THEN** the purchase page renders successfully

#### Scenario: non-ourlives user denied

- **WHEN** a staff user with zero ourlives permissions attempts to access `/admin/ourlives/appsettings/purchase/`
- **THEN** the system returns HTTP 403

#### Scenario: ourlives user submits checkout

- **WHEN** a staff user with ourlives permissions POSTs to `/stripe/create-checkout/` with a valid amount
- **THEN** the checkout session is created and the user is redirected to Stripe

#### Scenario: non-ourlives user submits checkout

- **WHEN** a user without ourlives permissions POSTs to `/stripe/create-checkout/`
- **THEN** the system returns HTTP 403

### Requirement: Source-based webhook dispatch

The system SHALL use a `source` field in Checkout Session metadata to route webhook events to the correct app handler, enabling future apps to share the same Stripe account and webhook endpoint without cross-app coupling.

#### Scenario: Event dispatched to correct handler

- **WHEN** a checkout completion event has metadata `source: "ourlives"`
- **THEN** the ourlives handler processes the event and increments `AppSettings.total_tokens`

#### Scenario: Future app event would be dispatched

- **WHEN** a checkout completion event has metadata `source: "future_app"`
- **THEN** the webhook recognizes no handler is registered, logs a warning, and returns HTTP 200 without error

#### Scenario: Missing source metadata

- **WHEN** a checkout completion event has no `source` in metadata
- **THEN** the webhook returns HTTP 200, logs a warning, and does not process the event
