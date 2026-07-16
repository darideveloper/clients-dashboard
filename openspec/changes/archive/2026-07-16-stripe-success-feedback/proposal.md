## Why

After a Stripe payment, users are redirected back to the purchase form page (`/admin/ourlives/appsettings/purchase/`) which shows the same empty form — no confirmation that the payment succeeded, no indication of credits added. The user has to navigate to the settings page manually and has no feedback at all.

## What Changes

- Change the Stripe `success_url` from the purchase page to the AppSettings change form (`/admin/ourlives/appsettings/`)
- Add a new `/stripe/success/` view that receives the redirect with `token_count` and Stripe `session_id`, sets a Django success message via `messages.success()`, and redirects to the admin settings page
- Register the new URL in `ourlives/urls.py`
- Keep `cancel_url` pointing back to the purchase page (user may want to retry)

## Capabilities

### New Capabilities

None — adding feedback to an existing flow, not a new capability.

### Modified Capabilities

- `credit-purchase`: Add requirements for post-payment UX — success feedback message and redirect destination

## Impact

- `ourlives/views.py` — modify `create_checkout` to set `success_url` to new `/stripe/success/` endpoint; add `payment_success` view
- `ourlives/urls.py` — register `success/` route
- `ourlives/tests.py` — update tests that assert on `success_url` contents; add tests for `payment_success` view
- No new dependencies
- No migration or config changes
