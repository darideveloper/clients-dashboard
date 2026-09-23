## Why

Both "Export to Excel" bulk actions crash with `ValueError: chunk_size must be provided when using QuerySet.iterator() after prefetch_related()` on `/admin/ourlives/order/` (prod, Django 5.2.17). `OrderAdmin.get_queryset()` adds `.prefetch_related("order_types")` and `.prefetch_related("items__product__currency")`, which survive into the admin action queryset, and `utils/excel_export.py` calls `qs.iterator()` with no `chunk_size`. Same latent crash affects any other admin with `prefetch_related` (e.g. `RepAdmin`).

## What Changes

- In `utils/excel_export.py::_write_sheet_for_model`, strip unused prefetches before streaming (`qs.prefetch_related(None)`) then keep `select_related(*fk_names)` for the FK columns the export actually reads.
- Pass explicit `chunk_size=2000` (Django's own default for non-prefetch querysets) to both `iterator()` call sites (`_write_sheet_for_model` main loop and the `include_related` fallback ID-collection loop) so any future prefetch can't crash the export again.
- Add regression coverage: export a queryset that carries `prefetch_related` (Order changelist queryset with `order_types` + `items__product__currency` prefetches) via `build_workbook_for_queryset` and via the admin changelist POST, asserting 200 + valid `.xlsx`.
- No admin `get_queryset` changes; changelist prefetch behavior is preserved.

## Capabilities

### New Capabilities
- None.

### Modified Capabilities
- `excel-export`: streaming requirement tightens — per-model and related-sheet iteration SHALL tolerate incoming querysets that carry `prefetch_related` (clear unused prefetches, iterate with explicit chunk size) instead of raising `ValueError`.

## Impact

- Touched: `utils/excel_export.py` (2 call sites), `utils/test_excel_export.py` (regression tests). No model, migration, URL, or permission changes.
- Behavior: Order (and any prefetch-carrying admin) exports succeed; exported columns/rows unchanged (M2M / reverse-FK prefetches were never exported — concrete fields only).
- Perf: removes useless per-chunk prefetch queries on export; memory profile unchanged (still streaming via `iterator`).
