## MODIFIED Requirements

### Requirement: Full ourlives app export via Unfold header action
`project/admin_base.OurlivesExportMixin` and `project/admin_base.OurlivesModelAdminBase(OurlivesExportMixin, ModelAdminUnfoldBase)` (single source in `project/admin_base.py`, no `ourlives/admin_base.py`) SHALL expose a single Unfold header button `Export all app data` via `actions_list = ["export_all"]` and `@action(description="Export all app data", icon="download", variant="default", permissions=["export_all"])`. The action handler `export_all` SHALL accept `object_id` as an optional parameter (`def export_all(self, request, object_id=None, *args, **kwargs)`) so it handles both Unfold `actions_list` routes (`export_all/`, no `object_id`) and `actions_detail` routes (`<path:object_id>/export_all/`, with `object_id`) without raising `TypeError`; the `object_id` value SHALL be ignored because the export is app-wide. The method `has_export_all_permission(self, request, obj=None, *args, **kwargs)` SHALL accept an optional `object_id` string and SHALL return `request.user.is_staff and request.user.has_module_perms("ourlives")`; Unfold auto-generates the URL and wraps the view in `admin_site.admin_view` (no manual `get_urls`). The action SHALL call `build_full_app_workbook()` which discovers ourlives models deterministically via `sorted(apps.get_models(), key=lambda m: m._meta.model_name)` filtered by `app_label=="ourlives"` so future ourlives models are included automatically and sheet order is stable, each sheet containing all rows of that model (`queryset.iterator()`), formatted identically to per-model exports. The filename SHALL be `ourlives_full_export_<YYYYMMDD_HHMM>.xlsx` with RFC 5987 `filename*=utf-8''` encoding. Ourlives `ModelAdmin`s `ProjectAdmin`, `OrganizationAdmin`, `InvitationCodeAdmin`, and `StripeEventAdmin` in `ourlives/admin.py` SHALL inherit `OurlivesModelAdminBase`; `AppSettingsAdmin` (singleton) SHALL keep `SingletonModelAdmin` first and add `OurlivesExportMixin` — e.g. `class AppSettingsAdmin(SingletonModelAdmin, OurlivesExportMixin, ModelAdminUnfoldBase):` — so singleton behavior is preserved while the header button is available via `actions_detail`; `core` admins SHALL keep `ModelAdminUnfoldBase` so the button never appears outside ourlives.

#### Scenario: Full export from any ourlives changelist
- **WHEN** a permitted staff user clicks "Export all app data" on the `Project` changelist (`actions_list`)
- **THEN** the downloaded workbook contains sheets (one per ourlives model, deterministically ordered) with all rows of each model

#### Scenario: Full export from AppSettings singleton changeform (detail route)
- **WHEN** a permitted staff user clicks "Export all app data" on the `AppSettings` changeform (`actions_detail`, URL `<path:object_id>/export_all/`)
- **THEN** the request succeeds with `200` and `Content-Type: application/vnd.openxmlformats-officedocument.spreadsheetml.sheet` and `Content-Disposition: attachment; filename*=utf-8''ourlives_full_export_*.xlsx`, returning a workbook with one sheet per ourlives model (AppSettings still exported via full-app header action)

#### Scenario: Full export from any ourlives changeform
- **WHEN** a permitted staff user clicks "Export all app data" on a `Project`/`Organization`/`InvitationCode`/`StripeEvent` changeform (detail route)
- **THEN** the request succeeds with the same app-wide workbook regardless of the `object_id` value in the URL

#### Scenario: New ourlives model automatically included
- **WHEN** a new model is added to the `ourlives` app and registered in the admin via `OurlivesModelAdminBase`
- **THEN** the next full export includes a sheet for that model without any change to the export action

#### Scenario: Core admins do not show full-app button
- **WHEN** a user views a `core` changelist (e.g., `Brand`)
- **THEN** the "Export all app data" header button is not present

#### Scenario: Permission gated for full export
- **WHEN** a non-staff or staff without `ourlives` module perms loads an ourlives changelist or changeform
- **THEN** the "Export all app data" header button is not visible (Unfold checks `has_export_all_permission`)
