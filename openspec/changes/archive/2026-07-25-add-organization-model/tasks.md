## 1. Model Layer

- [x] 1.1 Add `Organization` model in `ourlives/models.py` with `name` (unique, max 100) and `description` (text, blank) fields, proper Meta class and `__str__`
- [x] 1.2 Add `organization` ForeignKey to `InvitationCode` (`on_delete=PROTECT`, non-nullable, no explicit `related_name` — Django defaults to `invitationcode_set` to avoid collision with project FK's `related_name="invitation_codes"`)
- [x] 1.3 Generate the migration for the new model, add the FK column as nullable initially, and create a data migration to assign existing codes to a default organization (e.g., "Legacy")
- [x] 1.4 Create a second migration that alters the FK column to be non-nullable

## 2. Admin

- [x] 2.1 Register `OrganizationAdmin` in `ourlives/admin.py` (sidebar icon, list_display: name+description, search: name)
- [x] 2.2 Update `InvitationCodeAdmin` — add `organization` to `list_display`, `list_filter`, and `search_fields`

## 3. Management Command

- [x] 3.1 Add `--organization` / `-o` required argument to `import_invitation_codes` command
- [x] 3.2 Add Organization lookup by name in the command (raise `CommandError` if not found, matching the Project pattern)
- [x] 3.3 Include `organization` in the row dict passed to `InvitationCode(**vals)` and in the `update_or_create` defaults

## 4. Tests

- [x] 4.1 Add `Organization` creation to test fixtures in `ourlives/tests.py`
- [x] 4.2 Update existing `InvitationCode` creation calls to include `organization`
- [x] 4.3 Add tests for `import_invitation_codes --organization` (valid org, missing org)
