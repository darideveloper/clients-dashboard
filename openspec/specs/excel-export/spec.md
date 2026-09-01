# excel-export Specification

## Purpose
TBD - created by archiving change add-excel-export. Update Purpose after archive.
## Requirements
### Requirement: Per-model Excel export via bulk actions
Every changelist-based `ModelAdmin` that inherits `project.admin_base.ModelAdminUnfoldBase` (and `TokenAdmin` as `class TokenAdmin(ModelAdminUnfoldBase, BaseTokenAdmin)`) SHALL expose two Django admin bulk actions operating on the checkbox-selected queryset, declared with `unfold.decorators.action` and gated on `view` so read-only models remain exportable (`AppSettings` singleton has no changelist and is excluded — covered by the full-app header action):

- **Export to Excel** (`export_selected`) — single sheet, no related sheets.
- **Export to Excel (with related)** (`export_selected_with_related`) — main sheet plus one sheet per directly-related model (forward FK/OneToOne only, single hop).

Both actions SHALL be declared as `@action(description="Export to Excel", icon="download", permissions=["view"])` / `@action(description="Export to Excel (with related)", icon="download", permissions=["view"])`, SHALL define `has_export_selected_permission` / `has_export_selected_with_related_permission` delegating to `has_view_permission`, SHALL optimize the queryset via `select_related(*fk_names)` and iterate via `.iterator()`, and SHALL return an `HttpResponse` with `Content-Type: application/vnd.openxmlformats-officedocument.spreadsheetml.sheet` and RFC 5987 `Content-Disposition: attachment; filename="..." ; filename*=utf-8''...` (filename sanitized, non-ASCII handled). The main queryset received from the admin is the already-filtered selected set — the action SHALL NOT re-fetch via `request.POST["_selected_action"]`. Selecting no rows and invoking the action SHALL call `self.message_user(request, "Select at least one row to export.", messages.WARNING)` and return `None` (no file).

#### Scenario: Export selected rows without related data
- **WHEN** a staff user ticks 3 `InvitationCode` rows and runs "Export to Excel"
- **THEN** the downloaded workbook contains one sheet named after the model and exactly 3 data rows (plus header), and no additional sheets

#### Scenario: Export selected rows with related data (forward FKs only)
- **WHEN** a staff user ticks 2 `InvitationCode` rows (referencing Project A/B and Organization X) and runs "Export to Excel (with related)"
- **THEN** the workbook contains a main `InvitationCode` sheet with 2 rows plus separate `Project` and `Organization` sheets each containing only the referenced rows (deduped via `target.objects.filter(pk__in=distinct_ids)`), and contains no `StripeEvent` or transitive sheets

#### Scenario: Empty selection shows warning
- **WHEN** a user runs either export action with no rows selected
- **THEN** the admin displays a warning message "Select at least one row to export." and no file is downloaded

#### Scenario: Permission gated on view (read-only models included)
- **WHEN** a user without `view` permission on a model loads its changelist
- **THEN** the export actions are not available for that model
- **WHEN** a user with `view` but not `change` on `StripeEvent` (which has `has_change_permission=False`) loads the `StripeEvent` changelist
- **THEN** the export actions are still available (gated on `view`, not `change`)

#### Scenario: Singleton note
- **WHEN** a user opens the `AppSettings` singleton admin (no changelist)
- **THEN** per-model bulk actions are not surfaced there; AppSettings is still exported via the full-app header action

### Requirement: FK representation without related data
When `include_related` is false, each concrete forward FK/OneToOne field on the exported model SHALL be represented by exactly two columns: `<field_name>__str__` (value `str(related_obj)` when not null, blank when null; related object obtained via `select_related` to avoid N+1) and `<field_name>_id` (raw FK id, e.g., `project_id`). Non-FK concrete fields SHALL each map to one column titled by the field's `verbose_name` (or field name fallback). The exported row count SHALL equal the selected queryset count.

