## 1. Add payment_success view

- [x] 1.1 Add `payment_success` view function in `ourlives/views.py` that reads `token_count` and `session_id` from GET params, calls `messages.success()`, and redirects to `admin:ourlives_appsettings_change`
- [x] 1.2 Register the `success/` URL in `ourlives/urls.py` pointing to `payment_success`

## 2. Fix redirect destination

- [x] 2.1 In `create_checkout` view, change `success_url` to use `reverse("payment_success")` with `token_count` and `{CHECKOUT_SESSION_ID}` params
- [x] 2.2 Keep `cancel_url` pointing to the purchase page (existing behavior)

## 3. Update tests

- [x] 3.1 Add assertion in `test_successful_checkout_redirects` to verify `success_url` contains `/stripe/success/` with `token_count` and `CHECKOUT_SESSION_ID`, and `cancel_url` contains `/admin/ourlives/appsettings/purchase/`
- [x] 3.2 Add `test_payment_success_redirects_to_settings` for the `payment_success` view — asserts redirect to `admin:ourlives_appsettings_change` with message set
- [x] 3.3 Run full test suite to confirm no regressions
