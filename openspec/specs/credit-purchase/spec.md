# credit-purchase Specification

## Purpose
TBD - created by archiving change stripe-decimal-multi-currency. Update Purpose after archive.
## Requirements
### Requirement: Decimal precision throughout purchase pipeline

The system SHALL parse all monetary user input directly as `Decimal` from the raw string (not `float`). All arithmetic on monetary values SHALL use `Decimal`. The `float` → `str` → `Decimal` round-trip SHALL be eliminated.

#### Scenario: Decimal parsing from POST data
- **WHEN** a user submits `amount=10.99` in a POST request
- **THEN** the system SHALL parse it as `Decimal("10.99")` without intermediate float conversion

#### Scenario: Decimal comparison against minimum purchase
- **WHEN** comparing user amount against `min_purchase_amount`
- **THEN** both values SHALL be compared as `Decimal` instances, not floats

#### Scenario: Token count calculation receives Decimal
- **WHEN** calling `calculate_token_count(amount, price_per_token)`
- **THEN** `amount` SHALL be a `Decimal` (not float)
- **THEN** the function SHALL return the correct floor division result without float precision errors

#### Scenario: No float arithmetic in Stripe boundary
- **WHEN** creating a Stripe Checkout Session
- **THEN** the system SHALL convert per-token price to cents via `int(Decimal price_per_token * 100)` — safe `ROUND_DOWN` with no float

### Requirement: Inline price_data checkout with adaptive pricing

The system SHALL use inline `price_data` with `currency="usd"`, `unit_amount` (per-token price in cents), and `quantity` (token count) for Checkout Sessions. The Checkout Session SHALL enable `adaptive_pricing={"enabled": True}` so Stripe auto-detects the customer's local currency and converts at Stripe's market rate. `payment_method_types` SHALL be set to `["card"]`. `customer_email` SHALL be passed when the user has an email address.

#### Scenario: Checkout session using price_data
- **WHEN** creating a checkout session for 20 tokens with per-token price $0.10
- **THEN** the session SHALL use `line_items[0].price_data.currency = "usd"`
- **THEN** the session SHALL use `line_items[0].price_data.unit_amount = 10` (10 cents per token)
- **THEN** the session SHALL use `line_items[0].quantity = 20`
- **THEN** `payment_method_types` SHALL be `["card"]`

#### Scenario: Adaptive pricing enabled on session
- **WHEN** creating a Checkout Session
- **THEN** `adaptive_pricing` SHALL be set to `{"enabled": True}`

#### Scenario: Customer email passed when available
- **WHEN** the authenticated user has a non-empty email address
- **THEN** the session SHALL include `customer_email` set to the user's email

#### Scenario: Customer email omitted when empty
- **WHEN** the authenticated user has no email address
- **THEN** the session SHALL NOT include `customer_email`

#### Scenario: Auto-detected currency from customer locale
- **WHEN** a customer from Germany accesses the Checkout Session
- **THEN** Stripe SHALL present the total in EUR using Stripe's market conversion rate
- **THEN** the webhook SHALL include `presentment_details.presentment_currency = "eur"` and `presentment_details.presentment_amount`

#### Scenario: Fallback to USD for unsupported locales
- **WHEN** a customer's locale currency is not supported by Stripe
- **THEN** Stripe SHALL present the total in the default currency (USD)

### Requirement: Checkout creation validates price_per_token configured

The `create_checkout` view SHALL reject checkout session creation when `AppSettings.price_per_token` is not set or is zero/negative.

#### Scenario: Reject checkout without configured price
- **WHEN** a user POSTs to `/stripe/create-checkout/`
- **AND** `AppSettings.price_per_token` is `None` or `<= 0`
- **THEN** the system SHALL return a 400 error with message "Price must be configured first"

### Requirement: Presentment details stored in StripeEvent

The `StripeEvent` model SHALL store the customer-facing currency and amount from the webhook's `presentment_details`.

#### Scenario: Presentment details captured from webhook
- **WHEN** processing a `checkout.session.completed` webhook with `presentment_details`
- **THEN** the system SHALL store `presentment_currency` and `presentment_amount` from the payload