#### Scenario: FK shown as str and id
- **WHEN** an `InvitationCode` with `project` "Alpha" (`id=7`) is exported without related data
- **THEN** the sheet contains columns `project__str` with value "Alpha" and `project_id` with value 7, and no `project` object column

#### Scenario: Non-FK fields each produce one column
- **WHEN** `Project` rows are exported
- **THEN** each concrete non-FK field (e.g., `name`, `description`) appears as one column with its verbose name as header

### Requirement: Related sheets contain referenced rows only
When `include_related` is true, for each distinct forward FK/OneToOne target model of the exported model, the workbook SHALL include one additional sheet named after the target model containing only the rows referenced by the selected queryset (distinct, via `pk__in` of the collected FK ids; related querysets use `.iterator()`). The main sheet SHALL still contain the two FK columns (`__str__` + `_id`). Reverse relations, M2M, and transitive (second-hop) models SHALL NOT produce sheets.

#### Scenario: Related sheets are referenced-only
- **WHEN** 5 `InvitationCode`s are selected that collectively reference 2 distinct `Project`s out of 10 total projects
- **THEN** the `Project` sheet contains exactly 2 rows regardless of total projects in the DB

#### Scenario: No transitive sheets
- **WHEN** a model A has FK to B and B has FK to C, and A is exported with related
- **THEN** the workbook contains sheets for A and B only, not C

### Requirement: Full ourlives app export via Unfold header action
`project/admin_base.OurlivesExportMixin` and `project/admin_base.OurlivesModelAdminBase(OurlivesExportMixin, ModelAdminUnfoldBase)` (single source in `project/admin_base.py`, no `ourlives/admin_base.py`) SHALL expose a single Unfold header button `Export all app data` via `actions_list = ["export_all"]` and `@action(description="Export all app data", icon="download", variant="default", permissions=["export_all"])`. The method `has_export_all_permission(self, request)` SHALL return `request.user.is_staff and request.user.has_module_perms("ourlives")`; Unfold auto-generates the URL and wraps the view in `admin_site.admin_view` (no manual `get_urls`). The action SHALL call `build_full_app_workbook()` which discovers ourlives models deterministically via `sorted(apps.get_models(), key=lambda m: m._meta.model_name)` filtered by `app_label=="ourlives"` so future ourlives models are included automatically and sheet order is stable, each sheet containing all rows of that model (`queryset.iterator()`), formatted identically to per-model exports. The filename SHALL be `ourlives_full_export_<YYYYMMDD_HHMM>.xlsx` with RFC 5987 `filename*=utf-8''` encoding. Ourlives `ModelAdmin`s `ProjectAdmin`, `OrganizationAdmin`, `InvitationCodeAdmin`, and `StripeEventAdmin` in `ourlives/admin.py` SHALL inherit `OurlivesModelAdminBase`; `AppSettingsAdmin` (singleton) SHALL keep `SingletonModelAdmin` first and add `OurlivesExportMixin` — e.g. `class AppSettingsAdmin(SingletonModelAdmin, OurlivesExportMixin, ModelAdminUnfoldBase):` — so singleton behavior is preserved while the header button is available; `core` admins SHALL keep `ModelAdminUnfoldBase` so the button never appears outside ourlives.

#### Scenario: Full export from any ourlives changelist
- **WHEN** a permitted staff user clicks "Export all app data" on the `Project` changelist
- **THEN** the downloaded workbook contains sheets (one per ourlives model, deterministically ordered) with all rows of each model

#### Scenario: New ourlives model automatically included
- **WHEN** a new model is added to the `ourlives` app and registered in the admin via `OurlivesModelAdminBase`
- **THEN** the next full export includes a sheet for that model without any change to the export action

#### Scenario: Core admins do not show full-app button
- **WHEN** a user views a `core` changelist (e.g., `Brand`)
- **THEN** the "Export all app data" header button is not present

#### Scenario: Permission gated for full export
- **WHEN** a non-staff or staff without `ourlives` module perms loads an ourlives changelist
- **THEN** the "Export all app data" header button is not visible (Unfold checks `has_export_all_permission`)

