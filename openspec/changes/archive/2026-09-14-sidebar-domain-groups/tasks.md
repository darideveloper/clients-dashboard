## 1. Sidebar regrouping (settings only)

- [x] 1.1 Remove the `Order Items`, `Contacts`, and `Addresses` item dicts from the Our Lives group in `UNFOLD["SIDEBAR"]["navigation"]`.
- [x] 1.2 Insert the new collapsible + separator **Order Data** group after Our Lives with `Order Items` (`list_alt`, `admin:ourlives_orderitem_changelist`, `ourlives.view_orderitem`) and `Order Types` (`shopping_bag`, `admin:ourlives_ordertype_changelist`, `ourlives.view_ordertype`); remove `Order Types` from Reference data.
- [x] 1.3 Insert the new collapsible + separator **Organization Data** group after Order Data with `Contacts` (`contact_mail`, `admin:ourlives_contact_changelist`, `ourlives.view_contact`), `Addresses` (`location_on`, `admin:ourlives_organizationaddress_changelist`, `ourlives.view_organizationaddress`), and `Contact Types` (`contacts`, `admin:ourlives_contacttype_changelist`, `ourlives.view_contacttype`); remove `Contact Types` from Reference data.
- [x] 1.4 Verify against `admin.site._registry`: every registered model has exactly one nav entry and no entry is orphaned (the `SidebarCoverageTests` test enforces this — run it).

## 2. Icon deduplication

- [x] 2.1 Change `RepAdmin.sidebar_icon` from `"person"` to `"badge"` in `ourlives/admin.py`.
- [x] 2.2 Change the TokenProxy admin `sidebar_icon` from `"key"` to `"vpn_key"` in `core/admin.py` (fallbacks if a glyph is missing from the deployed font: Reps → `assignment_ind`, Tokens → `password`).
- [x] 2.3 Grep tests for `sidebar_icon` pins (proposal audit found none — coverage/permission tests walk groups generically); if the suite flags one, update the test to the new glyph, never the spec delta.

## 3. Verification

- [x] 3.1 Run the full suite (`venv/bin/python manage.py test`) — must be green with no test-code changes.
- [x] 3.2 Visual check on dev admin: six groups in order, both new groups collapsible with separators, auto-open when inside, unique icons throughout.
- [x] 3.3 Visual check as a limited-permission user (e.g. `view_country` only): only permitted links render; direct URLs to hidden models return 403.
