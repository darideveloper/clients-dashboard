## ADDED Requirements

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
