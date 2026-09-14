# org-rep-order-summaries Specification

## Purpose
Per-currency order summaries on Organization and Rep for the admin.

## Requirements
### Requirement: Order summary properties on Organization and Rep

The system SHALL provide five read-only calculated summaries on both `Organization` and `Rep` in `ourlives/models.py`, derived from the related `orders` (`related_name="orders"`, direct FK `Order.rep` for Rep scope — not via `Organization.assigned_rep`):
- `order_count`: integer count of related orders.
- `agreed_scans_total`: per-currency mapping of `SUM(number_of_scans × cost_per_scan)` over related orders, with null `number_of_scans`/`cost_per_scan` treated as 0 (same rule as `Order.total_agreed_price`). Each order amount is attributed to the order's `currency` when set, otherwise to its `pilot_currency`, otherwise to an `Uncategorized` bucket. Pilot orders are included.
- `catalog_items_total`: per-currency mapping of `SUM(quantity × unit_price)` over related orders' items. Each item amount is attributed to the parent order's `currency` when set, otherwise its `pilot_currency`, otherwise the line's `Product.currency`; amounts with no resolvable currency go under an `Uncategorized` bucket.
- `combined_total`: per-currency element-wise sum of `agreed_scans_total` + `catalog_items_total` (currencies never mixed).
- `last_order_date`: `MAX(submitted_at)` over related orders, None when there are no orders.
- No database columns SHALL be added for any summary. Currency codes in mappings are ordered alphabetically.

#### Scenario: Organization with no orders
- **WHEN** an Organization has no related orders
- **THEN** `order_count` is 0, all money mappings are empty, and `last_order_date` is None

#### Scenario: Agreed total treats nulls as zero and includes pilots
- **WHEN** an Organization has a pilot order with `number_of_scans=500, cost_per_scan="2.50"` and a standard order with null scans
- **THEN** `agreed_scans_total` for the pilot order's currency equals `Decimal("1250.00")`

#### Scenario: Agreed currency attribution rule
- **WHEN** an order has `currency` set (even with `pilot_currency` also set)
- **THEN** its agreed amount is attributed to `currency`
- **WHEN** an order has null `currency` but `pilot_currency` set
- **THEN** its agreed amount is attributed to `pilot_currency`
- **WHEN** an order has both currency fields null
- **THEN** its agreed amount is attributed to `Uncategorized`

#### Scenario: Items total summed across orders
- **WHEN** a Rep's orders contain items with line totals 1990.00 and 500.00 in the same currency
- **THEN** `catalog_items_total` for that currency equals `Decimal("2490.00")`

#### Scenario: Multi-currency breakdown stays separated
- **WHEN** an Organization has a USD agreed total of 1750.00 and a EUR agreed total of 800.00
- **THEN** `agreed_scans_total` is `{"EUR": Decimal("800.00"), "USD": Decimal("1750.00")}` and no single mixed sum exists

#### Scenario: Item currency attribution rule
- **WHEN** an OrderItem's parent order has `currency` set
- **THEN** its line total is attributed to the order's `currency` regardless of the product's currency
- **WHEN** the parent order has null `currency` but `pilot_currency` set
- **THEN** its line total is attributed to `pilot_currency`
- **WHEN** the parent order has both currency fields null
- **THEN** its line total is attributed to the line's `Product.currency`, or to `Uncategorized` when that is also unresolvable

#### Scenario: Combined total is per-currency addition
- **WHEN** agreed is `{"USD": 1250.00}` and items is `{"USD": 1990.00, "EUR": 100.00}`
- **THEN** `combined_total` is `{"USD": 3240.00, "EUR": 100.00}`

#### Scenario: Last order date
- **WHEN** a Rep has orders submitted on 2025-01-01 and 2026-03-04
- **THEN** `last_order_date` equals the 2026-03-04 timestamp

### Requirement: Summary display formatting and help texts

The system SHALL render money mappings as compact breakdown strings (`USD 1,750.00 · EUR 800.00`, codes alphabetical, `—` when empty) via a shared helper, and SHALL document each summary in the admin with these labels and help texts:
- `order_count` / "Orders" / "Number of orders linked to this record (Order.organization / Order.rep)."
- `agreed_scans_total` / "Agreed scans total" / "Sum of number_of_scans × cost_per_scan over its orders (form: scan count × price per scan). Null values count as 0. Per currency; pilots included."
- `catalog_items_total` / "Catalog items total" / "Sum of quantity × unit_price over its order items (form: product picker × quantity, price frozen at order time). Per currency; pilots included."
- `combined_total` / "Combined total" / "Agreed scans total + catalog items total, per currency. Amounts in different currencies are never added together."
- `last_order_date` / "Last order" / "Most recent Order.submitted_at."

#### Scenario: Empty breakdown renders placeholder
- **WHEN** a record has no amounts in any currency
- **THEN** money displays render `—` instead of an empty string

#### Scenario: Breakdown ordering
- **WHEN** a record has EUR and USD amounts
- **THEN** the rendered string lists EUR before USD
