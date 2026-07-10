## Why

The Stripe purchase flow has two problems: (1) `float` arithmetic causes off-by-1-cent errors when converting amounts to Stripe's smallest currency unit, and (2) customers are forced to pay in USD regardless of their local currency — incurring foreign transaction fees and poor UX.

## What Changes

- **Fix decimal precision**: Replace `float` with `Decimal` throughout the purchase pipeline (view input parsing, token calculation, cent conversion) with Decimal arithmetic (truncation — always exact for 2dp DecimalField)
- **Keep inline price_data with Adaptive Pricing**: Use `price_data` with `currency="usd"`, `unit_amount` (per-token in cents), and `quantity` (token count). Enable `adaptive_pricing={"enabled": True}` on Checkout Sessions — Stripe auto-detects customer locale and converts USD to local currency at Stripe's market rate (over 100 currencies supported)
- **Card-only payment methods**: Set `payment_method_types=["card"]` to restrict payment methods and ensure consistent multi-currency display
- **Customer email**: Pass `customer_email` when available (enables Stripe location-based currency testing via `+location_XX` suffix)
- **New model fields**: `StripeEvent.presentment_currency`, `StripeEvent.presentment_amount` for audit trail; `AppSettings.stripe_price_id` and `AppSettings.stripe_product_id` for optional Stripe Price/Product references
- **Webhook handling**: Capture `presentment_details` from `checkout.session.completed` events

## Capabilities

### New Capabilities
- `credit-purchase`: Token purchase via Stripe with proper decimal precision, inline `price_data` checkout, and multi-currency adaptive pricing

### Modified Capabilities
*(none — no existing specs for Stripe/purchase flow)*

## Impact

- `ourlives/models.py` — new fields on `AppSettings` and `StripeEvent`; `calculate_token_count` signature unchanged
- `ourlives/stripe.py` — rewrite `create_checkout_session` to use `price_data` with `unit_amount_cents+quantity`; add `adaptive_pricing`, `payment_method_types`, `customer_email` params
- `ourlives/views.py` — `create_checkout` uses `Decimal` for parsing; calculates `unit_amount_cents` from `price_per_token`; validates `price_per_token > 0`
- `ourlives/admin.py` — Stripe fieldset with readonly `stripe_product_id`/`stripe_price_id`; "Run Sync Stripe Price" button styled as Unfold primary button, gated behind `is_superuser`; `purchase_view` shows `is_configured` flag (based on `price_per_token`)
- `ourlives/tests.py` — update all tests for Decimal input, `price_data` sessions, `payment_method_types`, `customer_email`, multi-currency audit trail
- **Stripe SDK**: upgrade `stripe` Python package from v15 to latest (needed for `adaptive_pricing` parameter support)
- **Optional**: `sync_stripe_price` management command for admin reference (Stripe Product/Price). Checkout does not require it — `price_data` works independently
