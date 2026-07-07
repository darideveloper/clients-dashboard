## ADDED Requirements

### Requirement: Admin can manage projects
The system SHALL provide CRUD for Project entities in the admin panel.

#### Scenario: Create project
- **WHEN** admin creates a project with name "Launch Alpha" and description "First batch"
- **THEN** a Project row exists with name="Launch Alpha" and description="First batch"

#### Scenario: Duplicate project name rejected
- **WHEN** admin creates a project with a name that already exists
- **THEN** the system rejects with a uniqueness error

### Requirement: Admin can manage invitation codes
The system SHALL provide CRUD for InvitationCode entities in the admin panel. Each code is linked to a Project.

#### Scenario: Create invitation code with auto-generated code
- **WHEN** admin creates a new InvitationCode for a project with max_use=10
- **THEN** a code field is auto-populated with a unique random string and admin can edit it before saving
- **AND** is_active defaults to True, current_use defaults to 0

#### Scenario: Edit invitation code max_use
- **WHEN** admin changes max_use from 10 to 5
- **THEN** the update succeeds only if 5 >= current_use
- **AND** the token pool validation passes

#### Scenario: Deactivate invitation code
- **WHEN** admin sets is_active=False on an invitation code
- **THEN** the code is marked inactive but its max_use tokens remain consumed from the pool

#### Scenario: Reactivate disabled invitation code
- **WHEN** admin reactivates an invitation code (is_active=True)
- **THEN** the pool validation re-verifies that enough tokens remain to cover max_use
- **AND** if insufficient tokens remain, the reactivation is rejected with a ValidationError

### Requirement: Token pool validation
The system SHALL enforce that `SUM(max_use)` of all InvitationCodes never exceeds `total_tokens` in AppSettings.

#### Scenario: Create code within pool limit
- **WHEN** total_tokens=100, assigned=90, and admin creates a code with max_use=10
- **THEN** the code is saved successfully

#### Scenario: Create code exceeding pool limit
- **WHEN** total_tokens=100, assigned=95, and admin creates a code with max_use=10
- **THEN** the system rejects with a ValidationError explaining the token shortfall

#### Scenario: Update code increasing max_use within limit
- **WHEN** total_tokens=100, assigned=90, admin changes a code from max_use=5 to max_use=10
- **THEN** the update succeeds (assigned becomes 95, still within 100)

#### Scenario: Update code increasing max_use beyond limit
- **WHEN** total_tokens=100, assigned=95, admin changes a code from max_use=5 to max_use=10
- **THEN** the system rejects with a ValidationError

#### Scenario: Concurrent saves are serialized
- **WHEN** two admins simultaneously create codes that together would exceed total_tokens
- **THEN** only the first succeeds, the second is rejected

### Requirement: current_use is read-only in admin
The `current_use` field SHALL be displayed but not editable in the admin panel.

#### Scenario: Admin views invitation code detail
- **WHEN** admin opens an InvitationCode edit form
- **THEN** current_use appears as read-only text, not an input field

### Requirement: DB-level constraint on current_use
The database SHALL enforce that `current_use <= max_use` at row level.

#### Scenario: External service increments within limit
- **WHEN** external service runs `UPDATE SET current_use = 4` on a code with max_use=5
- **THEN** the update succeeds

#### Scenario: External service exceeds limit
- **WHEN** external service runs `UPDATE SET current_use = 6` on a code with max_use=5
- **THEN** the database rejects the update with a constraint violation

### Requirement: Admin can view token pool status
The AppSettings singleton SHALL display computed token status fields in the admin.

#### Scenario: View token pool status
- **WHEN** admin opens the AppSettings page with total_tokens=100, two codes with max_use=5 (current_use=3 each), and one code with max_use=10 (current_use=0)
- **THEN** the page shows: assigned=20, used=6, available=80

#### Scenario: Edit total_tokens
- **WHEN** admin changes total_tokens from 100 to 50
- **THEN** the save succeeds even if assigned > 50 (new code creation is blocked until pool grows)
