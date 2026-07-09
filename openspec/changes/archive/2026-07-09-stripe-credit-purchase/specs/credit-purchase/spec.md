## ADDED Requirements

### Requirement: Configure price per token

The system SHALL allow administrators to set a price per invitation code token in `AppSettings`, stored as a decimal field representing USD.

#### Scenario: Set price per token

- **WHEN** an administrator saves `AppSettings` with `price_per_token` set to `0.10`
- **THEN** the value `0.10` is persisted and used for all future purchase calculations

#### Scenario: Price per token is negative

- **WHEN** an administrator attempts to save `price_per_token` as a negative value
- **THEN** validation rejects the value with an error

#### Scenario: Price per token is zero (unconfigured)

- **WHEN** `price_per_token` is `0.00` (default, meaning pricing is not yet configured)
- **THEN** the model save succeeds, but any purchase attempt is rejected at runtime with "price must be configured first"

### Requirement: Configure minimum purchase amount

The system SHALL allow administrators to set a minimum dollar amount required for any purchase in `AppSettings`.

#### Scenario: Set minimum purchase amount

- **WHEN** an administrator saves `AppSettings` with `min_purchase_amount` set to `5.00`
- **THEN** the value `5.00` is persisted and enforced for all future purchases

#### Scenario: Minimum purchase amount is negative

- **WHEN** an administrator attempts to save `min_purchase_amount` as a negative value
- **THEN** validation rejects the value with an error

#### Scenario: Minimum purchase amount is zero

- **WHEN** an administrator saves `min_purchase_amount` as `0.00`
- **THEN** the save succeeds (zero minimum means no minimum purchase enforcement)

### Requirement: Standalone purchase page

The system SHALL provide a standalone "Purchase Credits" page at `/admin/ourlives/appsettings/purchase/` accessible to any staff user with `has_module_perms("ourlives")`, regardless of `change_appsettings` permission.

#### Scenario: Purchase page accessible to ourlives user

- **WHEN** a staff user with `ourlives.view_project` (but not `ourlives.change_appsettings`) navigates to the purchase page
- **THEN** the page renders inside the admin shell showing the purchase form with current price, minimum amount, and token pool status

#### Scenario: Purchase page forbidden to non-ourlives user

- **WHEN** a staff user with no ourlives model permissions attempts to access the purchase page
- **THEN** the system returns HTTP 403

#### Scenario: Purchase page renders purchase form

- **WHEN** the purchase page is loaded
- **THEN** the page displays a number input for USD amount, a "Buy Credits" button, and a live preview of how many tokens the entered amount will buy

#### Scenario: Pricing not configured on purchase page

- **WHEN** the purchase page is loaded and `price_per_token` is `0.00`
- **THEN** the page displays an error message indicating pricing is not configured and the purchase form is disabled

### Requirement: Sidebar navigation link for purchase page

The system SHALL display a "Purchase Credits" link in the admin sidebar for any user with `has_module_perms("ourlives")`, rendered via `UNFOLD["SIDEBAR"]["navigation"]` alongside the standard model-based `available_apps` entries.

#### Scenario: Sidebar link visible to ourlives user

- **WHEN** a staff user with any ourlives model permission views any admin page
- **THEN** the admin sidebar shows a "Purchase Credits" link with a shopping cart icon, separated from the model entries by a divider

#### Scenario: Sidebar link hidden from non-ourlives user

- **WHEN** a staff user with no ourlives model permissions views any admin page
- **THEN** the admin sidebar does not show the "Purchase Credits" link

### Requirement: Create Stripe Checkout Session

The system SHALL create a Stripe Checkout Session when a valid purchase is submitted, embedding the source app identifier, calculated token count, and AppSettings ID in the session metadata.

#### Scenario: Successful session creation

- **WHEN** an admin submits a purchase of `$10.00` with `price_per_token = 0.10`
- **THEN** the system creates a Stripe Checkout Session for `$10.00` with metadata `{source: "ourlives", token_count: "100", app_settings_id: "<pk>"}` (string values) and redirects the admin to the Stripe-hosted checkout URL

#### Scenario: Stripe API error

- **WHEN** the Stripe API call fails (network error, invalid key, etc.)
- **THEN** the system displays an error message and does not redirect

#### Scenario: Amount too low for token count

- **WHEN** an admin submits a purchase where `amount / price_per_token` yields zero tokens
- **THEN** the system rejects the purchase with an error message before making any Stripe API call

#### Scenario: Success and cancel URLs

- **WHEN** a Checkout Session is created
- **THEN** the `success_url` points back to the standalone purchase page (`/admin/ourlives/appsettings/purchase/`) and the `cancel_url` points back to the same page

### Requirement: Token count calculation

The system SHALL calculate the number of tokens purchased as the floor division of the submitted dollar amount by `price_per_token`, and SHALL reject purchases where the calculated token count is zero.

#### Scenario: Exact division

- **WHEN** amount is `10.00` and `price_per_token` is `0.10`
- **THEN** the calculated token count is `100`

#### Scenario: Non-exact division

- **WHEN** amount is `5.00` and `price_per_token` is `0.30`
- **THEN** the calculated token count is `16` (truncating any fractional token)

#### Scenario: Amount below price per token results in zero tokens

- **WHEN** amount is `1.00` and `price_per_token` is `1.50`
- **THEN** the system rejects the purchase with an error indicating the amount is too low to buy any tokens, and no Stripe Checkout Session is created
