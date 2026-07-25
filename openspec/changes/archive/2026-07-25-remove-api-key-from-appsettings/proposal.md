## Why

The `api_key` field added to `AppSettings` in the previous change is not needed — the external service it was intended for doesn't require a per-instance API key. Removing it avoids maintaining an unused field and migration baggage.

## What Changes

- Remove `api_key` field from `AppSettings` model
- Remove `api_key` from admin fieldset and `get_readonly_fields`
- Remove `api_key` assertions from admin tests
- Generate a new migration that drops the column (never deployed to prod, but already committed)
- Update the `admin-managed-settings` spec to reflect `api_key` is removed

## Capabilities

### New Capabilities
_(none)_

### Modified Capabilities
- `admin-managed-settings`: Remove the `api_key` requirement; the capability now covers only `storage_base_url` and any future superuser-only fields.

## Impact

- `ourlives/models.py` — remove `api_key` field
- `ourlives/admin.py` — remove `api_key` from fieldset and `get_readonly_fields`
- `ourlives/tests.py` — remove `api_key` assertions from `AppSettingsAdminTests`
- `ourlives/migrations/` — new migration to remove the column
- `openspec/specs/admin-managed-settings/spec.md` — remove `api_key` requirement
