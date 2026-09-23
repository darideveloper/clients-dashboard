## Why

The Organization and Order admin screens used inconsistent money terminology: the order page listed "Total agreed" and hid the "Catalog items total" and combined "Total Order Value" figures on the detail form. Aligning the order admin to the org's labels and rendering all three totals in the detail view makes the money story consistent across the two screens.

## What Changes

- Rename the Order detail/list display label "Total agreed" → **"Agreed scans total"** (aligns with the org rollup label for the same formula).
- Expose all three calculated figures on the Order **detail** page in the "Terms" fieldset, in org-summary order: `Agreed scans total`, `Catalog items total`, `Total Order Value`.
- Show **only the final `Total Order Value`** in the Order **list** (replacing the old agreed column).
- Add a shared `format_order_money(order, amount)` helper so the Order admin and the org-orders inline render identical `"CODE amount"` / `—` strings with the same currency fallback (order → pilot → product → "No Currency"); refactor `OrgOrderInline.total_order_value_display` to reuse it.
- Extend `OrderAdmin.get_queryset` to prefetch `items__product__currency` so the new list total column adds no per-row queries.

## Capabilities

### New Capabilities
- `order-totals-alignment`: shared per-order money formatting helper + the three order-level money figures (`Agreed scans total`, `Catalog items total`, `Total Order Value`) on the Order admin detail and list.

### Modified Capabilities
- `crm-admin-registration`: `OrderAdmin.list_display` drops `total_agreed_price_display` in favor of `total_order_value_display`; detail Terms shows all three totals as readonly; `total_agreed_price_display` (now "Agreed scans total") stays read-only.

## Impact

- `ourlives/admin.py` (`OrderAdmin`: `list_display`, Terms `fieldsets`, `readonly_fields`, `get_queryset`, display methods; module-level `format_order_money`; `OrgOrderInline` refactor).
- `ourlives/tests.py` (new `test_totals_display_and_terms_fieldset`, updated list/tuple assertions).
- No model changes, no migrations; pure admin/display-level change.