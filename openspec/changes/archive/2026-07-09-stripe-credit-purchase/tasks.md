## 1. Dependencies and Environment

- [x] 1.1 Add `stripe` to `requirements.txt` with pinned version
- [x] 1.2 `pip install` the new dependency
- [x] 1.3 Add `STRIPE_SECRET_KEY` and `STRIPE_WEBHOOK_SECRET` to `.env.dev` with placeholder values
- [x] 1.4 Add `STRIPE_SECRET_KEY` and `STRIPE_WEBHOOK_SECRET` to `.env.prod` with placeholder values
- [x] 1.5 Read both env vars in `project/settings.py` following existing `os.getenv()` pattern (default to empty string so missing keys don't crash at import time)

## 2. Models and Migrations

- [x] 2.1 Add `price_per_token` and `min_purchase_amount` DecimalFields to `AppSettings` model (`max_digits=10, decimal_places=2`)
- [x] 2.2 Add `clean()` validation — reject negative values only; zero means unconfigured (purchase view gates at runtime)
- [x] 2.3 Create `StripeEvent` model with fields: `stripe_event_id` (CharField, max_length=255, unique=True), `source` (CharField, max_length=50), `token_count` (PositiveIntegerField), `amount_cents` (PositiveIntegerField — the amount in smallest currency units from Stripe's event payload), `handled_at` (DateTimeField, auto_now_add=True)
- [x] 2.4 Generate and review migration: `python manage.py makemigrations ourlives`
- [x] 2.5 Run migration: `python manage.py migrate`

## 3. Stripe Service Module

- [x] 3.1 Create `ourlives/stripe.py` module
- [x] 3.2 Implement `create_checkout_session(amount_usd, token_count, app_settings_id, success_url, cancel_url)` — creates Stripe Checkout Session with metadata `{source: "ourlives", token_count, app_settings_id}` and returns the checkout URL
- [x] 3.3 Implement `verify_webhook_signature(payload, signature)` — verifies Stripe-Signature header using `STRIPE_WEBHOOK_SECRET`
- [x] 3.4 Add stripe API key configuration from `settings.STRIPE_SECRET_KEY` on module init

## 4. Core Backend Logic

- [x] 4.1 Implement `calculate_token_count(amount, price_per_token)` in `ourlives/models.py` — pure function using `Decimal` floor division (`amount // price_per_token`), returning integer tokens
- [x] 4.2 Implement `process_ourlives_checkout_completion(stripe_event)` in `ourlives/models.py` — extracts `source`, `token_count`, `app_settings_id` from metadata, atomically increments `total_tokens` via `select_for_update()`, creates `StripeEvent` record with `source` and idempotency guard
- [x] 4.3 Handle mismatched `app_settings_id`: if the metadata's `app_settings_id` doesn't match the current singleton's PK, log a warning but still apply the tokens (the metadata's `token_count` is the source of truth; the singleton may have been recreated)

## 5. Sidebar Navigation

- [x] 5.1 Add `can_purchase` helper function in `ourlives/admin.py` — returns `request.user.is_staff and request.user.has_module_perms("ourlives")`
- [x] 5.2 Add "Purchase Credits" item to `UNFOLD["SIDEBAR"]["navigation"]` in `project/settings.py` with icon `shopping_cart`, separator, and permission callback pointing to `ourlives.admin.can_purchase`
- [x] 5.3 Extend `project/templates/unfold/helpers/navigation.html` — after the `available_apps` loop, add a block that iterates `sidebar_navigation` groups and renders items with `has_permission` check, preserving existing `available_apps` rendering unchanged

## 6. Standalone Purchase Page

- [x] 6.1 Add `custom_urls` on `AppSettingsAdmin` registering a `purchase/` path pointing to `purchase_view`
- [x] 6.2 Implement `purchase_view(self, request)` method on `AppSettingsAdmin` — checks `has_module_perms("ourlives")`, reads `AppSettings` singleton, renders `admin/ourlives/purchase.html` with price config and token pool stats
- [x] 6.3 Create template `ourlives/templates/admin/ourlives/purchase.html` — extends `admin/base_site.html`, renders number input with `min` bound to `min_purchase_amount`, "Buy Credits" button, live token count preview via JS, and disabled state when pricing is unconfigured
- [x] 6.4 Add client-side JS — on amount input change, update preview `floor(amount / price_per_token)`; on form submit, POST to `/stripe/create-checkout/` with CSRF token; handle `min_purchase_amount` and `price == 0` states
- [x] 6.5 Ensure `success_url` and `cancel_url` for Stripe Checkout Sessions point to `/admin/ourlives/appsettings/purchase/`

## 7. Admin Registrations

- [x] 7.1 Add `price_per_token` and `min_purchase_amount` to `AppSettingsAdmin.fieldsets` in a "Pricing" fieldset
- [x] 7.2 Register `StripeEventAdmin` (read-only) inheriting `ModelAdminUnfoldBase` with `list_display` of `stripe_event_id`, `source`, `token_count`, `amount_cents`, `handled_at` and all fields set as `readonly_fields`

## 8. URLs and Views

- [x] 8.1 Create `ourlives/urls.py` with paths: `create-checkout/`, `webhook/`
- [x] 8.2 Include `ourlives.urls` in `project/urls.py` with `path("stripe/", include("ourlives.urls"))` — final URLs: `/stripe/create-checkout/`, `/stripe/webhook/`
- [x] 8.3 Implement `create_checkout` view — validates `request.user.has_module_perms("ourlives")` (403 if not), validates amount >= `min_purchase_amount`, validates `price_per_token > 0`, validates calculated `token_count >= 1` (rejects with error if amount too low), creates checkout session, returns redirect
- [x] 8.4 Implement `webhook` view — parses raw body, verifies `Content-Type: application/json` (400 if not), verifies Stripe signature (400 if missing/invalid), dispatches by `source` metadata: if `source == "ourlives"` calls `process_ourlives_checkout_completion`, otherwise logs warning and returns 200; returns 200 for unknown event types
- [x] 8.5 Add `@csrf_exempt` on webhook view, `@require_POST` on both views

## 9. Tests

- [x] 9.1 Test `AppSettings.clean()` rejects negative `price_per_token` and `min_purchase_amount`, allows zero
- [x] 9.2 Test `calculate_token_count` with exact and non-exact divisions
- [x] 9.3 Test `create_checkout_session` mock — verifies correct metadata and amount are sent to Stripe
- [x] 9.4 Test `purchase_view` — ourlives user gets 200 with form rendered, non-ourlives user gets 403
- [x] 9.5 Test `purchase_view` — pricing unconfigured shows disabled state, pricing configured shows active form
- [x] 9.6 Test `create_checkout` view validates ourlives permission (403 if missing), minimum amount, missing price, and zero tokens (amount < price_per_token)
- [x] 9.7 Test `webhook` view with valid signature processes event and increments `total_tokens`
- [x] 9.8 Test `webhook` view with invalid signature returns 400
- [x] 9.9 Test `webhook` view with missing `Stripe-Signature` header returns 400
- [x] 9.10 Test `webhook` view with wrong `Content-Type` returns 400
- [x] 9.11 Test duplicate webhook event is idempotent (second processing does not change `total_tokens`)
- [x] 9.12 Test `StripeEvent` unique constraint on duplicate `stripe_event_id`
- [x] 9.13 Test `StripeEvent` saves `source` field correctly from metadata
- [x] 9.14 Test webhook dispatches `source="ourlives"` to ourlives handler
- [x] 9.15 Test webhook with unknown `source` logs warning and returns 200 without modifying tokens
- [x] 9.16 Test webhook with missing `source` metadata logs warning and returns 200
- [x] 9.17 Test webhook still applies tokens when `app_settings_id` metadata differs from singleton PK (log warning, tokens applied)
- [x] 9.18 Test `can_purchase` returns True for ourlives staff user, False for non-ourlives staff and non-staff users
- [x] 9.19 Test `StripeEventAdmin` renders read-only list with expected columns including `source`
- [x] 9.20 Test sidebar renders "Purchase Credits" link for ourlives user and hides it for non-ourlives user
- [x] 9.21 Run full test suite: `python manage.py test ourlives`

## 10. Deployment

- [ ] 10.1 Configure Stripe webhook endpoint in Stripe dashboard pointing to `https://<host>/stripe/webhook/`
- [ ] 10.2 Restrict `/stripe/webhook/` to Stripe's IP ranges (https://stripe.com/docs/ips) at the reverse proxy level (e.g., nginx `allow`/`deny` directives)
