## Context

The Stripe purchase flow uses inline `price_data` with `currency: "usd"` hardcoded. Monetary amounts flow through `float` at multiple points, causing off-by-1-cent errors (`int(10.99 * 100)` → 1098 instead of 1099). There is no multi-currency support — all customers are charged in USD regardless of location, incurring foreign transaction fees.

The system stores `price_per_token` in a `DecimalField` (USD), calculates tokens via `calculate_token_count()` (already Decimal-correct), then converts the amount to cents with float arithmetic before sending to Stripe.

## Goals / Non-Goals

**Goals:**
- Eliminate float precision loss by using `Decimal` throughout the entire purchase pipeline
- Keep inline `price_data` with Adaptive Pricing — checkout uses `price_data` directly, no Price required
- Enable Stripe Adaptive Pricing so customers see/pay in their local currency (auto-detected from IP, over 100 currencies)
- Store audit trail of the presented currency and amount in `StripeEvent`
- Provide a management command that auto-creates the required Stripe Product + Price with no dashboard setup

**Non-Goals:**
- Manual currency override dropdown (no need — Stripe auto-detects perfectly)
- Programmatic management of exchange rates (Stripe Adaptive Pricing handles conversion at market rates)
- Real-time exchange rate APIs (Stripe manages rates internally)
- Subscriptions or recurring billing (single `payment` mode only)
- Multiple Stripe Prices (sync_stripe_price creates one Price for admin reference; checkout uses `price_data` independently)

## Decisions

### D1: Decimal throughout the pipeline

**Decision**: Parse all monetary user input directly as `Decimal` from the raw string, keep as `Decimal` through all business logic, and eliminate the `float` → `str` → `Decimal` round-trip.

**Rationale**:
- The current code does `float(data.get("amount"))` then `Decimal(str(amount))` — this round-trips through float, losing precision at parse time
- `calculate_token_count()` already accepts `Decimal` correctly (floor division)
- Stripe Python SDK v15+ accepts `Decimal` for monetary fields
- With `price_data` approach, we convert per-token price to cents via `int(price_per_token * 100)` — a Decimal-safe `ROUND_DOWN` operation with no float involvement

**Impact**:
- `views.py`: Parse `amount = Decimal(data.get("amount", "0"))` from raw POST/JSON string
- `views.py`: Compare `amount >= min_purchase_amount` as `Decimal` (no float conversion)
- `views.py`: Pass `Decimal` amount directly to `calculate_token_count()` without str round-trip
- `views.py`: Convert `price_per_token` to cents via `unit_amount_cents = int(settings_obj.price_per_token * 100)`
- Template: Pass `price_per_token` and all amounts as formatted strings, JS uses `parseFloat` only for preview

### D2: Inline price_data with Stripe Adaptive Pricing

