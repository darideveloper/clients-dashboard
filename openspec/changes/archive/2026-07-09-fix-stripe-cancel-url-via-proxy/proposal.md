## Why

Starting at `https://clients.localhost`, purchasing credits then canceling a Stripe payment redirects to `http://127.0.0.1:8000` (plain HTTP on internal IP) instead of back to `https://clients.localhost`. This breaks the user experience — they lose HTTPS and the domain name — and happens because `request.build_absolute_uri()` uses the `Host` header which the reverse proxy (`portless`) rewrites to the internal address.

## What Changes

- Replace `request.build_absolute_uri()` in `create_checkout` view with a method that yields the correct external URL regardless of proxy setup
- No new capabilities, no config changes, no new dependencies
- Single-line fix in `ourlives/views.py:59`

## Capabilities

### New Capabilities

None. This fixes an existing capability, it does not add a new one.

### Modified Capabilities

- `proxy-safe-url-resolution`: The Stripe credit checkout flow generates `cancel_url` and `success_url` that are sent to Stripe. Currently these URLs are wrong when Django is behind a reverse proxy (portless, nginx, traefik, etc.). No spec change needed — the requirements (correct external URLs) are unchanged, only the implementation is wrong.

## Impact

- `ourlives/views.py:59`: single line change to how `purchase_url` is computed
- `ourlives/stripe.py`: no changes needed (already receives the correct URL)
- Tests: existing test `test_successful_checkout_redirects` still passes (it patches `create_checkout_session` and doesn't depend on actual URL resolution)
- Dev and production: works with any reverse proxy without requiring `USE_X_FORWARDED_HOST` or proxy config changes