## Why

Stripe webhook endpoint crashes with `AttributeError: get` because stripe-python v15 removed the `.get()` method from `StripeObject`. Every Stripe webhook event fails silently — payments process on Stripe's side but credits are never added, and no user-facing error occurs.

## What Changes

- Convert the `event` `StripeObject` to a plain dict early in the webhook handler using `to_dict()`
- Replace all `.get()` calls on Stripe objects in `views.py` and `models.py` with equivalent dict operations
- No behavior changes — the same fields are read with the same fallback logic

## Capabilities

### New Capabilities

None — this is a bug fix, not a new capability.

### Modified Capabilities

None — no spec-level requirement changes. Existing `credit-purchase` spec behavior is preserved.

## Impact

- `ourlives/views.py` — line 87: event converted via `to_dict()` before use; `.get()` → `[""]` + `in` checks
- `ourlives/models.py` — `process_ourlives_checkout_completion` receives a plain dict; all `.get()` calls work unchanged
- `ourlives/tests.py` — no changes needed if tests construct events as dicts (verify)
- No new dependencies
- No migration or config changes
