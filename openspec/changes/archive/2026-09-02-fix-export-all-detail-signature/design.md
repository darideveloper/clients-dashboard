## Context

The `excel-export` capability (archived change `2026-09-01-add-excel-export`) added per-model bulk exports and a full-ourlives header export. The header export lives in `project/admin_base.py:OurlivesExportMixin.export_all` and is exposed via both `actions_list = ["export_all"]` and `actions_detail = ["export_all"]` (`OurlivesModelAdminBase` at `project/admin_base.py:93-96`). `AppSettingsAdmin` is a `SingletonModelAdmin` with no changelist, so it relies solely on `actions_detail`.

Unfold generates different URLs per action type (`unfold/admin.py:178-194`): `actions_list` → `export_all/` (no `object_id`), `actions_detail`/`actions_row` → `<path:object_id>/export_all/` via `wrap(method)` which forwards `object_id` as a kwarg to the action handler (`unfold/decorators.py:31-97` inner does `func(model_admin, request, *args, **kwargs)`). Permission checks follow the same rule (`unfold/decorators.py:66-68` and `unfold/mixins/action_model_admin.py:352` call `has_export_all_permission(request, object_id)` for detail actions).

Current implementation at `project/admin_base.py:78` is `def export_all(self, request):` — strict, so detail navigation fails with `TypeError: got an unexpected keyword argument 'object_id'`. List views appear healthy; every ourlives detail route would fail identically, but only the singleton (detail-only) makes it user-visible. Stack: Django 5.2, `django-unfold==0.97.0` (upgraded from 0.77.1), `openpyxl>=3.1,<3.2`, `django-solo`.

## Goals / Non-Goals

**Goals:**
- Make `Export all app data` work from both changelist (`actions_list`) and changeform (`actions_detail`) without duplicating URLs or violating the single-source admin base convention (`AGENTS.md:11`).
- Keep fix minimal (ponytail: one-line signature change) and fully backward compatible.
- Add regression coverage for list + detail paths.
- Clarify spec so future Unfold detail-contract regressions are prevented.

**Non-Goals:**
- No new export formats, streaming, permissions model changes, or UI redesign.
- No change to `build_full_app_workbook()` semantics (still app-wide, deterministic `sorted(apps.get_models(), key=model_name)`).
- No `get_urls()` override — Unfold's `actions_list`/`actions_detail` remains the idiomatic mechanism.

## Decisions

### Decision: Accept `object_id` via optional signature (`Option A` — chosen)

```python
class OurlivesExportMixin:
    @action(description="Export all app data", icon="download", permissions=["export_all"])
    def export_all(self, request, object_id=None, *args, **kwargs):
        from utils.excel_export import build_full_app_workbook
        wb = build_full_app_workbook()
        ...
        return _excel_response(wb, filename)

    def has_export_all_permission(self, request, obj=None, *args, **kwargs):
        ...
```

- **Rationale:** Matches Unfold's contract: detail actions always receive `object_id`; list actions omit it. `object_id=None` handles both, `*args/**kwargs` future-proofs against Unfold dialog `form` kwarg (`unfold/decorators.py:85`). Body ignores `object_id` because full export is app-wide anyway — identical to how `ModelAdminUnfoldBase.edit(request, object_id)` at `project/admin_base.py:37` already handles detail. Permission method tolerates `object_id` string without changing logic (`is_staff and has_module_perms("ourlives")`).
- **Alternatives considered:**
  - *Split into `export_all` + `export_all_detail`* — duplicates method/mixin and requires two `actions_list`/`actions_detail` entries for same behavior; rejected as bloat.
  - *Remove `actions_detail` from `OurlivesModelAdminBase`, keep detail only on `AppSettingsAdmin`* — would fix singleton but hides header action on every other detail page; contradicts `openspec/specs/excel-export/spec.md:59` and user expectation.
  - *Manual `get_urls` on mixin* — would duplicate URL registration across 5 ModelAdmins (previous rejected design, see `design.md` of add-excel-export); heavier than Unfold idiom.
  - *Thin wrapper delegating `export_all_detail` → `export_all`* — extra indirection for same result.

### Decision: No spec behavior change, only clarification

- Full export already specified as `actions_list = ["export_all"]` plus `AppSettingsAdmin(SingletonModelAdmin, OurlivesExportMixin, ModelAdminUnfoldBase)` preserving singleton behavior. The delta adds a scenario stating both list and detail routes succeed and notes the handler SHALL accept `object_id`; no change to workbook/discovery/filename/permission rules.

### Decision: Tests at two layers

- Unit: `RequestFactory` calls `OurlivesExportMixin.export_all(request, object_id="1")` and permission with `object_id`.
- Integration: `Client.get` via `reverse("admin:ourlives_appsettings_export_all", args=[1])` and `reverse("admin:ourlives_project_export_all", args=[id])` and changelist `reverse("admin:ourlives_project_export_all")` all 200 with Excel MIME; keep existing `utils/test_excel_export.py:ExcelExportAdminTests`.

## Risks / Trade-offs

- **Ignoring `object_id` is correct but subtle** → Full export is app-wide by design (`build_full_app_workbook` discovers via `app_label=="ourlives"`); document in method docstring that `object_id` is intentionally unused. Risk of future per-object export confusion is low and explicit.
- **Signature permissiveness** → `*args/**kwargs` could mask future required args; mitigated by keeping body simple and delegating to `build_full_app_workbook` (no per-object branching).
- **Unfold upgrade drift** → If Unfold adds new kwargs (e.g., `form`), permissive signature already handles it; if it switches to positional `object_id`, also covered via `*args`.
- **Singleton no changelist edge** → AppSettings detail is the only entry; fixing there guarantees user-visible success. No migration coordination needed.

## Migration Plan

1. Patch `project/admin_base.py` (one hunk per method).
2. Add/adjust `utils/test_excel_export.py` detail tests; run `pytest utils/test_excel_export.py -k export_all` + full suite `python -m pytest` / `python manage.py check`.
3. Manual QA as staff with `ourlives` perms: AppSettings changeform header button, Project changelist header button, Project detail header button; verify download, sheet order, `filename*` header; verify non-staff button hidden.
4. Deploy code-only; rollback = revert signature. Archive change with `openspec archive fix-export-all-detail-signature`.

## Open Questions

- None — fix is contract alignment; no pending decision.
