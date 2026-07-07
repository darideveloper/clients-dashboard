## Why

The invitation code admin form crashes with a Django debug error page (ValidationError) instead of showing a user-friendly form error when a user tries to create/update an invitation code that exceeds the token pool or violates business rules. This is because validation logic lives in `InvitationCode.save()` (inside a database lock/transaction) rather than in `Model.clean()`, where Django's admin form validation pipeline catches `ValidationError` and renders inline error messages.

## What Changes

- Add `InvitationCode.clean()` method containing token pool and max_use-vs-current_use validations so Django admin catches them as inline form errors
- Keep the `select_for_update` lock-based checks in `save()` as a race-condition safety net, but convert them so they don't raise `ValidationError` into the void
- Override `save_model()` in `InvitationCodeAdmin` to catch any `ValidationError` that still escapes (rare race condition) and display it as a Django message instead of crashing
- `full_clean()` call in `save()` is already before the transaction block — keep as-is (no change needed)
- `AppSettings` model: token pool validation now prevents reducing `total_tokens` below `tokens_assigned` (currently allows it, creating a state where no codes can be created but existing over-assignment persists)

## Capabilities

### New Capabilities
- `invitation-code-validation`: Token pool and business rule validation shown as inline form errors in Django admin, with race-condition-safe fallback

### Modified Capabilities
<!-- None - this is a bug fix, no existing spec behavior changes -->

## Impact

- **Modified**: `ourlives/models.py` — `InvitationCode.save()` and new `clean()` method; `AppSettings.save()` for pool reduction guard
- **Modified**: `ourlives/admin.py` — `InvitationCodeAdmin.save_model()` override
- **Modified**: `ourlives/tests.py` — existing tests may need adjustment for the new validation location
