## Context

The `ourlives` app manages invitation codes for projects. `AppSettings` (a `django-solo` singleton) holds `total_tokens` — the global cap on all invitation code `max_use` assignments. There is no way to increase `total_tokens` except through direct DB/admin edits. Operators need a self-service purchase flow.

The project uses Django 5.2, DRF, django-unfold (admin theme), and reads all configuration from env files via `python-dotenv`. It has no existing Stripe integration, webhook infrastructure, or payment logic.

## Goals / Non-Goals

**Goals:**
- Allow any user with ourlives model permissions to purchase invitation code tokens, not just AppSettings editors
- Store Stripe credentials exclusively in env files, never in the DB or admin UI
- Use Stripe Checkout (hosted) so no PCI scope in the application
- Auto-fulfill purchases via Stripe webhooks with idempotency guarantees
- Keep all code within the `ourlives` app; do not touch `core` or other apps

**Non-Goals:**
- Subscription/recurring billing
- Stripe Customer portal or saved payment methods
- Refund handling
- Non-Stripe payment methods
- Per-project pricing tiers
- Email notifications for purchases

## Decisions

### 1. Stripe Checkout Sessions over Stripe Elements

**Decision**: Use Stripe's hosted Checkout page.

**Rationale**: No card fields in our admin, zero PCI scope, fewer lines of code to maintain, and the admin is an authenticated backend — redirect to Stripe is acceptable UX. The project has no custom frontend requiring inline payment UI.

### 2. Metadata-based fulfillment

**Decision**: Pass `{source, token_count, app_settings_id}` in the Checkout Session metadata. The webhook reads the `source` field to dispatch to the correct app handler, then extracts `token_count` to determine how many tokens to add.

**Rationale**: Metadata travels with the Checkout Session and arrives in the `checkout.session.completed` event payload. This avoids re-deriving tokens from `amount_total / price_per_token`, which would produce incorrect results if the price changes between session creation and webhook delivery. The `source` field (`"ourlives"`) enables a single webhook endpoint to handle future payments from other apps on the same Stripe account — each app's handler is isolated. The `app_settings_id` is included for defense-in-depth: if the AppSettings singleton is deleted and recreated (changing its PK), the handler logs a warning but still applies the tokens — the metadata's `token_count` is the source of truth. The `amount_total` from Stripe (in cents) is also recorded in `StripeEvent.amount_cents` for audit, independent of metadata.

### 3. Idempotency via StripeEvent model

**Decision**: Store every processed webhook event ID in a `StripeEvent` model with a unique constraint on `stripe_event_id`. Before processing, check if the event was already handled.

**Rationale**: Stripe may retry webhook delivery. Without idempotency, `total_tokens` would be incremented twice for the same payment. The DB unique constraint is the simplest and most reliable guard.

### 4. Atomic token increment

**Decision**: `select_for_update()` on the `AppSettings` row before incrementing `total_tokens`, wrapped in `transaction.atomic()`.

**Rationale**: Matches the existing pattern in `InvitationCode.save()`. Prevents race conditions between simultaneous webhook deliveries.

### 4b. Decimal → integer cents conversion

**Decision**: The amount supplied by the user (Decimal, e.g. `5.00`) is converted to integer cents via `int(amount * 100)` before being sent to Stripe. The Stripe library's `checkout.Session.create()` receives `unit_amount` in cents as an integer. The webhook handler reads `amount_total` from Stripe's event payload (already in cents) and stores it directly in `StripeEvent.amount_cents`.

**Rationale**: Stripe's API operates in the smallest currency unit (cents for USD). Storing the converted integer cents in `StripeEvent.amount_cents` avoids future confusion about whether the field holds dollars or cents. The conversion only happens at the API boundary in `ourlives/stripe.py` — views and templates work exclusively in Decimal dollars.

### 4c. Webhook content-type guard

**Decision**: The webhook view checks `request.content_type == "application/json"` before processing. If the content type is anything else, return 400 immediately.

**Rationale**: Stripe always sends webhooks with `Content-Type: application/json`. A mismatched content type indicates a non-Stripe caller or a misconfigured proxy. This is cheap defense-in-depth before reaching signature verification and costs one line.

### 5. Env vars for secrets, not DB

**Decision**: `STRIPE_SECRET_KEY` and `STRIPE_WEBHOOK_SECRET` are read from env only. No model fields, no admin UI, no `CharField` masked with widgets.

