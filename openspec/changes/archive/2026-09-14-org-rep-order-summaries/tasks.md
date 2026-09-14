## 1. Model summaries

- [x] 1.1 Add shared breakdown helper + formatting helper (alphabetical codes, `—` on empty, `Uncategorized` bucket key).
- [x] 1.2 Add `order_count`, `agreed_scans_total`, `catalog_items_total`, `combined_total`, `last_order_date` properties to `Organization` (null scans/cost → 0, pilots included, item currency = order first / product fallback).
- [x] 1.3 Add the same five properties to `Rep` scoped to direct `orders` FK.
- [x] 1.4 Add model tests: empty org/rep, null handling, pilot inclusion, multi-currency separation, item-currency rule + fallback, combined math, last date.

## 2. Admin list views

- [x] 2.1 Extend `OrganizationAdmin.get_queryset` with `Count`/`Max` annotations for the sortable columns, plus a constant-query supplementary per-(object, currency) breakdown fetch (agreed via column-product expression reproducing null→0 with currency→pilot_currency→Uncategorized attribution; items via join with order→product→Uncategorized attribution).
- [x] 2.2 Extend `RepAdmin` the same way scoped to `orders`.
- [x] 2.3 Add breakdown `@admin.display` money columns (annotation-first, property fallback) to both admins; verify changelist query count has no per-row queries.
- [x] 2.4 Add admin tests: changelist renders columns, sorting by count/date works, annotation matches property values on shared fixtures.

## 3. Admin detail sections

- [x] 3.1 Add readonly "Order summary" fieldset with the five displays + labels/help texts to `OrganizationAdmin` (keep existing fields, inlines, filters).
- [x] 3.2 Add the same fieldset to `RepAdmin`.
- [x] 3.3 Add admin tests: change form shows section with help texts; empty record renders placeholders.

## 4. Verification

- [x] 4.1 Run full `ourlives` test suite and Unfold changelist smoke checks (Organization + Rep list/detail pages return 200).
- [x] 4.2 Confirm no migrations generated (`makemigrations --check`) and Excel export behavior unchanged.
