## ADDED Requirements

### Requirement: Import invitation codes from CSV via management command
The system SHALL provide a Django management command `import_invitation_codes` that reads a CSV file and creates or updates `InvitationCode` records linked to a specified project.

#### Scenario: Successful bulk import of new codes
- **WHEN** the operator runs `python manage.py import_invitation_codes --project ourlens --csv invitations_codes.csv` and all codes in the CSV are new (no code values already exist in the database) and the CSV is well-formed
- **THEN** the system creates all `InvitationCode` records via `bulk_create` in a single operation, linked to the project named "ourlens", and reports the count of created records

#### Scenario: Code already exists is overwritten
- **WHEN** the CSV contains a code value that already exists in the database for the same project
- **THEN** the system updates that existing record's `max_use`, `current_use`, and `is_active` fields to match the CSV row, and reports it as updated (not created)

#### Scenario: Project not found
- **WHEN** the operator specifies a `--project` name that does not match any `Project` record
- **THEN** the system outputs an error message stating the project was not found and exits without modifying the database

#### Scenario: CSV file not found
- **WHEN** the operator specifies a `--csv` path that does not point to a readable file
- **THEN** the system outputs an error message stating the file was not found and exits without modifying the database

### Requirement: CSV column mapping and validation
The system SHALL map CSV columns to model fields with explicit names and validate all rows before any database write.

#### Scenario: Required columns are validated
- **WHEN** the CSV file is missing any of the required columns (`code`, `max_use_rate`, `current_use_rate`, `is_active`)
- **THEN** the system outputs an error listing the missing columns and exits without modifying the database

#### Scenario: CSV values are type-validated
- **WHEN** any row in the CSV has a non-integer value for `max_use_rate` or `current_use_rate`, an empty `code`, or a non-boolean value for `is_active`
- **THEN** the system outputs an error identifying the problematic row number and column, and exits without modifying the database

#### Scenario: current_use exceeds max_use in CSV row
- **WHEN** any row has `current_use_rate` greater than `max_use_rate`
- **THEN** the system outputs an error identifying the row and the values, and exits without modifying the database

#### Scenario: api_token column is ignored
- **WHEN** the CSV contains an `api_token` column
- **THEN** the system ignores it silently; its presence or absence does not affect the import

### Requirement: Token pool auto-adjustment
The system SHALL ensure `AppSettings.total_tokens` is large enough to accommodate the sum of all imported `max_use_rate` values, bumping it up if necessary.

#### Scenario: Token pool is sufficient
- **WHEN** `AppSettings.total_tokens` is greater than or equal to the sum of all `max_use_rate` values in the CSV
- **THEN** the system does not modify `total_tokens` and proceeds with the import

#### Scenario: Token pool is insufficient and auto-bumped
- **WHEN** `AppSettings.total_tokens` is less than the sum of all `max_use_rate` values in the CSV
- **THEN** the system sets `total_tokens` to the required sum, reports the old and new values to the operator, and proceeds with the import

### Requirement: Idempotent re-runs
The system SHALL support re-running the command with the same CSV and project without errors or duplicate side effects.

#### Scenario: Re-run with same CSV
- **WHEN** the operator runs the command a second time with the same CSV and project
- **THEN** the system reports all codes as updated (since they now exist), the token pool adjustment is a no-op (total_tokens already sufficient), and no new records are created beyond the original set
