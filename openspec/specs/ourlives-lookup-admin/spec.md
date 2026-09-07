# ourlives-lookup-admin Specification

## Purpose
Admin registration and changelist behavior for the Phase-1 lookup models (`Country`, `Rep`, `ContactType`, `CodeType`, `OrderType`) plus the `InvitationCode` admin tune. Created by archiving change register-ourlives-models-admin.
## Requirements
### Requirement: Country admin registration

The system SHALL register `Country` in `ourlives/admin.py` as `CountryAdmin(OurlivesModelAdminBase)` with `sidebar_icon="globe"`, `list_display=("iso2","iso3","name","active")`, `list_display_links=("iso2",)`, `list_filter=("active",)`, `search_fields=("iso2","iso3","name")`, `list_editable=("active",)`, `has_add_permission` returning False and `has_delete_permission` returning False.

#### Scenario: Country changelist renders

- **WHEN** a staff user with `ourlives` view permission opens `/admin/ourlives/country/`
- **THEN** rows show ISO2, ISO3, name, and active flag with search over ISO2/ISO3/name and a single Active filter

#### Scenario: Country add and delete blocked

- **WHEN** a staff user opens the Country changelist or guesses `/admin/ourlives/country/add/`
- **THEN** no Add button is shown and direct add/delete attempts are denied while inline active toggles still save

### Requirement: Rep admin registration

The system SHALL register `Rep` in `ourlives/admin.py` as `RepAdmin(OurlivesModelAdminBase)` with `sidebar_icon="person"`, `list_display=("first_name","last_name","email")`, `search_fields=("first_name","last_name","email")`, full add/change/delete permissions, and no `list_filter` or `list_editable`.

#### Scenario: Rep CRUD by staff

- **WHEN** a staff user creates a `Rep` with first_name "John", last_name "Doe", email "john@ourlivesapp.com"
- **THEN** it persists, appears in the changelist searchable by any name/email fragment, and remains editable and deletable

### Requirement: ContactType admin registration

The system SHALL register `ContactType` in `ourlives/admin.py` as `ContactTypeAdmin(OurlivesModelAdminBase)` with `sidebar_icon="contacts"`, `list_display=("code","name","active")`, `list_display_links=("code",)`, `list_filter=("active",)`, `search_fields=("code","name")`, `list_editable=("active",)` and full add/change/delete permissions.

#### Scenario: ContactType toggle inline

- **WHEN** a staff user flips `active` on a ContactType row and saves the changelist
- **THEN** the change persists without opening the detail form and `code` remains the row link

### Requirement: CodeType admin registration

The system SHALL register `CodeType` in `ourlives/admin.py` as `CodeTypeAdmin(OurlivesModelAdminBase)` with `sidebar_icon="sell"`, `list_display=("code","name","max_codes","active")`, `list_display_links=("code",)`, `list_filter=("active",)`, `search_fields=("code","name")`, `list_editable=("active",)` and full add/change/delete permissions.

#### Scenario: CodeType shows bundle size

- **WHEN** a staff user opens `/admin/ourlives/codetype/`
- **THEN** each row shows `max_codes` alongside code, name, and active, with `max_codes` editable only in the detail form

### Requirement: OrderType admin registration

The system SHALL register `OrderType` in `ourlives/admin.py` as `OrderTypeAdmin(OurlivesModelAdminBase)` with `sidebar_icon="shopping_bag"`, `list_display=("code","name","active")`, `list_display_links=("code",)`, `list_filter=("active",)`, `search_fields=("code","name")`, `list_editable=("active",)` and full add/change/delete permissions.

#### Scenario: OrderType free management

- **WHEN** a staff user adds an `OrderType` with a new code and name
- **THEN** it persists, is searchable by code/name, and its active flag is toggleable inline

### Requirement: InvitationCode admin tune

The system SHALL set `InvitationCodeAdmin.autocomplete_fields=("project","organization")` and `list_editable=("is_active",)` keeping `list_display_links=("code",)`, with all existing display, filter, search, `readonly_fields=("current_use",)`, and pool validation behavior unchanged.

#### Scenario: InvitationCode autocomplete and quick deactivate

- **WHEN** a staff user opens an InvitationCode change form
- **THEN** project and organization render as autocomplete widgets backed by existing `search_fields`
- **WHEN** a staff user flips `is_active` on the changelist and saves
- **THEN** the flag persists and `max_use`/`current_use` remain non-inline with pool validation still enforced on save
