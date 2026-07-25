# invitation-code-org-link Specification

## Purpose
TBD - created by archiving change add-organization-model. Update Purpose after archive.
## Requirements
### Requirement: InvitationCode organization FK

The `InvitationCode` model SHALL have a required ForeignKey field `organization` pointing to `Organization` with `on_delete=PROTECT`. The reverse relation from Organization SHALL use Django's default related name (`invitationcode_set`), since `related_name="invitation_codes"` is already used by the `project` FK.

#### Scenario: Create invitation code with organization
- **WHEN** a user creates an InvitationCode with both a Project and an Organization
- **THEN** the InvitationCode SHALL be persisted with both foreign keys set correctly

#### Scenario: Protect organization with active codes
- **WHEN** a user attempts to delete an Organization that has associated InvitationCodes
- **THEN** the system SHALL prevent deletion and raise a ProtectedError

### Requirement: Admin display and filtering

The InvitationCode admin SHALL display `organization` in list view, support filtering by organization, and include search by `organization__name`.

#### Scenario: Organization column in list
- **WHEN** a staff user views the InvitationCode admin list
- **THEN** the organization name SHALL appear as a column alongside the existing project column

#### Scenario: Filter by organization
- **WHEN** a staff user applies the organization filter in the InvitationCode admin
- **THEN** the list SHALL filter to only invitation codes belonging to the selected organization

### Requirement: CSV import with organization

The `import_invitation_codes` management command SHALL accept a `--organization` argument (required) that specifies the Organization name. The command SHALL look up the Organization by name and assign it to all imported codes.

#### Scenario: Import with valid organization
- **WHEN** a user runs `import_invitation_codes --organization "Acme Corp" --csv data.csv`
- **THEN** all imported InvitationCodes SHALL have their `organization` FK set to the matching Organization

#### Scenario: Import with unknown organization
- **WHEN** a user runs `import_invitation_codes --organization "Ghost" --csv data.csv`
- **THEN** the command SHALL raise a CommandError with a message like "Organization 'Ghost' not found."

