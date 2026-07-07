## Why

After successful login to Django admin, users are redirected to `/accounts/profile/` (Django's default `LOGIN_REDIRECT_URL`) which doesn't exist in this project. This causes a 404 or confusing experience. The correct post-login destination should be `/admin/`.

## What Changes

- Add `LOGIN_REDIRECT_URL = "/admin/"` to `project/settings.py`
- No other code changes needed

## Capabilities

### New Capabilities

None — this is a configuration fix, not a new capability.

### Modified Capabilities

None.

## Impact

- `project/settings.py` — add one setting
- No API, dependency, or schema changes
