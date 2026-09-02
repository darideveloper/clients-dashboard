## 1. Fix mixin signature (single-source)

- [x] 1.1 Update `project/admin_base.py:OurlivesExportMixin.export_all` to `def export_all(self, request, object_id=None, *args, **kwargs):` and keep body calling `build_full_app_workbook()` + `_excel_response` unchanged (ignore `object_id`, app-wide export)
- [x] 1.2 Update `project/admin_base.py:OurlivesExportMixin.has_export_all_permission` to `def has_export_all_permission(self, request, obj=None, *args, **kwargs):` (tolerate `object_id` string from Unfold detail checks; logic stays `is_staff and has_module_perms("ourlives")`)

## 2. Tests and QA

- [x] 2.1 Add/adjust `utils/test_excel_export.py` — unit: `RequestFactory` calls `export_all(request)` and `export_all(request, object_id="1")` both 200 + Excel MIME + `filename*`; permission checks via `has_export_all_permission(request, "1")` granted/denied; integration: `Client` GET `reverse("admin:ourlives_appsettings_export_all", args=[1])` (singleton detail), `reverse("admin:ourlives_project_export_all", args=[id])` (generic detail), and `reverse("admin:ourlives_project_export_all")` (list) all succeed with `openpyxl.load_workbook`
- [x] 2.2 Run test suite: `pytest utils/test_excel_export.py` and `python manage.py check`; verify `collectstatic` still guards `_primary_color` fallback
- [x] 2.3 Manual QA as `is_staff` + `has_module_perms("ourlives")`: header button `Export all app data` on AppSettings changeform, on Project changelist, on Project changeform; each downloads app-wide workbook with deterministic sheet order; verify non-staff / no-perms user does not see button on list or detail

## 3. Spec/Docs verification

- [x] 3.1 Verify `openspec/specs/excel-export/spec.md` delta archived correctly (scenarios for list + detail, `object_id` acceptance) and no `AGENTS.md` change needed (single source stays `project/admin_base.py`)
