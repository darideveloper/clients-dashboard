## ADDED Requirements

### Requirement: Stripe secret key from environment

The system SHALL read the Stripe secret key from the `STRIPE_SECRET_KEY` environment variable at startup.

#### Scenario: Key available in environment

- **WHEN** the application starts and `STRIPE_SECRET_KEY` is set in the env file
- **THEN** `stripe.api_key` is configured with that value and Stripe API calls succeed

#### Scenario: Key missing in environment

- **WHEN** the application starts and `STRIPE_SECRET_KEY` is not set
- **THEN** the application still starts (graceful degradation), but any Stripe API call raises a clear error indicating the key is missing

### Requirement: Webhook signing secret from environment

The system SHALL read the Stripe webhook signing secret from the `STRIPE_WEBHOOK_SECRET` environment variable.

#### Scenario: Secret available

- **WHEN** a webhook request arrives and `STRIPE_WEBHOOK_SECRET` is configured
- **THEN** the system verifies the Stripe signature using that secret before processing the event

#### Scenario: Secret missing

- **WHEN** a webhook request arrives and `STRIPE_WEBHOOK_SECRET` is not set
- **THEN** the system rejects the webhook with a 500 error indicating missing configuration

### Requirement: No admin surface for credentials

The system SHALL NOT expose Stripe credentials in the Django admin interface, database, or any model field.

#### Scenario: Credentials absent from admin

- **WHEN** any admin page is rendered
- **THEN** no form field, read-only display, or configuration option reveals the `STRIPE_SECRET_KEY` or `STRIPE_WEBHOOK_SECRET` values

#### Scenario: Credentials absent from database

- **WHEN** a database backup or dump is inspected
- **THEN** no table or row contains the Stripe secret key or webhook signing secret
