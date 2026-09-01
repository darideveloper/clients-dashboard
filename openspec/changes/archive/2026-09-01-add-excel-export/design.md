## Context

The admin currently has 9 registered models across two local apps plus auth:
- `core`: `Brand`, `User`, `Group`, `TokenProxy` (DRF)
- `ourlives`: `Project`, `Organization`, `InvitationCode`, `AppSettings` (singleton via `django-solo`), `StripeEvent` (read-only — `has_change_permission=False`)
- `Membership` exists only as an inline

All ModelAdmins except `TokenAdmin` inherit `project/admin_base.ModelAdminUnfoldBase` (unfold `ModelAdmin`) which already centralizes chrome (sidebar icons, compressed fields, row `Edit` action) at `project/admin_base.py:7` via `unfold.decorators.action`. No export exists. `requirements.txt` has no Excel library; the stack is Django 5.2, `django-unfold==0.77.1`, `pillow`, `psycopg`, DRF, S3 via `django-storages`. AppSettings is a `SingletonModelAdmin` (no changelist), so per-model bulk actions are not surfaced there — the full-app header button must still be reachable.

In explore, decisions were fixed: per-model export = selected-rows bulk actions with **two buttons** ("Export" / "Export + related"), related = **forward FK/OneToOne only** (no reverse/M2M), related sheets = **referenced rows only** (deduped) for the selected set, and a **full ourlives app export** (ourlives models only, all rows).

## Goals / Non-Goals

**Goals:**
- Per-model Excel export from the admin that operates on the checkbox-selected queryset, with an explicit choice to include or exclude directly-related data — visible even on read-only models.
- Full ourlives app export (all rows of Project, Organization, InvitationCode, AppSettings, StripeEvent) from a single Unfold header action, without duplicate URL registrations.
- Workbooks are well-formatted: auto-sized columns, bold larger header with themed fill, frozen header row, banded rows, single sheet per model and separate sheets for related models when requested.
- Generic, extensible implementation: adding a new admin-registered model automatically gets the per-model actions; adding a new ourlives model automatically appears in the full export without code changes beyond registration.
- Minimal new dependencies and surface area; single source of admin bases in `project/admin_base.py`; admin views remain thin and reuse a shared util.

**Non-Goals:**
- CSV/PDF or other formats; scheduled/background exports; client-side JS export.
- Reverse FK, M2M, or transitive (indirect) relationships in related sheets.
- Exporting non-model data, media files, or computed annotations beyond `__str__`/`id` for FKs.
- Role-based export restrictions beyond existing Django admin per-model `view` permission and `has_module_perms("ourlives")` for the full export.
- Streaming for very large datasets (>50k rows per sheet) — not needed for current volumes.

## Decisions

### Decision: `openpyxl` pinned `>=3.1,<3.2` for workbook generation
- **Chosen**: `openpyxl>=3.1,<3.2` (add to `requirements.txt`, e.g. `==3.1.5` today).
- **Rationale**: Native `.xlsx` with full control over fonts, fills, column widths, freeze panes, and sheet names; same library `pandas` would delegate to for styling, so going direct avoids an extra layer. Pinning mirrors `django-unfold==0.77.1` already pinned and prevents Excel write breakage on major bumps.
- **Alternatives considered**: `pandas + ExcelWriter(openpyxl)` — awkward for FK `__str__`/`id` and styling; `xlsxwriter` — write-only, heavier API, no read-back needed.

### Decision: Shared utility `utils/excel_export.py` — thin admins, testable core
- **Chosen**: One module exposing `sanitize_sheet_name(name, existing)`, `serialize_value(field, obj)`, `columns_for_model(model)`, `get_related_targets(model)`, `build_workbook_for_queryset(model, queryset, include_related)`, `build_full_app_workbook()`, `style_sheet(ws)`, `autosize_columns(ws)`, plus internal `_primary_color()` helper.
- **Rationale**: Keeps admins thin; testable in isolation; reused by per-model actions and full-app action.
- **FK representation** (include_related=False): each concrete FK/OneToOne expands to two columns `<field>__str__` (via `str(getattr(obj, field.name))` when not None, otherwise blank) and `<field>_id` (raw FK id). The main queryset is built with `queryset.select_related(*fk_names)` to avoid N+1, and iterated via `.iterator()` for large sets. Non-FK concrete fields map to one column titled by `field.verbose_name` (fallback `field.name`).
- **FK representation** (include_related=True): main sheet still shows the two FK columns; one additional sheet per distinct forward FK target containing its referenced rows (`target.objects.filter(pk__in=distinct_ids)`). Related sheets use the same column logic without further expansion (single hop).
- **Serialization & formatting**: Char/Text/Slug/URL/Email → str; Boolean → bool; Integer/BigInteger/PositiveInteger → int; Decimal → float with `number_format='#,##0.00'` for price fields; Date/DateTime/Time → native Python objects (openpyxl handles); File/ImageField → file name or URL string; JSONField → JSON string; `None`/empty → blank cell. No locale-dependent coercion. Decimal→float risk noted below.
- **Determinism**: `build_full_app_workbook()` discovers via `sorted(apps.get_models(), key=lambda m: m._meta.model_name)` filtered by `app_label=="ourlives"` so sheet order is stable and new ourlives models appear automatically.
- **Styling helper `_primary_color()`**: reads `Brand.get_or_create_default().primary_color` with `fallback="#C92FFF"` and guards `OperationalError`/`ProgrammingError` during migrations when the `Brand` table does not yet exist — avoids a DB hit breaking `migrate` or `collectstatic`.

