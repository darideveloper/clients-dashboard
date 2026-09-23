## Why

The Organization admin shows a "Combined total" column whose name no longer matches business language, and its Orders inline duplicates the order number (Unfold title row + first column) while lacking the per-order money figure that explains the org-level total.

## What Changes

- Rename the visible "Combined total" label to "Total Order Value" in the Organization and Rep admins (display label only; `combined_total` / `combined_total_display` code names unchanged).
- Replace the `"Uncategorized"` money bucket with `"No Currency"` everywhere per-currency breakdowns render (org/rep summaries, exports, seed data).
- Orders inline on the Organization change page:
  - Add a link-styled order-number cell (permission-aware Change/View, same pattern as the existing link column); keep the existing Change link column.
  - Add a per-order total column: agreed scans price + catalog items sum, formatted with the order's currency (order → pilot → product fallback), `—` when zero.
  - Hide the Unfold inline title row that repeats the order number (`hide_title = True`).
- Update the demo seed so a currency-less order exercises the "No Currency" bucket.

## Capabilities

### New Capabilities
- `order-total-value`: per-order combined money figure (`Order.total_order_value` property + admin display) with currency fallback chain and zero-state rendering.

### Modified Capabilities
- `org-rep-order-summaries`: "Combined total" label becomes "Total Order Value"; missing-currency bucket becomes "No Currency".
- `organization-management`: org admin list shows the renamed column; details "Order summary" section unchanged in structure.
- `ourlives-lookup-admin`: Rep admin shows the renamed column (shared mixin).
- `org-orders-inline`: inline columns gain linked order number + per-order total; title row hidden.
- `demo-seed`: seed data exercises the "No Currency" bucket.

## Impact

- Affected code: `project/admin_base.py` (display label, mixin), `ourlives/models.py` (`UNCATEGORIZED_CURRENCY`, new `Order` property), `ourlives/admin.py` (`OrgOrderInline`), `ourlives/management/commands/` seed, `ourlives/tests.py`, `ourlives/tests_seed_demo.py`.
- No API, URL, or schema (migration) changes; admin-only, display-level change.
- Existing tests asserting the old label, inline field tuples, and "Uncategorized" will be updated.
