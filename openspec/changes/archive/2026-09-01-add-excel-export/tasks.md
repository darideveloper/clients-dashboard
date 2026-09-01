## 1. Dependencies and scaffolding

- [x] 1.1 Add `openpyxl>=3.1,<3.2` to `requirements.txt` (e.g. `==3.1.5`) and install/verify `import openpyxl` — pin mirrors `django-unfold==0.77.1`
- [x] 1.2 Create `utils/excel_export.py` module skeleton with docstring, `_primary_color()` helper (guards `OperationalError`/`ProgrammingError`, fallback `#C92FFF`), and no-op exports

## 2. Excel export utility

- [x] 2.1 Implement `sanitize_sheet_name(name, existing)` — enforce ≤31 chars, replace `:\/?*[]` with `_`, strip leading/trailing `'`, handle empty name → `model._meta.model_name`, deduplicate with numeric suffix `_2`, `_3`
- [x] 2.2 Implement `serialize_value(field, obj)` — handle Char/Text/Slug/URL/Email, Boolean, Integer/BigInteger, Decimal→float with `number_format='#,##0.00'` for money fields, Date/DateTime/Time (tz-naive), File/ImageField, JSONField, None→blank; use `select_related` on FKs to avoid N+1
- [x] 2.3 Implement `columns_for_model(model)` — concrete fields only; FK/OneToOne → two column specs (`__str__`+`_id` via `select_related`), others → one column with `verbose_name` header
- [x] 2.4 Implement `get_related_targets(model)` — collect distinct forward FK/OneToOne target models (single hop, no reverse/M2M)
- [x] 2.5 Implement `build_workbook_for_queryset(model, queryset, include_related, existing_workbook=None)` — main sheet from `queryset.select_related(*fk_names).iterator()`, additional sheets for referenced rows (`target.objects.filter(pk__in=distinct_ids).iterator()`) when `include_related=True`, sanitize names, handle non-ASCII via slugify; fixed empty-sheet placeholder row
- [x] 2.6 Implement `build_full_app_workbook()` — discover `ourlives` models deterministically via `sorted(apps.get_models(), key=lambda m: m._meta.model_name)` filtered by `app_label=="ourlives"`, one sheet per model with all rows via `.iterator()`, stable order
- [x] 2.7 Implement `style_sheet(ws)` (bold 11–12pt white-on-`_primary_color()` header, thin bottom border, `number_format` for Decimal, freeze `A2`, banded rows `#F9FAFB`/`#FFFFFF`) and `autosize_columns(ws)` (max length capped at 50, scale 1.2); wire into workbook builders
- [x] 2.8 Add unit tests for `utils/excel_export.py` — FK str/id columns with `select_related`, related referenced-only sheets, no transitive sheets, sheet name sanitization (forbidden chars, leading `'`, empty, duplicates), typed serialization with `number_format`, `_primary_color` fallback during missing table, formatting helpers

## 3. Per-model bulk actions (generic, gated on view)

- [x] 3.1 Extend `project/admin_base.py:ModelAdminUnfoldBase` with bulk actions `@action(description="Export to Excel", icon="download", permissions=["view"]) export_selected` and `@action(description="Export to Excel (with related)", icon="download", permissions=["view"]) export_selected_with_related` — define `has_export_selected_permission` / `has_export_selected_with_related_permission` delegating to `has_view_permission`, guard empty `queryset.exists()` with `self.message_user(request, "Select at least one row to export.", messages.WARNING)` and return `None`, call `build_workbook_for_queryset` with `queryset.select_related(...).iterator()`, return `HttpResponse` with `Content-Type: application/vnd.openxmlformats-officedocument.spreadsheetml.sheet` and RFC 5987 `Content-Disposition: attachment; filename="..."; filename*=utf-8''...`
- [x] 3.2 Fix `core/admin.py:105` to `class TokenAdmin(ModelAdminUnfoldBase, BaseTokenAdmin):` (Unfold base first — correct MRO) so TokenProxy also exposes the two actions
- [x] 3.3 Manual QA: verify actions appear in Actions dropdown for Brand, User, Group, TokenProxy, Project, Organization, InvitationCode, StripeEvent (read-only `view`-gated) — AppSettings singleton has no changelist so bulk actions not surfaced there (covered by full export); export with/without related and open in Excel/LibreOffice; non-ASCII filenames encoded correctly

## 4. Full ourlives app export (single Unfold header action)

- [x] 4.1 Add `OurlivesExportMixin` and `OurlivesModelAdminBase(OurlivesExportMixin, ModelAdminUnfoldBase)` to `project/admin_base.py` (single source — no `ourlives/admin_base.py`) with `actions_list = ["export_all"]` and `@action(description="Export all app data", icon="download", permissions=["export_all"]) export_all(self, request)` plus `has_export_all_permission(self, request)` checking `request.user.is_staff and request.user.has_module_perms("ourlives")` — Unfold auto-generates the URL and wraps in `admin_site.admin_view`, no manual `get_urls`
- [x] 4.2 Implement `export_all` to call `build_full_app_workbook()`, return Excel response with `Content-Type` and RFC 5987 `filename*=utf-8''ourlives_full_export_<YYYYMMDD_HHMM>.xlsx` (sanitized, sorted sheets)
- [x] 4.3 Migrate `ourlives/admin.py` admins `ProjectAdmin`, `OrganizationAdmin`, `InvitationCodeAdmin`, and `StripeEventAdmin` to inherit `OurlivesModelAdminBase`; make `AppSettingsAdmin` inherit `SingletonModelAdmin` + `OurlivesExportMixin` + `ModelAdminUnfoldBase` (`class AppSettingsAdmin(SingletonModelAdmin, OurlivesExportMixin, ModelAdminUnfoldBase):`) so singleton behavior is preserved while the header button is available (`core` admins keep `ModelAdminUnfoldBase` so button never appears on Brand/User/Group/Token)
- [x] 4.4 Manual QA: full export header button visible on all ourlives changelists (including the singleton’s change form if applicable via `actions_detail`), not on core changelists; downloaded workbook has one sheet per ourlives model deterministically ordered with all rows and correct formatting; non-staff/no-perms user does not see the button

## 5. Documentation and housekeeping

- [x] 5.1 Update `AGENTS.md` with convention: new admin-registered models must inherit `ModelAdminUnfoldBase` (or `project.admin_base.OurlivesModelAdminBase` for `ourlives` — single source, not `ourlives/admin_base.py`) to automatically get export actions / full-app participation; no per-model wiring needed
- [x] 5.2 Add admin integration tests — POST to `admin:core_brand_changelist` and `admin:ourlives_invitationcode_changelist` with `action=export_selected` + `_selected_action`, assert `Content-Type: application/vnd...` and `filename*` header; test empty-selection warning and `has_export_all_permission` gating
- [x] 5.3 Run existing test suite and fix regressions; verify `python manage.py check` and `collectstatic` pass with new pinned dependency and `_primary_color` guard
