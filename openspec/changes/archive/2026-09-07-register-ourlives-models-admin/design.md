## Context

`ourlives/models.py` defines 10 models; `ourlives/admin.py` registers 5 (`Project`, `Organization`, `InvitationCode`, `AppSettings`, `StripeEvent`). The 5 Phase-1 lookup models (`Country` ×249 fixtures, `Rep` ×0 by design, `ContactType` ×4, `CodeType` ×2, `OrderType` ×4) have models + `base_loaddata` fixtures + model tests but zero admin surface. Staff cannot browse, search, deactivate, or bulk-export them. All admin bases live single-source in `project/admin_base.py` (`ModelAdminUnfoldBase` bulk Excel actions gated on `view`; `OurlivesExportMixin.export_all` header button gated on `has_module_perms("ourlives")`; `OurlivesModelAdminBase` combines both). Full-app export (`build_full_app_workbook`, `utils/excel_export.py`) auto-discovers via `sorted(apps.get_models())`, so new admins need no export wiring.

## Goals / Non-Goals

**Goals:**
- Standalone changelist admins for the 5 lookups with display/filter/search/inline-toggle appropriate to each field set and fixture policy.
- `Country` fixture-guarded (no add/delete, active-toggle only); `Rep` + 3 type tables fully staff-editable.
- Small `InvitationCodeAdmin` tune (autocomplete + inline `is_active`) without touching pool validation.

**Non-Goals:**
- No model/field/migration/fixture changes; no FKs, inlines, or cross-model workflows (explicitly deferred).
- No `date_hierarchy` (no date fields), no per-row audit-reason UI, no custom permissions beyond add/delete guards on `Country`.
- No changes to `project/admin_base.py` or `utils/excel_export.py`.

## Decisions

- **Inherit `OurlivesModelAdminBase` for all 5** (over plain `ModelAdminUnfoldBase`) — gives per-model bulk `Export to Excel` actions + `Export all app data` header button for free; matches `AGENTS.md` convention. Alternative (plain base + manual export wiring) rejected as duplication.
- **`Country` guard via `has_add_permission=False` / `has_delete_permission=False`** (over `readonly` or `has_change=False`) — keeps changelist visible + `active` toggle editable while blocking PK drift from the 249-row explicit-PK fixture. Applies to all users including superusers; emergency add/delete path is fixtures + `loaddata` or Django shell (no admin UI path by design). Alternative (fully free) rejected: new/deleted ISO rows would desync `base_loaddata` idempotency. Alternative (fully read-only) rejected: user confirmed toggle must stay.
- **`list_filter=(active,)` only for `Country`** (drop `region`) — fixture scan shows `region==''` for all 249 rows; a region filter renders a useless single empty choice. Re-add when populated. Same single-filter shape for the 3 type tables; `Rep`/`Project`-likes get no filter (no bool/category field).
- **Inline `list_editable=(active,)` with explicit `list_display_links`** (`(iso2,)` / `(code,)`) — Django requires the editable column to differ from the link column; fast bulk deactivation for lookup curation. Thin `LogEntry` history accepted (who/when logged, no why). Detail view remains for context (`description`) and future guards. Alternative (detail-only) rejected as too slow for 249 countries; user confirmed inline.
- **`InvitationCode.autocomplete_fields`** (over expanded `list_filter` dropdowns) — FK dropdowns degrade as Project/Org rows grow; targets already expose `search_fields=(name,)` so autocomplete works with zero extra changes. `max_use`/`current_use` deliberately excluded from `list_editable` (pool `clean()/save()` must run through the full form path).
- **Icons chosen to avoid sidebar collisions**: `globe` (Country), `person` (Rep), `contacts` (ContactType), `sell` (CodeType), `shopping_bag` (OrderType); `receipt_long` stays with `StripeEvent`.
- **`description` excluded from `list_display`/`search`** — long free text, blank-heavy; detail-form only keeps changelists scannable and search indexes narrow.

## Risks / Trade-offs

- [Risk] Inline `active` toggle has no confirmation and thin history (`Changed active.`, no reason) → Mitigation: reversible boolean; `Country` add/delete blocked so worst case is a visibility flip, re-flippable in one click.
- [Risk] Free-add on code tables (`ContactType`/`CodeType`/`OrderType`) can introduce near-duplicate codes before FKs exist → Mitigation: `code`/`name` unique constraints already enforced at DB + model tests; dedupe pass deferred to the FK-introducing change.
- [Risk] `Country.list_per_page` default may paginate 249 rows without complaint, but large future Reg filters absent → Mitigation: search on `iso2/iso3/name` covers lookup; revisit if rows grow 10×.
