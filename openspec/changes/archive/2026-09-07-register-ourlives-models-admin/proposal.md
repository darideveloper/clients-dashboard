## Why

Five `ourlives` lookup models (`Country`, `Rep`, `ContactType`, `CodeType`, `OrderType`) exist with fixtures and tests but have no Django admin registration, so staff cannot view, search, toggle, or bulk-export them.

## What Changes

- Register `Country`, `Rep`, `ContactType`, `CodeType`, `OrderType` in `ourlives/admin.py`, each inheriting `OurlivesModelAdminBase` (bulk Excel export + full-app `Export all app data` header button free, per `project/admin_base.py` single-source convention).
- `Country`: fixture-only + active toggle — `has_add_permission=False`, `has_delete_permission=False`; `list_display=(iso2,iso3,name,active)`; `list_filter=(active,)` (region dropped — all blank in fixtures); `search_fields=(iso2,iso3,name)`; `list_editable=(active,)` with `list_display_links=(iso2,)`; icon `globe`.
- `Rep`: fully free CRUD (no fixtures by design); `list_display=(first_name,last_name,email)`; `search_fields=(first_name,last_name,email)`; no filter/editable; icon `person`.
- `ContactType` / `CodeType` / `OrderType`: fully free CRUD; `list_display=(code,name,active[,max_codes for CodeType])`; `list_filter=(active,)`; `search_fields=(code,name)`; `list_editable=(active,)` with `list_display_links=(code,)`; icons `contacts` / `sell` / `shopping_bag`.
- Tune `InvitationCodeAdmin`: add `autocomplete_fields=(project,organization)` and `list_editable=(is_active,)` (links already `code`); no change to pool validation in `clean()/save()`.
- No `date_hierarchy` anywhere (no DateField in these models); `description` stays detail-form only; Meta `ordering` inherited, not duplicated.

## Capabilities

### New Capabilities

- `ourlives-lookup-admin`: admin registration and changelist behavior (display, filter, search, inline active toggle, add/delete guards, icons) for Country, Rep, ContactType, CodeType, OrderType, plus InvitationCode admin tune.

### Modified Capabilities

- None (model specs in `crm-phase1-lookups` and export behavior in `excel-export` are unchanged; new admins inherit existing export machinery with no requirement change).

## Impact

- `ourlives/admin.py` only (5 new `ModelAdmin` classes + 2-line `InvitationCodeAdmin` tune). No model, migration, fixture, or export-utility changes.
- `build_full_app_workbook()` already discovers new models via `apps.get_models()` — full export gains 5 sheets with zero wiring.
- Staff UX: 5 models become visible/searchable in Unfold sidebar; `Country` cannot be added/deleted (toggle only).
