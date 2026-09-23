## 1. Rename label + No Currency bucket

- [x] 1.1 Set `combined_total_display` description to "Total Order Value" in `project/admin_base.py`
- [x] 1.2 Rename `UNCATEGORIZED_CURRENCY` value to `"No Currency"` in `ourlives/models.py`
- [x] 1.3 Update label/bucket assertions in `ourlives/tests.py` ("Combined total" → "Total Order Value", "Uncategorized" → "No Currency")

## 2. Per-order total value

- [x] 2.1 Add `Order.total_order_value` property in `ourlives/models.py` (agreed + items, currency fallback chain)
- [x] 2.2 Add `total_order_value_display` readonly + prefetch (`items`, `currency`, `pilot_currency`) to `OrgOrderInline` in `ourlives/admin.py`
- [x] 2.3 Add property/display tests (merge math, nulls→0, fallback chain, zero renders `—`)

## 3. Inline links + title row

- [x] 3.1 Add perm-aware `order_number_link` readonly to `OrgOrderInline` and swap into `fields`/`readonly_fields`
- [x] 3.2 Set `hide_title = True` on `OrgOrderInline`
- [x] 3.3 Update `OrgOrderInline` opts/link tests in `ourlives/tests.py` (tuples, link method, `hide_title`)

## 4. Seed + verify

- [x] 4.1 Ensure seed data exercises a currency-less order (→ `No Currency`) and a per-order total in `seed_ourlives_demo`
- [x] 4.2 Run `python manage.py test ourlives` green and visually check one Organization change page
