## Why

Child entities (`Contact`, `OrganizationAddress`, `OrderItem`) can only be managed on standalone changelists, forcing staff through extra navigation for data that is always created in the context of its parent (`Organization`, `Order`). At the same time the Unfold sidebar auto-lists every registered model, so fixture-only lookup tables (`Country`, `ContactType`, `CodeType`, `OrderType`, plus `Currency`/`Product`) clutter the daily workspace with equal visual weight as operational models.

## What Changes

- `Contact` and `OrganizationAddress` become editable Unfold inlines on the `Organization` change page (stacked, tabbed, `extra=0`); their standalone `ModelAdmin`s are removed (unregistered), hiding them from sidebar, index, and URLs.
- `OrderItemInline` is migrated from `django.contrib.admin.TabularInline` to `unfold.admin.TabularInline` and its standalone `OrderItemAdmin` is removed; line items live only inside `Order`.
- `OrderAdmin.autocomplete_fields` drops `primary_contact`/`invoice_contact` (Django autocomplete requires the target model to be registered) → plain selects.
- `UNFOLD["SIDEBAR"]` switches to fully manual navigation (`show_all_applications=False`): an operational group, a collapsible **Reference data** group (`Country`, `ContactType`, `CodeType`, `OrderType`, `Currency`, `Product`), the existing **Credits** link, and an explicit **Core** group. Every item carries a `view_<model>` permission check.
- **BREAKING**: replaces the auto-rendered permission sidebar mandated by `unfold-permission-sidebar` (the `navigation.html` override rendering `available_apps` is retired; new `ModelAdmin`s need an explicit nav entry to appear in the sidebar). Admin index page, search, URLs, and exports are unaffected.
- **BREAKING**: `/admin/ourlives/contact/`, `/admin/ourlives/organizationaddress/`, and `/admin/ourlives/orderitem/` cease to exist; per-model Excel row actions for those three disappear (full-app export still covers them via `apps.get_models()`).
- Test-only fix (pre-existing, unrelated to this change but required for a green suite): two `utils/test_excel_export` with-related assertions still expect 3 sheets from before `InvitationCode` gained its `order`/`code_type` FKs; updated to the correct 5 (main + Project + Organization + Order + Code Type). No engine or spec changes.

## Capabilities

### New Capabilities

- `admin-inline-children`: child-only models edited exclusively via Unfold inlines on their parent change pages (inline types, tab grouping, `extra=0`, in-inline autocomplete, full add/change/delete through parent).
- `manual-admin-sidebar`: curated Unfold sidebar groups (operational, collapsible Reference data, Credits, Core) with per-item permission checks and a registry-coverage test guaranteeing every registered model has exactly one nav entry.

### Modified Capabilities

- `crm-admin-registration`: `Contact`/`OrganizationAddress`/`OrderItem` standalone registrations removed; `OrderAdmin` contact autocompletes removed; `OrderItemInline` becomes an Unfold tabular inline.
- `unfold-permission-sidebar`: auto-rendered `available_apps` sidebar replaced by explicit `SIDEBAR.navigation`; `show_all_applications` flips to `False`; "new ModelAdmin needs no settings change" no longer holds for the sidebar (index/search still automatic).
- `unfold-admin-theme`: "Unfold config block" `SIDEBAR` flips to `show_all_applications=False` with the curated four-group `navigation`; sidebar body rendered by Unfold's bundled sidebar from `SIDEBAR.navigation` instead of the auto-render override.

## Impact

- `ourlives/admin.py` (inline classes, removed registrations, trimmed autocomplete), `project/settings.py` (`UNFOLD["SIDEBAR"]`), `project/templates/unfold/helpers/navigation.html` (override retired/deleted), `ourlives/tests.py` (inline render + child-404 + sidebar coverage assertions), `utils/test_excel_export.py` (stale with-related sheet counts corrected, test-only).
- Staff workflow: contacts/addresses/items edited on parent pages; lookup tables grouped under one collapsible section; users without `ourlives` perms see no ourlives links (headers-only groups remain — accepted cosmetic limitation).
- No model, migration, fixture, export-workbook, or URL changes outside the three removed changelists.
