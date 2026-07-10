## 1. Data Model & Migration

- [x] 1.1 Add `stripe_product_id` field to `AppSettings` model (CharField, max_length=255, blank=True)
- [x] 1.2 Add `stripe_price_id` field to `AppSettings` model (CharField, max_length=255, blank=True)
- [x] 1.3 Add `presentment_currency` and `presentment_amount` fields to `StripeEvent` model
- [x] 1.4 Update `StripeEvent.amount_cents` help text to clarify it's settlement amount
- [x] 1.5 Generate and apply migration

## 2. Stripe Price Sync Command

- [x] 2.1 Create `management/commands/sync_stripe_price.py` that:
  - Guards: skips if `price_per_token <= 0` (purchases disabled)
  - Uses `AppSettings.stripe_product_id` if set, else `STRIPE_PRODUCT_ID` from settings, else creates Product
  - Archives existing Price via `active=False` (wraps in try/except for deleted Prices)
  - Creates new Price with `unit_amount=int(price_per_token * 100)`, `currency="usd"`, no `currency_options`
  - Stores resulting IDs in `AppSettings.stripe_price_id` and `AppSettings.stripe_product_id`
- [x] 2.2 Command handles `STRIPE_PRODUCT_ID` from Django settings for existing Product reuse

## 3. Stripe Module Rewrite

- [x] 3.1 Rewrite `create_checkout_session` to accept `unit_amount_cents`, `quantity`, `app_settings_id`, `success_url`, `cancel_url`, `customer_email`
- [x] 3.2 Build `line_items` with `price_data` (`currency="usd"`, `unit_amount`, `product_data`) and `quantity`
- [x] 3.3 Add `adaptive_pricing={"enabled": True}` to Session create call
- [x] 3.4 Set `payment_method_types=["card"]` and pass `customer_email` conditionally (only when non-empty); keep metadata unchanged

## 4. Decimal Precision Fix in Views

- [x] 4.1 Parse `amount` as `Decimal(data.get("amount", "0"))` from raw string in `create_checkout` view
- [x] 4.2 Remove `float()` conversion for `min_purchase_amount` comparison — compare as `Decimal` directly
- [x] 4.3 Pass `Decimal` amount directly to `calculate_token_count()` without `str()` round-trip
- [x] 4.4 Validate `AppSettings.price_per_token > 0` — return 400 if price not configured
- [x] 4.5 Update error messages and validation to use Decimal formatting

## 5. Webhook Presentment Details

- [x] 5.1 Extract `presentment_details.presentment_currency` and `presentment_details.presentment_amount` from webhook payload
- [x] 5.2 Store new fields when creating `StripeEvent` records in `process_ourlives_checkout_completion`

## 6. Admin & Settings

- [x] 6.1 Display `stripe_price_id` in `AppSettingsAdmin` (read-only, auto-populated)
- [x] 6.2 Update `admin.py` purchase view `is_configured` to check `price_per_token > 0` instead of `stripe_price_id`
- [x] 6.3 Add "Run Sync Stripe Price" button as readonly field in Stripe fieldset:
  - Rendered via `format_html` as `<a>` tag with Unfold primary button Tailwind classes (`bg-primary-600`, `text-white`, etc.)
  - Visible only to superusers (`request.user.is_superuser`); non-admins see `"-"`
  - Links to custom `sync-stripe-price/` URL registered via `get_urls()`
  - View triggers `sync_stripe_price` management command, redirects back
  - View also gated behind `is_superuser` (not just `has_module_perms`)

## 7. Stripe SDK Upgrade

- [x] 7.1 Upgrade `stripe` Python package from v15 to v15.4+ (pre-release with API version 2026-06-24.preview)
- [x] 7.2 Verify `stripe.checkout.Session.create` accepts `adaptive_pricing={"enabled": True}`

## 8. Tests

- [x] 8.1 Update `CreateCheckoutSessionTests` for `price_data` approach (verify `unit_amount_cents`, `quantity`, `adaptive_pricing`, `payment_method_types`, `customer_email`)
- [x] 8.2 Update `CreateCheckoutViewTests` for Decimal input parsing, price_per_token > 0 validation
- [x] 8.3 Update `WebhookViewTests` for `presentment_details` fields
- [x] 8.4 Update `StripeEventModelTests` for new fields
- [x] 8.5 Add tests for `sync_stripe_price` management command (zero-price skip, Product/Price creation, re-run)
- [x] 8.6 Run full test suite and verify all pass