**Decision**: Use inline `price_data` with `currency="usd"`, `unit_amount` set to per-token price in USD cents, and `quantity` set to token count. Enable `adaptive_pricing={"enabled": True}` on the Checkout Session. Also set `payment_method_types=["card"]` (consistent with Stripe Checkout best practices for card-presented multi-currency) and pass `customer_email` when available (enables Stripe's location-based currency testing). Stripe auto-detects customer locale from IP and converts USD to local currency using Stripe's market rates (applying a 2-4% conversion fee).

**Rationale**:
- Zero configuration — no currency list, no exchange rates, no manual setup
- Stripe handles over 100 currencies automatically
- No Stripe Price object required — works immediately with any `price_per_token` value
- 2-4% fee is comparable to what customers pay in bank foreign transaction fees
- `presentment_details` in the webhook still captures what the customer saw
- `payment_method_types=["card"]` ensures consistent payment experience across currencies
- `customer_email` enables Stripe testing via `+location_MX` suffix and improves UX

**Flow**:
```
Admin enters $10 USD
→ tokens = floor(10 / 0.50) = 20
→ unit_amount_cents = int(0.50 * 100) = 50
→ Checkout Session:
     price_data={currency="usd", unit_amount=50, product_data={name: "Invitation Code Tokens"}}
     quantity=20
     adaptive_pricing={"enabled": True}
     payment_method_types=["card"]
     customer_email="user@example.com"
→ Stripe detects IP → DE customer → converts USD→EUR → presents €9.20
→ Webhook: currency="usd", amount_total=1000,
           presentment_details={presentment_currency="eur", presentment_amount=920}
```

**Why not `currency_options`?** The alternative approach required creating Stripe Prices with explicit per-currency rates, which needs manual exchange rate management. Adaptive Pricing with Stripe's rates eliminates all that — at the cost of a 2-4% fee on the exchange rate. This is the same range as typical bank FX fees and far simpler to maintain.

### D3: StripeEvent audit trail

**Decision**: Add `presentment_currency` (CharField, max_length=3) and `presentment_amount` (PositiveIntegerField) to `StripeEvent`. Rename existing `amount_cents` help text to clarify it's the settlement amount.

**Rationale**:
- `amount_cents` tracks what Stripe settles in the integration's currency (USD)
- `presentment_*` tracks what the customer actually saw and paid (in their local currency)
- Both are needed for reconciliation and audit

### D4: Price lifecycle management (optional sync command)

**Decision**: A management command (`sync_stripe_price`) creates a Stripe Product + Price for admin reference and stores both IDs on `AppSettings`. On first run, it creates a Product "Invitation Code Tokens" (persists ID in `stripe_product_id`) + a Price with `unit_amount = int(price_per_token * 100)` cents in USD (persists ID in `stripe_price_id`). When `price_per_token` changes, re-running the command creates a NEW Price (Prices are immutable), archives the old one, and updates `stripe_price_id`. Checkout does NOT require this Price — it uses `price_data` independently.

**Rationale**:
- Optional — checkout works without running this command
- Provides Stripe Product/Price references in admin for dashboard visibility
- Prices are immutable in Stripe (can't change `unit_amount`), so changes require a new Price
- Archiving old Prices keeps the Stripe dashboard clean
- Both IDs stored on AppSettings for full lifecycle traceability
- Command is safe to re-run — skips if `price_per_token <= 0`
- `STRIPE_PRODUCT_ID` in Django settings overrides Product lookup (e.g., reuse existing Product from another system)

### D5: Admin sync button — readonly field with superuser gate

**Decision**: The "Run Sync Stripe Price" button is rendered as a readonly field in the Stripe fieldset (inline with `stripe_product_id` and `stripe_price_id`), not as an `actions_detail` toolbar action. It uses Unfold's primary button Tailwind classes directly in `format_html` rather than the component system. Both the button visibility and the view that handles it are gated behind `request.user.is_superuser`.

**Rationale**:
- Inline placement keeps the sync action visually grouped with its related Stripe fields
- Tailwind classes bypass Unfold's component system for simplicity — button still picks up `--color-primary-600` from Unfold's theming
- `is_superuser` is stricter than `has_module_perms("ourlives")` (used by `purchase_view`) because syncing Stripe state is an infrastructure operation, not a business operation
- Non-admins see `"-"` instead of the button (no dead-click 403)

**Permission model divergence**:
```
purchase_view          → is_staff + has_module_perms("ourlives")
sync_stripe_price_view → is_superuser only
```
This is intentional: purchasing tokens is a routine admin operation, but syncing Stripe infrastructure is reserved for superusers.

**Pseudocode**:
```
sync_stripe_price:
  if app_settings.price_per_token <= 0:
    print("Skipping: price_per_token must be positive")
    return

  if app_settings.stripe_product_id:
    product_id = app_settings.stripe_product_id
  elif settings.STRIPE_PRODUCT_ID:
    product_id = settings.STRIPE_PRODUCT_ID
  else:
    product = stripe.Product.create(name="Invitation Code Tokens")
    app_settings.stripe_product_id = product.id
    product_id = product.id

  if app_settings.stripe_price_id:
    try:
      stripe.Price.modify(app_settings.stripe_price_id, active=False)
    except stripe.error.StripeError:
      pass  # old price may already be deleted

  cents = int(app_settings.price_per_token * 100)
  price = stripe.Price.create(
    product=product_id,
    unit_amount=cents,
    currency="usd",      # base currency for Adaptive Pricing
  )
  app_settings.stripe_price_id = price.id
  app_settings.save()
```

## Architecture

```
Purchase form (admin)
  │  POST amount=10.00
  ▼
create_checkout view
  │  amount = Decimal("10.00")
  │  tokens = calculate_token_count(amount, price_per_token)  # 20
  │  unit_amount_cents = int(price_per_token * 100)  # 50
  ▼
create_checkout_session(unit_amount_cents=50, quantity=20, customer_email="...")
  │  stripe.checkout.Session.create(
  │    payment_method_types=["card"],
  │    line_items=[{
  │      "price_data": {
  │        "currency": "usd",
  │        "product_data": {"name": "Invitation Code Tokens"},
  │        "unit_amount": 50,
  │      },
  │      "quantity": 20,
  │    }],
  │    mode="payment",
  │    adaptive_pricing={"enabled": True},
  │    customer_email="user@example.com",
  │    metadata={"source": "ourlives", "token_count": "20", ...},
  │  )
  ▼
Stripe Checkout (auto-detects currency via Adaptive Pricing)
  │  US customer → $10.00
  │  DE customer → €9.20  (Stripe converts at market rate + fee)
  │  JP customer → ¥1,500
  │  MX customer → MX$200 (if Adaptive Pricing enabled on account)
  ▼
Webhook (checkout.session.completed)
  │  currency = "usd"              (settlement)
  │  amount_total = 1000           (settlement cents)
  │  presentment_currency = "eur"  (customer-facing)
  │  presentment_amount = 920      (customer-facing cents)
  ▼
process_ourlives_checkout_completion
  │  locked.total_tokens += token_count
  │  StripeEvent.create(
  │    amount_cents=1000,
  │    presentment_currency="eur",
  │    presentment_amount=920,
  │    ...
  │  )
```

## Data Model Changes

```
AppSettings (existing):
  + stripe_product_id = CharField(max_length=255, blank=True)
      # Stripe Product ID (e.g., "prod_xxxxx")
      # Auto-populated by sync_stripe_price command on first run
  + stripe_price_id = CharField(max_length=255, blank=True)
      # Stripe Price ID (e.g., "price_xxxxx")
      # Auto-populated by sync_stripe_price command
  - price_per_token: unchanged (source of truth in USD)
  - min_purchase_amount: unchanged

StripeEvent (existing):
  - amount_cents: unchanged (settlement amount, always in USD cents)
  + presentment_currency = CharField(max_length=3, blank=True)
      # ISO 4217 code (e.g., "eur", "gbp") from webhook presentment_details
  + presentment_amount = PositiveIntegerField(null=True, blank=True)
      # Amount in customer's currency smallest unit
```

Note: `supported_currencies` and `currency_options` are intentionally omitted. Stripe Adaptive Pricing handles all currencies automatically using Stripe's market rates.

## Dependencies

- **`stripe` Python package**: upgrade from v15 to v15.4+ (pre-release) to support `adaptive_pricing` parameter. The parameter is passed as `adaptive_pricing={"enabled": True}` per the SDK's TypedDict signature (not a bare boolean).

## Edge Cases

- **`price_per_token = 0`**: The `sync_stripe_price` command skips execution (purchases are disabled via existing view guard). No Price is created or archived.
- **Price deleted in Stripe dashboard**: `sync_stripe_price` wraps archiving in try/except — if the old Price was already deleted, it silently proceeds to create a new one.

## Risks / Trade-offs

| Risk | Mitigation |
|---|---|---|
| **2-4% conversion fee** charged by Stripe on each transaction | Acceptable trade-off. Comparable to bank foreign transaction fees. Avoids need to manage exchange rates |
| **Adaptive Pricing not enabled on Stripe account** | `adaptive_pricing` API parameter may be silently ignored. Require enabling in Stripe Dashboard at Settings → Adaptive Pricing |
| **`presentment_amount` not populated for non-adaptive sessions** | Field is nullable; settlement `amount_cents` is always populated |
| **Customer without email causes Stripe error** | `customer_email` only passed when non-empty; fallback gracefully handled in code |
| **Stripe creates many archived Prices on price_per_token changes** | Each change creates 1 new Price + archives 1 old. Even weekly changes = ~52 Prices/year. Negligible |
