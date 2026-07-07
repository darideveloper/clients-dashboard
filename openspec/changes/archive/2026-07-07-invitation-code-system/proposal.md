## Why

The `ourlives` app needs an invitation code system to gate access. Admins need to create projects, generate invitation codes with configurable usage limits, and track token consumption. An external service will consume codes by incrementing `current_use` directly in the DB. A singleton settings model is required to manage the global token pool and enforce allocation limits.

## What Changes

- Create **Project** model (name, description) in `ourlives/`
- Create **InvitationCode** model (project FK, code, is_active, max_use, current_use) in `ourlives/`
- Create **AppSettings** singleton model (total_tokens + computed status properties) via django-solo
- Add token pool validation: `SUM(max_use)` of all codes must never exceed `total_tokens`
- Add DB-level check constraint: `current_use <= max_use`
- Register `ourlives` in `INSTALLED_APPS`
- Register all models in admin with django-unfold styling
- No API layer — management-only via admin panel; external service reads/writes DB directly

## Capabilities

### New Capabilities
- `invitation-code-system`: Admin management of projects, invitation codes, and token pool settings. Enforces allocation limits and exposes token utilization status.

### Modified Capabilities

None. This is a new app with no existing capabilities.

## Impact

- `project/settings.py`: Add `"ourlives"` to `INSTALLED_APPS`
- `ourlives/models.py`: 3 new models (Project, InvitationCode, AppSettings)
- `ourlives/admin.py`: 3 new ModelAdmin classes
- `ourlives/tests.py`: Token validation tests, constraint tests
- DB: 3 new tables + 1 check constraint
- External service: Reads/writes `current_use` on `InvitationCode` table directly
