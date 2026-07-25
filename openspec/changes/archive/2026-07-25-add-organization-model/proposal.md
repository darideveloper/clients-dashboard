## Why

Invitation codes currently link only to a `Project`, but operationally we also need to track which *organization* an invitation code belongs to. An organization represents the billing/account entity, while a project is the technical scope. Both dimensions are needed for internal control and reporting — without this, we cannot distinguish codes issued to different organizations within the same project.

## What Changes

- New `Organization` model with `name` and `description` fields (internal control only, no validation)
- `InvitationCode` gains a required `organization` ForeignKey to `Organization`, alongside the existing `project` FK
- Admin UI updated to manage Organizations and show the new field on InvitationCodes
- `import_invitation_codes` management command updated to accept `--organization`
- Migration: create `Organization` table, add FK column to `InvitationCode`, backfill data

## Capabilities

### New Capabilities
- `organization-management`: CRUD for Organization model (name, description), admin registration, list/filter/search in admin
- `invitation-code-org-link`: `InvitationCode.organization` FK field, inclusion in admin list display/filter, CSV import support

### Modified Capabilities
*(none — no existing specs are affected)*

## Impact

- `ourlives/models.py` — new `Organization` model, new FK on `InvitationCode`
- `ourlives/admin.py` — register `OrganizationAdmin`, update `InvitationCodeAdmin` list/filter/search fields
- `ourlives/management/commands/import_invitation_codes.py` — add `--organization` argument, lookup by name
- `ourlives/tests.py` — add Organization to test fixtures, update test assertions
- A new migration will be generated
