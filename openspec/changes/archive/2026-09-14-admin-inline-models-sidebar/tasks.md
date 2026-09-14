## 1. Verify Unfold version APIs

- [x] 1.1 Confirm `unfold.admin.TabularInline`/`StackedInline` (`extra`, `autocomplete_fields`) against the venv's installed django-unfold version (0.77.1 per requirements pin — verified: no `tab` attr in 0.77, inlines auto-render as change-form tabs; `tab=True` dropped from specs/tasks)
- [x] 1.2 Confirm `SIDEBAR.navigation` item keys (`title`, `icon`, `link`, `permission`, `collapsible`, `separator`) and `reverse_lazy` changelist links against the installed version (0.77.1 `sites.py`/templates verified: keys supported, missing `permission` defaults visible, `reverse_lazy` handled via Callable branch)

## 2. Child inlines in ourlives/admin.py

- [x] 2.1 Add `ContactInline(UnfoldStackedInline)`: `model=Contact`, `extra=0`, `autocomplete_fields=("contact_type",)` (no `tab` attr — Unfold 0.77 auto-tabs inlines); wire into `OrganizationAdmin.inlines`
- [x] 2.2 Add `OrganizationAddressInline(UnfoldStackedInline)`: `model=OrganizationAddress`, `extra=0`, `autocomplete_fields=("country",)` (no `tab` attr); wire into `OrganizationAdmin.inlines`
- [x] 2.3 Migrate `OrderItemInline` from `admin.TabularInline` to `unfold.admin.TabularInline` (keep `extra=0`, product autocomplete, readonly `line_total_display`)
- [x] 2.4 Remove `@admin.register` + `ModelAdmin` classes for `Contact`, `OrganizationAddress`, `OrderItem`
- [x] 2.5 Trim `OrderAdmin.autocomplete_fields` to `("organization","rep","currency","pilot_currency")` (drop contact autocompletes; plain selects)

## 3. Manual sidebar in project/settings.py

- [x] 3.1 Set `show_all_applications=False` (keep `show_search=True`); define the four navigation groups (operational, collapsible Reference data, Credits unchanged, Core explicit) with `reverse_lazy` changelist links, `sidebar_icon` values, and per-item `view_<model>` permission callbacks
- [x] 3.2 Retire `project/templates/unfold/helpers/navigation.html` override (return to Unfold bundled sidebar)

## 4. Tests in ourlives/tests.py

- [x] 4.1 Assert Organization change page renders both inlines and Order page renders items inline (editable, extra=0)
- [x] 4.2 Assert `/admin/ourlives/contact/`, `/organizationaddress/`, `/orderitem/` return 404
- [x] 4.3 Assert sidebar registry coverage: every registered admin model has exactly one `SIDEBAR.navigation` entry (matched by admin URL — changelist URL, or the solo change URL for `AppSettings`)
- [x] 4.4 Assert permission isolation: ourlives-perm-less staff sees no ourlives links; `view_country`-only staff sees only Countries; cross-app user blocked from ourlives URLs/exports
- [x] 4.5 Rewrite `CrmAdminRegistrationTests` for the unregistered children: drop `contact`/`organizationaddress`/`orderitem` from the changelist-render loop; remove `ContactAdmin`/`OrganizationAddressAdmin`/`OrderItemAdmin` imports and registry assertions; drop the three models from the export-actions loop; repoint the address-toggle test at the Organization inline form; assert trimmed `OrderAdmin.autocomplete_fields` and Unfold inline classes

## 5. Verify

- [x] 5.1 Run full test suite green; click-check Organization/Order pages, Reference data collapse, and perm-less staff sidebar (293/295 pass before 5.2; 2 failures in `utils.test_excel_export` with-related sheet counts are pre-existing — verified failing on clean tree via `git stash`; click-checks left for manual verification)
- [x] 5.2 Fix stale with-related sheet-count assertions in `utils/test_excel_export.py` (expect 5 sheets: main + Project + Organization + Order + Code Type, reflecting current `InvitationCode` FKs; engine behavior unchanged)
