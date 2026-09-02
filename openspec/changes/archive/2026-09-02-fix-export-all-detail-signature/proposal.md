## Why

`GET /admin/ourlives/appsettings/1/export_all/` crashes with `TypeError: OurlivesExportMixin.export_all() got an unexpected keyword argument 'object_id'` (`unfold/decorators.py:69` forwards `object_id` for `actions_detail` routes). The header button `Export all app data` is registered as both `actions_list` and `actions_detail` (`OurlivesModelAdminBase` at `project/admin_base.py:93-96`, and `AppSettingsAdmin(SingletonModelAdmin, OurlivesExportMixin, ModelAdminUnfoldBase)`), so the singleton changeform (no changelist) is the only entry point and is broken. Other `ourlives` changelists appear to work only because the list route has no `object_id`; their detail route (`/<id>/export_all/`) would fail identically. One-line signature mismatch blocks a user-visible admin feature.

## What Changes

- Fix `project/admin_base.py:OurlivesExportMixin.export_all` signature to `export_all(self, request, object_id=None, *args, **kwargs)` so it handles both Unfold list (`export_all/`) and detail (`<path:object_id>/export_all/`) URLs; body unchanged (still calls `build_full_app_workbook()`).
- Make `has_export_all_permission(self, request, obj=None, *args, **kwargs)` tolerant of the `object_id` string Unfold passes for detail permission checks.
- Add regression tests covering `export_all` from both `actions_list` and `actions_detail` (AppSettings singleton + Project detail/list).
- Clarify `excel-export` spec that `Export all app data` must work from both changelist and changeform, without changing app-wide export semantics.

## Capabilities

### New Capabilities
<!-- None — bugfix -->
- None

### Modified Capabilities
- `excel-export`: Clarify that the full ourlives app export header action must handle Unfold detail routes (accept `object_id`) while keeping app-wide semantics, permissions, and filename unchanged

## Impact

- **Code**: `project/admin_base.py` (signature fix), `utils/test_excel_export.py` (detail + list regression tests)
- **Specs**: `openspec/specs/excel-export/spec.md` (scenario clarification)
- **APIs/Systems**: Admin-only; no public API, no DB migration, no new dependencies
- **Breaking changes**: None
