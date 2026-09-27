## MODIFIED Requirements

### Requirement: Admin form shows inline validation errors for invitation codes
The system SHALL display business rule violations as inline form-level error messages in the Django admin, instead of crashing to a debug error page. Token pool exhaustion is no longer a validation error: codes may be created even when they over-assign the pool.

#### Scenario: Create code exceeding token pool is allowed
- **WHEN** admin user submits a new invitation code and the sum of all assigned tokens (including this code) exceeds `AppSettings.total_tokens`
- **THEN** the code is saved without a pool-exhaustion error (availability may go negative)

#### Scenario: Update max_use below current_use
- **WHEN** admin user edits an invitation code and sets `max_use` to a value lower than the current `current_use` value in the database
- **THEN** the form redisplays with the error message "max_use (X) cannot be less than current_use (Y)" shown inline on the `max_use` field

#### Scenario: Update max_use exceeding token pool is allowed
- **WHEN** admin user edits an invitation code and increases `max_use` such that total assigned tokens exceed `total_tokens`
- **THEN** the code is saved without a pool-exhaustion error (availability may go negative)

### Requirement: Current use never exceeds max use
The system SHALL continue to enforce `current_use <= max_use` on invitation codes.

#### Scenario: current_use above max_use rejected
- **WHEN** a save would leave `current_use` greater than `max_use`
- **THEN** the system rejects it with an error

### Requirement: Reduce total_tokens below assigned tokens is allowed
The system SHALL allow reducing `AppSettings.total_tokens` below the sum of all assigned `max_use` values across invitation codes (availability may go negative).

#### Scenario: Reduce total_tokens below assigned
- **WHEN** admin user sets `total_tokens` to a value less than the current `tokens_assigned`
- **THEN** the change is accepted and `tokens_available` becomes negative

## REMOVED Requirements

### Requirement: Race condition safety net for concurrent admin operations
**Reason**: The token pool over-assignment guard it protected no longer exists — order-creation and code creation are decoupled from the pool (negative availability is the intended model).
**Migration**: No migration path needed; concurrent admin saves of invitation codes are unaffected (they simply no longer coordinate on pool capacity).