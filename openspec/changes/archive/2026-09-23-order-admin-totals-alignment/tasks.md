## 1. Shared helper

- [x] 1.1 Add module-level `format_order_money(order, amount)` in `ourlives/admin.py` (order → pilot → product → "No Currency"; `—` when zero/unsaved)
- [x] 1.2 Refactor `OrgOrderInline.total_order_value_display` to use the helper

## 2. Order admin displays

- [x] 2.1 Rename `total_agreed_price_display` label to "Agreed scans total" and render via the helper (`CODE amount`)
- [x] 2.2 Add `catalog_items_total_display` ("Catalog items total", Σ quantity × unit_price over items)
- [x] 2.3 Add `total_order_value_display` ("Total Order Value", model `total_order_value`)

## 3. Wiring

- [x] 3.1 Terms fieldset lists the three money figures in org-summary order; add `catalog_items_total_display`/`total_order_value_display` to `readonly_fields`
- [x] 3.2 `list_display`: replace `total_agreed_price_display` with `total_order_value_display` (final total only, non-sortable)
- [x] 3.3 Prefetch `items__product__currency` in `OrderAdmin.get_queryset` (N+1 guard)

## 4. Tests + verify

- [x] 4.1 Add `test_totals_display_and_terms_fieldset` (list final-total-only, Terms carries all three, merge/`—` displays, detail page renders labels)
- [x] 4.2 Run `python manage.py test ourlives` green
- [x] 4.3 Update `crm-admin-registration` spec delta to document `total_order_value_display` in `list_display` and the three readonly totals in Terms