### Requirement: Workbook formatting
Every generated workbook SHALL apply formatting via a shared styling helper:

- Header row (row 1) SHALL be bold, font size 11–12pt, white text on a fill using `_primary_color()` (reads `Brand.get_or_create_default().primary_color` with fallback `#C92FFF` and guards `OperationalError`/`ProgrammingError` during migrations), with a thin bottom border. Decimal/money cells SHALL have `number_format='#,##0.00'`.
- The header row SHALL be frozen (`ws.freeze_panes = "A2"`).
- Data rows SHALL use banded fill (alternating `#F9FAFB` / `#FFFFFF`).
- Column widths SHALL be auto-sized from the maximum display length of the header and cell values in that column, scaled by ~1.2 and capped at 50 characters.
- Sheet names SHALL be sanitized to Excel constraints (≤31 chars, characters `:\/?*[]` replaced with `_`, leading/trailing `'` stripped, empty name falls back to `model._meta.model_name`, forbidden empty handled, duplicates disambiguated with numeric suffix `_2`, `_3`).

#### Scenario: Header styling applied
- **WHEN** any export workbook is opened
- **THEN** row 1 on every sheet is bold with white-on-brand fill and remains visible while scrolling (frozen)

#### Scenario: Column widths are readable
- **WHEN** a sheet contains a column with values up to 40 characters
- **THEN** that column's width is sized to fit the longest value (capped at 50) without manual adjustment

#### Scenario: Sheet name sanitization
- **WHEN** a model verbose name exceeds 31 characters or contains forbidden Excel characters or is empty
- **THEN** the sheet name is truncated/sanitized (forbidden chars replaced, leading/trailing `'` stripped, empty falls back to model name) and remains unique within the workbook via suffix disambiguation

#### Scenario: Brand table missing during migrations
- **WHEN** `migrate` or `collectstatic` runs and the `Brand` table does not yet exist
- **THEN** workbook generation does not raise `OperationalError`; the fallback color `#C92FFF` is used

### Requirement: Value serialization for Excel
Field values SHALL be serialized to Excel-native primitives: Char/Text/Slug/URL/Email → string; Boolean → boolean; Integer/BigInteger/PositiveInteger → integer; Decimal → float with `number_format`; Date/DateTime/Time → Python `date`/`datetime`/`time` objects; FileField/ImageField → file name or URL string; JSONField → JSON string; `None`/empty → blank cell. Related objects for `__str__` are obtained via `select_related` to avoid N+1. No locale-dependent number or date formatting SHALL be applied at serialization time beyond `number_format`; openpyxl's default type handling SHALL be relied upon.

#### Scenario: Typed cells in Excel
- **WHEN** a row with an integer `max_use=100`, decimal `price_per_token=2.50`, boolean `is_active=True`, and datetime `handled_at` is exported
- **THEN** the corresponding Excel cells are typed as number, number (with `#,##0.00`), boolean, and datetime respectively (not all strings)

#### Scenario: Null FK produces blank str column
- **WHEN** a row has a nullable FK that is null
- **THEN** the `<field>__str__` cell is blank and `<field>_id` is blank

### Requirement: Extensibility convention documented in AGENTS.md
`AGENTS.md` SHALL document the convention that new admin-registered models MUST inherit `project.admin_base.ModelAdminUnfoldBase` (or `project.admin_base.OurlivesModelAdminBase` for `ourlives` models — single source, not `ourlives/admin_base.py`) to automatically receive the export bulk actions (and, for ourlives, participation in the full-app export). The note SHALL state that no per-model export wiring is required beyond inheriting the correct base.

#### Scenario: New model automatically gets export
- **WHEN** a developer registers a new model `NewThing` with `admin.register(NewThing)(NewThingAdmin)` where `NewThingAdmin` inherits `ModelAdminUnfoldBase`
- **THEN** the changelist for `NewThing` shows "Export to Excel" and "Export to Excel (with related)" in the Actions dropdown without additional code