#### Scenario: Presentment details absent for non-adaptive sessions
- **WHEN** processing a session where `presentment_details` is not present
- **THEN** `presentment_currency` SHALL be stored as empty string
- **THEN** `presentment_amount` SHALL be stored as null

### Requirement: Admin sync button for Stripe Price management

The system SHALL provide a button on the AppSettings change form to trigger `sync_stripe_price`. The button SHALL appear inline with the Stripe configuration fields (`stripe_product_id`, `stripe_price_id`) and SHALL be rendered as a styled primary button.

#### Scenario: Sync button visible only to superusers
- **WHEN** a superuser views the AppSettings change form
- **THEN** they SHALL see a "Run Sync Stripe Price" button in the Stripe fieldset
- **THEN** the button SHALL use Unfold's primary button styling (solid primary background, white text)

#### Scenario: Sync button hidden for non-superusers
- **WHEN** a non-superuser staff member views the AppSettings change form
- **THEN** they SHALL see `"-"` instead of the button
- **THEN** they SHALL NOT be able to access the sync endpoint directly

#### Scenario: Sync button triggers management command
- **WHEN** a superuser clicks the sync button
- **THEN** the system SHALL execute `call_command("sync_stripe_price")`
- **THEN** the output SHALL be displayed as a success message
- **THEN** the user SHALL be redirected back to the AppSettings change form

### Requirement: Stripe Price auto-creation via management command

The system SHALL provide a management command to create or update a Stripe Product + Price automatically, seeded from `AppSettings.price_per_token`. No dashboard setup required.

#### Scenario: Sync command creates Product and Price
- **WHEN** running `sync_stripe_price` without an existing Product or Price
- **THEN** it SHALL create a new Product "Invitation Code Tokens"
- **THEN** it SHALL create a Price with `unit_amount = int(price_per_token * 100)`, `currency = "usd"`, no `currency_options`
- **THEN** it SHALL store Product ID in `AppSettings.stripe_product_id` and Price ID in `AppSettings.stripe_price_id`

#### Scenario: Sync command uses existing Product from AppSettings
- **WHEN** running `sync_stripe_price` with `AppSettings.stripe_product_id` already set
- **THEN** it SHALL reuse the existing Product instead of creating a new one

#### Scenario: Sync command archives and recreates Price on price change
- **WHEN** running `sync_stripe_price` after `price_per_token` has changed
- **THEN** it SHALL archive the existing Price via `active=False`
- **THEN** it SHALL create a NEW Price with the updated `unit_amount`
- **THEN** it SHALL update `AppSettings.stripe_price_id` to the new Price ID

#### Scenario: Sync command skips when price_per_token is zero
- **WHEN** running `sync_stripe_price` with `price_per_token = 0`
- **THEN** it SHALL skip all Stripe API calls
- **THEN** it SHALL output a message that purchasing is disabled

### Requirement: Payment success redirect shows confirmation

After a successful Stripe payment, the system SHALL redirect the user to the AppSettings change form and SHALL display a success message confirming the number of credits purchased. The cancel flow SHALL redirect back to the purchase page without a message.

#### Scenario: Success redirect to settings with token count

- **WHEN** a user completes a Stripe Checkout Session
- **THEN** the system SHALL redirect to `/admin/ourlives/appsettings/`
- **THEN** the system SHALL display a Django success message: "Payment successful! N credits added."
- **THEN** the `N` in the message SHALL equal the token count from the checkout

#### Scenario: Cancel redirect back to purchase page

- **WHEN** a user cancels a Stripe Checkout Session
- **THEN** the system SHALL redirect to `/admin/ourlives/appsettings/purchase/`
- **THEN** the system SHALL NOT display a success message

#### Scenario: Payment success without session_id

- **WHEN** a user completes a Stripe Checkout Session
- **AND** the `session_id` query parameter is missing from the success URL
- **THEN** the system SHALL still redirect to `/admin/ourlives/appsettings/`
- **THEN** the system SHALL display a generic success message
- **THEN** the system SHALL NOT error

