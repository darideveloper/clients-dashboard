## ADDED Requirements

### Requirement: Organization CRUD

The system SHALL provide an Organization model with fields for `name` (unique, max 100 chars) and `description` (text, blankable). The system SHALL register Organization in the Django admin with search by name and filtered list display.

#### Scenario: Create organization via admin
- **WHEN** a staff user creates an Organization with name "Acme Corp" and description "Primary billing entity"
- **THEN** the Organization SHALL be persisted with those values and appear in the admin list

#### Scenario: Organization name uniqueness
- **WHEN** a user attempts to create a second Organization with the same name as an existing one
- **THEN** the system SHALL reject the duplicate and show a validation error

#### Scenario: Organization list display
- **WHEN** a staff user views the Organization admin list
- **THEN** the list SHALL display "name" and "description" columns, be searchable by name, and sortable by name
