## Why

AppSettings (the singleton model) currently manages token pools, pricing, and Stripe configuration. The app needs two additional settings — `api_key` and `storage_base_url` — that must be configurable at runtime through the admin UI and editable only by superusers.

## What Changes

- Add `api_key` (CharField) and `storage_base_url` (URLField) to the `AppSettings` model
- Display them in a new "API Configuration" fieldset in the existing `AppSettingsAdmin`
- Restrict editing to superusers (`is_superuser=True`) via dynamic `get_readonly_fields`; other staff can view but not edit
- Generate a new Django migration for the schema change
- Update the admin coverage test if one exists

## Capabilities

### New Capabilities
- `admin-managed-settings`: Runtime configuration of API credentials and storage URLs through the AppSettings singleton, editable only by superusers in the admin interface. This capability covers any future superuser-only fields on AppSettings.

### Modified Capabilities
_(none — no existing spec behavior changes)_

## Impact

- `ourlives/models.py` — 2 new fields on `AppSettings`
- `ourlives/admin.py` — new fieldset + `get_readonly_fields` override
- `ourlives/migrations/` — new migration file
