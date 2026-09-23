## MODIFIED Requirements

### Requirement: Calculated-field branch coverage
The seeded data SHALL exercise: `total_agreed_price` (normal + null scans + null cost), `is_pilot_order` (pilot-only, standard-only, multi-type, typeless), agreed-totals attribution (`currency` wins over `pilot_currency`, pilot-only, neither → `No Currency`), catalog-items attribution (order currency → pilot currency → product currency fallback), `combined_total` merge, `total_order_value` per-order figure, an empty org/rep with zero orders, and a full org holding the most orders.

#### Scenario: All summary branches present
- **WHEN** seeding completes
- **THEN** there exists an order with `number_of_scans=None`, one with `cost_per_scan=None`, one pilot / one standard / one multi-type / one typeless order, one `currency+pilot` order, one pilot-only order, one currency-less order with scans (→ `No Currency`), an item whose order currency differs from its product currency, an org with zero orders (its `last_order_date` is None and all its totals render `—`), a rep with zero orders, an order with zero items, and an order with zero invitation codes (empty items-inline / `codes_list` states)