**Rationale**: Secrets in env files are already the project convention. DB storage of secrets adds attack surface (backups, replication, admin exports). Django's admin has no built-in "masked secret" widget that prevents reading the raw value from `request.POST` — even a custom widget would leak the plaintext secret through the admin form submission in transit.

### 6. `ourlives/stripe.py` service module

**Decision**: Encapsulate all Stripe API interactions (`stripe` library calls, session creation, webhook signature verification) in a dedicated module `ourlives/stripe.py`. Pure business logic (`calculate_token_count`, `process_ourlives_checkout_completion`) lives in `ourlives/models.py` alongside the `AppSettings` model that owns the pricing config.

**Rationale**: Keeps views thin and testable. The module can be mocked independently in tests without importing Stripe. Separating Stripe API surface from domain logic means `calculate_token_count` (a pure function using `Decimal` floor division) has zero Stripe dependency.

### 7. Standalone admin purchase view via `custom_urls`

**Decision**: Register a custom admin view on `AppSettingsAdmin` via `custom_urls` at `/admin/ourlives/appsettings/purchase/`. The view is a function-based method `purchase_view(request)` that renders a standalone purchase page inside the admin shell. Access is gated on `request.user.has_module_perms("ourlives")` — any staff user with at least one ourlives model permission can access, regardless of `change_appsettings`.

**Rationale**: The `AppSettings` change form requires `change_appsettings` permission, which is typically reserved for project admins. Users who manage projects and invitation codes (with `view_project`, `change_invitationcode`, etc.) need to buy tokens but should not edit pricing. A standalone page decouples the purchase action from editing privileges. The `custom_urls` mechanism is unfold's built-in way to add views under a model's admin namespace — no hacks, no phantom models.

### 8. URL namespace `/stripe/`

**Decision**: Add `ourlives/urls.py` with paths `create-checkout/` and `webhook/` (relative), then include in `project/urls.py` as `path("stripe/", include("ourlives.urls"))`. Final URLs: `/stripe/create-checkout/` and `/stripe/webhook/`.

**Rationale**: Current project has no app-level URL files. The `/stripe/` prefix groups related endpoints cleanly. The webhook path should be clear and predictable for Stripe dashboard configuration. The `ourlives/urls.py` file establishes a pattern for future app URL modules.

### 9. DecimalField precision

**Decision**: `price_per_token` and `min_purchase_amount` use `DecimalField(max_digits=10, decimal_places=2)`.

**Rationale**: Avoids arbitrary-precision storage that can cause rounding mismatches with Stripe's integer cent amounts. Two decimal places match USD currency. Ten total digits allow values up to $99,999,999.99.

### 10. Price field allows zero (not configured)

**Decision**: `AppSettings.clean()` rejects negative values for `price_per_token` and `min_purchase_amount`, but allows zero. The purchase view checks at runtime and rejects purchases with `"price must be configured first"` when `price_per_token == 0`.

**Rationale**: After migration, existing `AppSettings` instances will have these fields set to `0.00` (the DecimalField default). If `clean()` rejects zero, admins would be locked out of saving any AppSettings change until they configure pricing. Separating persistence validation from business validation keeps the form always saveable while gating purchases on proper configuration.

### 11. Sidebar navigation via `UNFOLD["SIDEBAR"]["navigation"]`

**Decision**: Add a "Purchase Credits" sidebar link via `UNFOLD["SIDEBAR"]["navigation"]` in `settings.py` with a `permission` callback (`ourlives.admin.can_purchase`) that resolves to `request.user.has_module_perms("ourlives")`. Extend the project's custom `navigation.html` template to render `sidebar_navigation` items after the existing `available_apps` loop, using the same DOM structure (collapsible groups with `<h2>` headers and `<ol>` model lists matching the `available_apps` visual style — Material icon, gap/padding, highlight on active path).

**Rationale**: The project's custom `navigation.html` template currently only renders `available_apps` (Django's standard permission-filtered model list) and completely ignores unfold's `sidebar_navigation` system. Adding ~12 lines to also render `sidebar_navigation` items enables custom sidebar links without losing the existing icon customization. The sidebar_navigation items use the same DOM contract as `available_apps` entries (<h2> header + <ol> list + Material icon + active-path highlighting) so the visual presentation is seamless. When `sidebar_navigation` is empty (the current default), nothing changes — fully backward compatible. This approach also future-proofs the sidebar for any future custom pages.

**Note**: This reverses an earlier architectural decision (archived change `2026-06-27-unfold-permission-based-sidebar`) that intentionally kept `sidebar_navigation=[]` and rendered everything from `available_apps`. The reversal is necessary because `available_apps` can only render model-based admin links — a custom purchase page has no model and must use `sidebar_navigation`.

