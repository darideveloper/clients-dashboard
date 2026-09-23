## ADDED Requirements

### Requirement: Shared order-total formatting helper
The system SHALL provide a module-level `format_order_money(order, amount)` helper in `ourlives/admin.py` that renders a single per-order money string `"CODE amount"` (or `—` when the amount is falsy or the order is unsaved). The display code SHALL resolve via the order's `currency` when set, otherwise its `pilot_currency`, otherwise the first resolvable item `Product.currency`, otherwise the `No Currency` (`UNCATEGORIZED_CURRENCY`) label. The `OrgOrderInline.total_order_value_display` SHALL delegate to this helper so the Order admin and the org-orders inline render identically.

#### Scenario: Order currency wins
- **WHEN** an order has `currency` set
- **THEN** the helper prefixes the amount with that currency code (order currency beats pilot and product currency)

#### Scenario: Pilot currency fallback
- **WHEN** an order has null `currency` but `pilot_currency` set
- **THEN** the helper prefixes with the pilot currency code

#### Scenario: Product currency fallback to No Currency
- **WHEN** an order has both currency fields null but an item's product has a currency
- **THEN** the helper prefixes with the product currency code
- **WHEN** an order has no resolvable currency
- **THEN** the helper prefixes with `No Currency`

#### Scenario: Zero renders placeholder
- **WHEN** an order's amount is zero or the order is unsaved
- **THEN** the helper returns `—`