### Decision: Per-model export as Django bulk actions on `ModelAdminUnfoldBase` — gated on `view`
- **Chosen**: Extend `project/admin_base.ModelAdminUnfoldBase` with:

  ```python
  from unfold.decorators import action

  @action(description="Export to Excel", icon="download", permissions=["view"])
  def export_selected(self, request, queryset):
      if not queryset.exists():
          self.message_user(request, "Select at least one row to export.", messages.WARNING)
          return None
      wb = build_workbook_for_queryset(self.model, queryset.select_related(*fk_names).iterator(), include_related=False)
      ...

  def has_export_selected_permission(self, request, obj=None):
      return self.has_view_permission(request, obj)
  # same for export_selected_with_related
  ```

  Register as `actions = ["export_selected", "export_selected_with_related"]`. Both return an `HttpResponse` with `Content-Type: application/vnd.openxmlformats-officedocument.spreadsheetml.sheet` and RFC 5987 `Content-Disposition: attachment; filename="..."; filename*=utf-8''...` (sanitized via `sanitize_sheet_name` + slugify for non-ASCII brand names).

- **Rationale**: Bulk actions natively receive the checkbox-selected `queryset`; `permissions=["view"]` + `has_*_permission` delegating to `has_view_permission` keeps the export visible on read-only models like `StripeEvent` (`ourlives/admin.py:159` has `has_change_permission=False`). Fixes the current design’s `permissions=["change"]` gap. Two distinct actions satisfy the “two buttons” UX without an intermediate prompt template. `TokenAdmin` is fixed to `class TokenAdmin(ModelAdminUnfoldBase, BaseTokenAdmin):` (correct MRO — Unfold’s `ModelAdmin` must come first).
- **Singleton note**: `AppSettingsAdmin` (`ourlives/admin.py:54`, `SingletonModelAdmin`) has no changelist, so bulk actions are not surfaced there — acceptable; the full-app header button still covers AppSettings.
- **Alternatives considered**: Unfold `actions_list` header buttons reading `_selected_action` PKs — fragile; single action + prompt template — extra round-trip, rejected per user’s two-button choice.

### Decision: Full ourlives app export as a single Unfold `actions_list` header action — no manual `get_urls`
- **Chosen**: Add a mixin/base in the **single source** `project/admin_base.py` (no new `ourlives/admin_base.py`):

  ```python
  class OurlivesExportMixin:
      @action(description="Export all app data", icon="download", variant="default", permissions=["export_all"])
      def export_all(self, request):
          ...

      def has_export_all_permission(self, request):
          return request.user.is_staff and request.user.has_module_perms("ourlives")

  class OurlivesModelAdminBase(OurlivesExportMixin, ModelAdminUnfoldBase):
      actions_list = ["export_all"]
  ```

  Unfold auto-generates the URL (`…/export-all/`) and wraps it in `admin_site.admin_view` (checks `is_active and is_staff` via `AdminSite.has_permission`). The action builds via `build_full_app_workbook()` (one sheet per ourlives model, all rows, same `_primary_color`/`style_sheet`). `ourlives/admin.py` admins `ProjectAdmin`, `OrganizationAdmin`, `InvitationCodeAdmin`, and `StripeEventAdmin` inherit `OurlivesModelAdminBase`; `AppSettingsAdmin` (singleton) keeps `SingletonModelAdmin` first and adds `OurlivesExportMixin` — `class AppSettingsAdmin(SingletonModelAdmin, OurlivesExportMixin, ModelAdminUnfoldBase):` — so singleton behavior is preserved while the header button is available; `core/admin.py` admins keep `ModelAdminUnfoldBase` so the button never appears on `Brand`/`User`/`Group`/`Token`.

