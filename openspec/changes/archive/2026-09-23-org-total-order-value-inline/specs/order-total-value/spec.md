## ADDED Requirements

### Requirement: Per-order total value
The system SHALL provide a read-only `total_order_value` on `Order` in `ourlives/models.py` equal to `total_agreed_price` plus `SUM(quantity × unit_price)` over the order's items (null scans/cost count as 0, same rule as `total_agreed_price`). No database column SHALL be added. The display currency SHALL resolve via the order's `currency` when set, otherwise its `pilot_currency`, otherwise the items' `Product.currency` (first resolvable), otherwise the `No Currency` bucket.

#### Scenario: Agreed plus items merge
- **WHEN** an order has `total_agreed_price` 1250.00 and one item with `line_total` 40.00
- **THEN** `total_order_value` is `Decimal("1290.00")`

#### Scenario: Nulls treated as zero
- **WHEN** an order has null `number_of_scans` but an item worth 20.00
- **THEN** `total_order_value` is `Decimal("20.00")`

#### Scenario: No value renders placeholder
- **WHEN** an order has no scans value and no items
- **THEN** the admin display renders `—`

#### Scenario: Currency fallback chain
- **WHEN** an order has null `currency` but `pilot_currency` set
- **THEN** the display is prefixed with the pilot currency code
- **WHEN** an order has both currency fields null
- **THEN** the display uses the items' product currency, or `No Currency` when unresolvable
