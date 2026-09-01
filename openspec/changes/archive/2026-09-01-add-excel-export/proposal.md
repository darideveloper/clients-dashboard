## Why

Staff and operators need to extract data from the admin for reporting, audits, and offline analysis. No export capability exists today — data is only viewable inside the Django admin. An Excel export that supports per-model selected-row exports (with and without related data) and a full ourlives app dump, with proper formatting, removes manual copy-paste and reduces operational friction.

## What Changes

- Add `openpyxl>=3.1,<3.2` as a pinned project dependency for `.xlsx` generation with styling (Unfold is pinned at `0.77.1`, so pinning avoids breakage).
- Add a shared Excel export utility (`utils/excel_export.py`) that introspects model fields, handles FK/OneToOne forward relations only, and applies formatting (bold header, brand-themed colors, auto column widths, frozen header, banded rows). The util uses `select_related` on the main queryset and `.iterator()` for large sets, and sanitizes every value to an Excel-native type.
- Add two Django admin bulk actions to every model admin via `project/admin_base.ModelAdminUnfoldBase` using `unfold.decorators.action` with `permissions=["view"]` so read-only models (e.g. `StripeEvent`) remain exportable:
  - **Export to Excel** — selected rows only, single sheet (model name), FKs shown as `<field>__str__` + `<field>_id`.
  - **Export to Excel (with related)** — selected rows plus one sheet per directly-related model (forward FK/OneToOne only), containing only the referenced rows (deduped); main sheet still shows `__str__`+`id`.
  - Both actions expose `has_export_selected_permission` / `has_export_selected_with_related_permission` delegating to `has_view_permission`, return an `HttpResponse` with `Content-Type: application/vnd.openxmlformats-officedocument.spreadsheetml.sheet` and an RFC 5987 `filename*=utf-8''` disposition, and call `message_user(..., messages.WARNING)` on empty selection.
- Add a full ourlives app export: a single Unfold header button `Export all app data` on ourlives changelists via `project/admin_base.OurlivesExportMixin` / `OurlivesModelAdminBase` (single source in `project/admin_base.py` — no new `ourlives/admin_base.py`). The mixin declares an Unfold `actions_list` action `@action(description="Export all app data", icon="download", permissions=["export_all"])` with `has_export_all_permission` checking `is_staff and has_module_perms("ourlives")`; Unfold auto-generates the URL (no manual `get_urls`). The action calls `build_full_app_workbook()` which discovers ourlives models deterministically via `sorted(apps.get_models(), key=lambda m: m._meta.model_name)` filtered by `app_label="ourlives"`, one sheet per model with all rows, same formatting. `TokenAdmin` is fixed to `class TokenAdmin(ModelAdminUnfoldBase, BaseTokenAdmin):` (correct MRO).
- Update `AGENTS.md` with a convention note so future admin-registered models automatically get the export actions by inheriting the correct base (`ModelAdminUnfoldBase` everywhere, `OurlivesModelAdminBase` for ourlives to join the full export).

## Capabilities

### New Capabilities
- `excel-export`: Excel export from the Django admin — per-model bulk exports, related-data sheets, full-app export, and workbook formatting.

### Modified Capabilities
- _None_ — this change introduces a new capability; existing specs (e.g., `unfold-admin-theme`, `unfold-auth-admin-registration`) are not changing at the spec level, only gaining additional admin actions.

## Impact

- **Code**: `requirements.txt`, `project/admin_base.py` (single source for both bases/mixin), new `utils/excel_export.py`, `ourlives/admin.py` (migrate to `OurlivesModelAdminBase`), `core/admin.py` (`TokenAdmin` MRO fix), `AGENTS.md`.
- **Dependencies**: adds `openpyxl>=3.1,<3.2` (no other new runtime deps).
- **APIs / Systems**: no public API change; admin-only feature. Excel MIME `application/vnd.openxmlformats-officedocument.spreadsheetml.sheet` with RFC 5987 filename encoding for non-ASCII.
- **Breaking changes**: none.