- **Rationale**: One header button, no duplicate URL registrations (previous design put `get_urls` on the mixin, so 5 ModelAdmins would each register `admin:ourlives_export_all`). Unfold’s `@action` + `actions_list` is the idiomatic way for header actions (see `unfoldadmin/django-unfold` `actions/changelist.md`). Discovering models via `apps.get_models()` with sorted order keeps new ourlives models automatic.
- **Alternatives considered**: Manual `get_urls` on `AppSettingsAdmin` only — valid Django but inconsistent with Unfold’s header-action idiom; site-wide `AdminSite.get_urls` override — heavier; `UNFOLD["SIDEBAR"]["navigation"]` link — semantically wrong (export is an app action, not navigation).

### Decision: Formatting via `style_sheet` / `autosize_columns` / `sanitize_sheet_name`
- **Chosen**: Header row (row 1) bold, ~11–12pt, white font on `_primary_color()` fill, thin bottom border; `ws.freeze_panes = "A2"`; banded rows (`#F9FAFB`/`#FFFFFF`); `autosize_columns` computes max display length per column (header + cell strings) capped at **50** and scaled by **1.2**; `number_format` applied to Decimal/money cells.
- **Sheet naming**: `sanitize_sheet_name` enforces Excel constraints (≤31 chars, replaces `:\/?*[]`, strips leading/trailing `'`, handles empty `verbose_name_plural` → fallback `model_name`, deduplicates with numeric suffix `_2`, `_3`).
- **Rationale**: Meets “correct column widths, titles in bold/bigger, table colors” without a table-style dependency. Using `_primary_color()` reuses existing theming (`utils/callbacks.py:80` `primary_palette_css`) consistently.

### Decision: Single source of admin bases + convention in `AGENTS.md`
- **Chosen**: Keep all bases/mixins in `project/admin_base.py`; add convention section to `AGENTS.md` stating new admin-registered models must inherit `ModelAdminUnfoldBase` (or `OurlivesModelAdminBase` for `ourlives`) to automatically get export; no per-model wiring required.
- **Rationale**: Avoids splitting bases across `project/` and `ourlives/`; single source is discoverable and the `AGENTS.md` note makes extensibility explicit without a linter.

## Risks / Trade-offs

- [Only forward FKs exported] → Reverse/M2M not included by design; util can be extended later.
- [Selected-rows + related = referenced rows only] → Action labels (“Export to Excel (with related) — related sheets show only rows referenced by your selection”) and empty-selection `message_user` clarify scope; easy to switch to “all rows” if requested.
- [In-memory workbook] → Large querysets use memory; mitigated by `select_related` + `.iterator()` and future streaming (`StreamingHttpResponse`) if needed; threshold remains 50k rows.
- [Decimal→float] → Sub-cent precision loss possible; mitigated by `number_format` and authoritative DB values; acceptable for reporting.
- [TokenAdmin not on base] → Fixed by correct MRO `ModelAdminUnfoldBase, BaseTokenAdmin`; previously sole model without export.
- [Sheet name collisions] → Deduplication with suffix handles it; empty/overlong names handled via fallback.
- [Brand table missing during migrations] → `_primary_color()` guards `OperationalError`/`ProgrammingError`; fallback color prevents `migrate` breakage.
- [Singleton AppSettings has no changelist] → Per-model bulk actions not surfaced there — covered by full-app export; no extra wiring needed.

## Migration Plan

1. Pin `openpyxl>=3.1,<3.2` in `requirements.txt` and install.
2. Create `utils/excel_export.py` with `_primary_color()`, `sanitize_sheet_name`, `serialize_value`, `columns_for_model`, `get_related_targets`, `build_workbook_for_queryset` (`select_related` + `iterator`), `build_full_app_workbook` (sorted discovery), `style_sheet`/`autosize_columns` (with `number_format`).
3. Extend `project/admin_base.py` with bulk actions `export_selected` / `export_selected_with_related` (`@action(permissions=["view"])`, `has_*_permission` → `has_view_permission`, RFC 5987 disposition, empty-selection guard) and `OurlivesExportMixin` / `OurlivesModelAdminBase` (`actions_list=["export_all"]`, `@action(icon="download", permissions=["export_all"])`).
4. Update `ourlives/admin.py` admins to inherit `OurlivesModelAdminBase`; update `core/admin.py:105` to `class TokenAdmin(ModelAdminUnfoldBase, BaseTokenAdmin):` (correct MRO).
5. Update `AGENTS.md` with the export convention.
6. No DB migrations. Deploy is code-only; rollback is revert.

## Open Questions

- None blocking. Empty-selection now consistently uses `message_user(..., messages.WARNING)` (“Select at least one row to export.”).
