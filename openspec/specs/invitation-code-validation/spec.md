## ADDED Requirements

### Requirement: Admin form shows inline validation errors for invitation codes
The system SHALL display token pool exhaustion and business rule violations as inline form-level error messages in the Django admin, instead of crashing to a debug error page.

#### Scenario: Create code exceeds token pool
- **WHEN** admin user submits a new invitation code and the sum of all assigned tokens (including this code) exceeds `AppSettings.total_tokens`
- **THEN** the form redisplays with the error message "Not enough tokens. Available: X, Requested: Y" shown inline on the `max_use` field

#### Scenario: Update max_use below current_use
- **WHEN** admin user edits an invitation code and sets `max_use` to a value lower than the current `current_use` value in the database
- **THEN** the form redisplays with the error message "max_use (X) cannot be less than current_use (Y)" shown inline on the `max_use` field

#### Scenario: Update max_use exceeds token pool
- **WHEN** admin user edits an invitation code and increases `max_use` such that total assigned tokens exceed `total_tokens`
- **THEN** the form redisplays with the error message "Not enough tokens. Available: X, Requested: Y" shown inline on the `max_use` field

### Requirement: Race condition safety net for concurrent admin operations
The system SHALL prevent token pool over-assignment even when two admin users submit forms simultaneously, by retaining a database-level lock in the `save()` method.

#### Scenario: Two admins create codes simultaneously exhausting pool
- **WHEN** two admin users each submit a code that individually passes `clean()` validation but combined would exceed the pool
- **THEN** the second save transaction detects the over-assignment under the SELECT FOR UPDATE lock, rolls back, and the admin `save_model()` override catches the error, displaying it as a Django message instead of crashing

### Requirement: Reduce total_tokens below assigned tokens is rejected
The system SHALL prevent reducing `AppSettings.total_tokens` to a value lower than the sum of all assigned `max_use` values across invitation codes.

#### Scenario: Reduce total_tokens below assigned
- **WHEN** admin user attempts to set `total_tokens` to a value less than the current `tokens_assigned`
- **THEN** the form redisplays with the error message "Cannot set total tokens (X) below currently assigned tokens (Y)" shown inline on the `total_tokens` field
