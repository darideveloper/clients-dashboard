# ourlives-lookup-admin Specification

## Purpose
Admin registration and changelist behavior for the Phase-1 lookup models (`Country`, `Rep`, `ContactType`, `CodeType`, `OrderType`) plus the `InvitationCode` admin tune. Created by archiving change register-ourlives-models-admin.
## Requirements
### Requirement: Country admin registration

The system SHALL register `Country` in `ourlives/admin.py` as `CountryAdmin(OurlivesModelAdminBase)` with `sidebar_icon="globe"`, `list_display=("iso2","iso3","name","active")`, `list_display_links=("iso2",)`, `list_filter=("active",)`, `search_fields=("^iso2","^iso3","name")`, `list_editable=("active",)`, `has_add_permission` returning False and `has_delete_permission` returning False.

#### Scenario: Country changelist renders

- **WHEN** a staff user with `ourlives` view permission opens `/admin/ourlives/country/`
- **THEN** rows show ISO2, ISO3, name, and active flag with prefix search over ISO2/ISO3 plus name search and a single Active filter

#### Scenario: Country add and delete blocked

- **WHEN** a staff user opens the Country changelist or guesses `/admin/ourlives/country/add/`
- **THEN** no Add button is shown and direct add/delete attempts are denied while inline active toggles still save

### Requirement: Rep admin registration

The system SHALL register `Rep` in `ourlives/admin.py` as `RepAdmin(OurlivesModelAdminBase)` with `sidebar_icon="badge"`, `list_display=("first_name","last_name","email","order_count_display","agreed_scans_total_display","catalog_items_total_display","combined_total_display","last_order_date_display")`, `search_fields=("first_name","last_name","email")`, full add/change/delete permissions, and no `list_filter` or `list_editable`. `order_count_display` and `last_order_date_display` SHALL be sortable via `admin_order_field` on annotated queryset fields; the three money columns SHALL render per-currency breakdowns (display-only). The change form SHALL include a readonly "Order summary" section exposing the five summaries with their labels and help texts (see `org-rep-order-summaries`).

#### Scenario: Rep CRUD by staff

- **WHEN** a staff user creates a `Rep` with first_name "John", last_name "Doe", email "john@ourlivesapp.com"
- **THEN** it persists, appears in the changelist searchable by any name/email fragment, and remains editable and deletable

#### Scenario: Rep sidebar icon is unique

- **WHEN** a staff user loads any admin page
- **THEN** the Reps nav entry renders the `badge` glyph, distinct from the Users `person` glyph

#### Scenario: Rep summary columns
- **WHEN** a staff user views the Rep changelist for a rep with orders in two currencies
- **THEN** the row shows the correct `order_count` and per-currency money breakdowns without per-row queries

#### Scenario: Rep summary section
- **WHEN** a staff user opens a Rep change form
- **THEN** a readonly "Order summary" section shows the five summaries with labels and help texts

### Requirement: ContactType admin registration

The system SHALL register `ContactType` in `ourlives/admin.py` as `ContactTypeAdmin(OurlivesModelAdminBase)` with `sidebar_icon="contacts"`, `list_display=("code","name","active")`, `list_display_links=("code",)`, `list_filter=("active",)`, `search_fields=("^code","name","description")`, `list_editable=("active",)` and full add/change/delete permissions.

#### Scenario: ContactType toggle inline

- **WHEN** a staff user flips `active` on a ContactType row and saves the changelist
- **THEN** the change persists without opening the detail form and `code` remains the row link

#### Scenario: ContactType found by description

- **WHEN** a staff user searches a description word in `/admin/ourlives/contacttype/`
- **THEN** matching types are returned alongside code/name matches

### Requirement: CodeType admin registration

The system SHALL register `CodeType` in `ourlives/admin.py` as `CodeTypeAdmin(OurlivesModelAdminBase)` with `sidebar_icon="sell"`, `list_display=("code","name","max_codes","active")`, `list_display_links=("code",)`, `list_filter=("active",)`, `search_fields=("^code","name","description")`, `list_editable=("active",)` and full add/change/delete permissions.

#### Scenario: CodeType shows bundle size

- **WHEN** a staff user opens `/admin/ourlives/codetype/`
- **THEN** each row shows `max_codes` alongside code, name, and active, with `max_codes` editable only in the detail form

#### Scenario: CodeType found by description

- **WHEN** a staff user searches a description word in `/admin/ourlives/codetype/`
- **THEN** matching types are returned alongside code/name matches

### Requirement: OrderType admin registration

The system SHALL register `OrderType` in `ourlives/admin.py` as `OrderTypeAdmin(OurlivesModelAdminBase)` with `sidebar_icon="shopping_bag"`, `list_display=("code","name","active")`, `list_display_links=("code",)`, `list_filter=("active",)`, `search_fields=("^code","name","description")`, `list_editable=("active",)` and full add/change/delete permissions.

#### Scenario: OrderType free management

- **WHEN** a staff user adds an `OrderType` with a new code and name
- **THEN** it persists, is searchable by code/name/description, and its active flag is toggleable inline

### Requirement: InvitationCode admin tune

The system SHALL set `InvitationCodeAdmin` with `search_fields=("^code","project__name","organization__name","order__order_number","code_type__code","code_type__name")`, `list_filter=("is_active","project","organization","code_type")`, `autocomplete_fields=("project","organization")` and `list_editable=("is_active",)` keeping `list_display_links=("code",)`, with all existing display, `readonly_fields=("current_use",)`, and pool validation behavior unchanged, plus `search_help_text` naming code/project/org/order/type coverage.

#### Scenario: InvitationCode autocomplete and quick deactivate

- **WHEN** a staff user opens an InvitationCode change form
- **THEN** project and organization render as autocomplete widgets backed by existing `search_fields`
- **WHEN** a staff user flips `is_active` on the changelist and saves
- **THEN** the flag persists and `max_use`/`current_use` remain non-inline with pool validation still enforced on save

#### Scenario: InvitationCode found by order or type

- **WHEN** a staff user searches an order number fragment or a code-type code in `/admin/ourlives/invitationcode/`
- **THEN** linked invitation codes are returned
- **WHEN** a staff user clicks a `code_type` filter choice
- **THEN** only codes of that type are shown
