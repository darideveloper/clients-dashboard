## MODIFIED Requirements

### Requirement: Rep admin registration

The system SHALL register `Rep` in `ourlives/admin.py` as `RepAdmin(OurlivesModelAdminBase)` with `sidebar_icon="badge"`, `list_display=("first_name","last_name","email","order_count_display","agreed_scans_total_display","catalog_items_total_display","combined_total_display","last_order_date_display")`, `search_fields=("first_name","last_name","email")`, full add/change/delete permissions, and no `list_filter` or `list_editable`. `order_count_display` and `last_order_date_display` SHALL be sortable via `admin_order_field` on annotated queryset fields; the three money columns SHALL render per-currency breakdowns (display-only), with `combined_total_display` labeled "Total Order Value". The change form SHALL include a readonly "Order summary" section exposing the five summaries with their labels and help texts (see `org-rep-order-summaries`).

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
