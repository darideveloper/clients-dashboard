## Why

The ourlives app manages invitation codes tied to projects, but there is no way to bulk-import codes from an external CSV source. When onboarding a new project (e.g., "ourlens") with dozens of pre-generated codes, the admin must manually create each code one by one—error-prone and slow.

## What Changes

- New Django management command `import_invitation_codes` in the `ourlives` app
- Accepts a CSV file path and a project name (not ID—IDs are not fixed across environments)
- Uses `bulk_create` for a single atomic insert of all valid rows
- If a code already exists (unique constraint), it is overwritten with `update_or_create`
- Automatically ensures `AppSettings.total_tokens` is large enough to fit all imported codes; bumps it if needed
- Validates all rows upfront before touching the database (csv structure, field types, `current_use ≤ max_use`, project existence)

## Capabilities

### New Capabilities

- `bulk-code-import`: Import invitation codes from a CSV file into a specified project via a management command

### Modified Capabilities

<!-- No existing capability requirements change. The existing `invitation-code-validation` spec (admin form validation, token pool constraints, race condition safety) is unchanged—the new command respects those constraints by bumping `total_tokens` before inserts. -->

## Impact

- **New file**: `ourlives/management/commands/import_invitation_codes.py`
- **New package files**: `ourlives/management/__init__.py`, `ourlives/management/commands/__init__.py`
- **No modifications** to existing models, views, admin, or other commands
- **Depends on**: `ourlives.models.Project`, `ourlives.models.InvitationCode`, `ourlives.models.AppSettings`
