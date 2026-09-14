## MODIFIED Requirements

### Requirement: Rep admin registration

The system SHALL register `Rep` in `ourlives/admin.py` as `RepAdmin(OurlivesModelAdminBase)` with `sidebar_icon="badge"`, `list_display=("first_name","last_name","email")`, `search_fields=("first_name","last_name","email")`, full add/change/delete permissions, and no `list_filter` or `list_editable`.

#### Scenario: Rep CRUD by staff

- **WHEN** a staff user creates a `Rep` with first_name "John", last_name "Doe", email "john@ourlivesapp.com"
- **THEN** it persists, appears in the changelist searchable by any name/email fragment, and remains editable and deletable

#### Scenario: Rep sidebar icon is unique

- **WHEN** a staff user loads any admin page
- **THEN** the Reps nav entry renders the `badge` glyph, distinct from the Users `person` glyph
