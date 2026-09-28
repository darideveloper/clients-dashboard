# invitation-code-autocreate Specification

## Purpose
Auto-population of InvitationCode rows from form code-N slots (code_type by bundle, sequence, max_use=1, current_use=0, project always ourlens, order + org links), Order.tokens_used population, and add-missing-codes reconcile on re-submit.
## Requirements

### Requirement: The ourlens project is guaranteed by fixture
The system SHALL ship a `Project` fixture (`ourlives/fixtures/ourlives/Project.json`) containing the `ourlens` project (and `ourplan`) so a fresh environment loaded via `base_loaddata` always has the project the webhook depends on.

#### Scenario: Fresh environment has the ourlens project
- **WHEN** a fresh environment runs `migrate` + `base_loaddata`
- **THEN** a Project named `ourlens` exists (alongside `ourplan`) and codes can be linked to it without manual admin entry

### Requirement: Codes never block order creation
The system SHALL create order and codes regardless of the current token pool state (availability may go negative).

#### Scenario: Order with codes succeeds when pool is exhausted
- **WHEN** `AppSettings.total_tokens` is less than the sum of assigned `max_use` (or availability is already negative)
- **THEN** the order and its codes are still created without validation error

#### Scenario: Created codes count toward availability
- **WHEN** codes are created
- **THEN** `tokens_assigned` and `tokens_available` reflect the new codes (availability may be negative)
