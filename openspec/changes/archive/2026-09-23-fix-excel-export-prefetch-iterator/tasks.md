## 1. Reproduce and fix streaming

- [x] 1.1 Reproduce `ValueError` with the real Order changelist queryset (`OrderAdmin.get_queryset` with `order_types` + `items__product__currency` prefetches; bare `.iterator()` and `build_workbook_for_queryset(Order, qs)`) and confirm both admin actions hit it.
- [x] 1.2 In `utils/excel_export.py::_write_sheet_for_model`, clear unused prefetches (`prefetch_related(None)`, guarded) before `select_related(*fk_names)` and switch main loop to `qs.iterator(chunk_size=2000)`.
- [x] 1.3 In `utils/excel_export.py::build_workbook_for_queryset` fallback ID-collection loop, use `queryset.iterator(chunk_size=2000)`.

## 2. Regression coverage

- [x] 2.1 Add `build_workbook_for_queryset` test with `prefetch_related` queryset (Order changelist queryset with both prefetches, `include_related=False/True`) asserting valid workbook + row counts.
- [x] 2.2 Add admin changelist POST test for `/admin/ourlives/order/` both export actions asserting 200 + Excel content-type (fails before fix).
- [x] 2.3 Run `utils/test_excel_export.py` plus `ourlives` admin/export tests; confirm no regressions.
