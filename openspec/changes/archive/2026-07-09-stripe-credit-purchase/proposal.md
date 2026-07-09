## Why

The invitation code system tracks tokens via `AppSettings.total_tokens`, but there is no way to buy more tokens. Administrators need an in-app purchase flow backed by Stripe, with webhook-based auto-fulfillment and credentials isolated from the admin interface.

## What Changes

- Add `price_per_token` and `min_purchase_amount` fields to `AppSettings` so the cost model is configurable in admin
- Add `StripeEvent` model for audit trail of processed webhook events, with read-only admin registration and a `source` field to distinguish between apps using the same Stripe account
- Add Stripe credentials to env vars (`STRIPE_SECRET_KEY`, `STRIPE_WEBHOOK_SECRET`) following existing dotenv patterns — never stored in DB or shown in admin
- Add standalone "Purchase Credits" admin page accessible via custom admin view registered on `AppSettingsAdmin`, gated on `has_module_perms("ourlives")` — any user with ourlives model permissions can access, not just those with `change_appsettings`
- Add sidebar navigation link for the purchase page via `UNFOLD["SIDEBAR"]["navigation"]` and extend the navigation template to render `sidebar_navigation` items
- Add admin endpoint that creates a Stripe Checkout Session and redirects the user to Stripe's hosted payment page (validates token count >= 1 before creating the session, rejecting purchases where the amount is below `price_per_token`)
- Add webhook endpoint that receives Stripe events, verifies signatures, dispatches by `source` metadata (preparing for future multi-app payments on the same Stripe account), and increments `total_tokens` for ourlives-sourced events
- Add `stripe` package to requirements.txt
- Register new URLs under `/stripe/` namespace, included from root URLconf

## Capabilities

### New Capabilities

- `stripe-credentials`: Environment-only Stripe configuration (secret key + webhook signing secret) with no admin surface, following the project's existing `os.getenv()` pattern
- `credit-purchase`: Standalone admin purchase page accessible to any ourlives user (not just AppSettings editors), sidebar navigation link, and backend flow to initiate a Stripe Checkout Session with metadata-bound token count, price-per-token ratio, and minimum purchase enforcement
- `stripe-webhook`: Secure webhook receiver that validates Stripe signatures, dispatches events by `source` metadata to correct app handler (enabling future multi-app payments), processes checkout completion events idempotently, and atomically increments `AppSettings.total_tokens` plus logs the event

### Modified Capabilities

_None._ No existing spec requirements change. `AppSettings` gains two new fields but the invitation code validation rules and token pool semantics are unchanged.

## Impact

- **Dependencies**: New `stripe` Python package added to `requirements.txt`
- **Env files**: `.env.dev` and `.env.prod` gain `STRIPE_SECRET_KEY` and `STRIPE_WEBHOOK_SECRET`
- **Settings**: `project/settings.py` reads two new env vars; `UNFOLD["SIDEBAR"]["navigation"]` gains a "Purchase Credits" item
- **Templates**: `project/templates/unfold/helpers/navigation.html` extended to render `sidebar_navigation` items after `available_apps`; new `ourlives/templates/admin/ourlives/purchase.html` for the standalone purchase page
- **Models**: `AppSettings` gains two fields (new migration); new `StripeEvent` model with `source` field for multi-app audit (new migration)
- **URLs**: `project/urls.py` includes `ourlives.urls`; new `ourlives/urls.py` with `/stripe/` endpoints; `AppSettingsAdmin` registers custom admin view at `/admin/ourlives/appsettings/purchase/`
- **Admin**: `AppSettingsAdmin` gains `custom_urls` with `purchase_view` method; new read-only `StripeEventAdmin` for audit trail; `can_purchase` permission helper for sidebar visibility
- **Views**: new `create_checkout` and `webhook` views in `ourlives/views.py`
- **Stripe service**: new `ourlives/stripe.py` module encapsulating Stripe API calls
- **Tests**: new test suite covering checkout session creation, webhook processing, idempotency, and validation