### 12. Landing URL after checkout

**Decision**: `success_url` and `cancel_url` for Stripe Checkout Sessions point back to the standalone purchase page (`/admin/ourlives/appsettings/purchase/`), not the AppSettings change form.

**Rationale**: The user initiated the purchase from the standalone page. After payment (or cancellation), they should return there. The page shows live token counts so they can verify the updated balance.

### 13. Source-based webhook dispatch for multi-app payments

**Decision**: The single `/stripe/webhook/` endpoint uses a `source` metadata field to dispatch events. Currently only `"ourlives"` is handled. Future apps register their handler by adding an `elif` branch. The `StripeEvent` model includes a `source` CharField so audit records are filterable by app.

**Rationale**: Future apps (e.g., `core`) may need Stripe payments under the same Stripe account and webhook endpoint. A dispatcher pattern keeps each app's fulfillment logic independent. Three small upfront costs — one metadata field, one model field, one `if/elif` — prevent a later redesign.

## Risks / Trade-offs

- **Webhook never arrives**: If Stripe cannot reach the server (firewall, DNS, downtime), tokens are never credited but the user was charged.  
  → Mitigation: Stripe retries webhooks with exponential backoff for up to 3 days. The webhook endpoint logs failures. For production, configure Stripe dashboard alerts for webhook delivery failures.

- **Price change between checkout and webhook**: If an admin changes `price_per_token` after a session is created but before the webhook processes, the token count in metadata is already fixed.  
  → Mitigation: This is correct behavior — metadata carries the token count that was shown to the buyer at purchase time. No risk of discrepancy.

- **Checkout session expires**: Stripe Checkout sessions created via API expire after 24 hours. If the user abandons the payment page, no tokens are consumed and no webhook fires.  
  → Mitigation: This is harmless. The session simply expires.

- **Dual admin modifying AppSettings simultaneously**: The purchase UI only reads `price_per_token` and `min_purchase_amount`. The actual increment happens in the webhook, which uses `select_for_update()` — safe against parallel edits.

- **`stripe` package version churn**: The `stripe` Python library has frequent major releases.  
  → Mitigation: Pin a specific version in `requirements.txt`. The `ourlives/stripe.py` module isolates all Stripe API surface so upgrading is contained.

- **Unprotected webhook endpoint**: `/stripe/webhook/` is publicly accessible (no auth). Malicious callers could flood the endpoint with invalid payloads.  
  → Mitigation: Signature verification rejects all non-Stripe payloads (400). For production, restrict the webhook endpoint to Stripe's IP ranges (see https://stripe.com/docs/ips) at the reverse proxy/load balancer level. This is documented in the migration plan.

- **Rate limiting on checkout creation**: `/stripe/create-checkout/` could be spammed by an authenticated user, creating many Stripe Checkout Sessions. Stripe doesn't charge for session creation, and sessions expire after 24 hours, so the blast radius is noise, not financial.  
  → Mitigation: Not addressed in v1. Document as a follow-up improvement (e.g., throttle to N sessions per minute per user).

- **Zero-token purchase**: If `min_purchase_amount < price_per_token`, `floor(amount / price_per_token)` yields 0 tokens. The user would pay without receiving tokens.  
  → Mitigation: The `create_checkout` view validates that `token_count >= 1` before creating a Stripe session. The purchase page's client-side preview also shows 0 tokens so the user can see this before submitting. The `AppSettings.clean()` does not enforce `min_purchase_amount >= price_per_token` because zero values (unconfigured) are allowed — the runtime gate in the view is the authoritative check.

## Migration Plan

1. Add `stripe` to `requirements.txt` and install
2. Add `STRIPE_SECRET_KEY` and `STRIPE_WEBHOOK_SECRET` to env files with placeholder values
3. Add env var reads in `settings.py`
4. Create migrations for `AppSettings` new fields and `StripeEvent` model
5. Deploy code, run migrations, set real values in production env
6. Configure Stripe webhook endpoint in Stripe dashboard pointing to `https://<host>/stripe/webhook/`
7. Restrict the `/stripe/webhook/` path to Stripe's IP ranges (https://stripe.com/docs/ips) at the reverse proxy/load balancer level (nginx `allow`/`deny` directives)
8. Test with Stripe test mode keys first

**Rollback**: Remove env vars, revert `requirements.txt`, reverse migrations. No data loss risk — `total_tokens` increments are additive and don't break existing invitation codes.
