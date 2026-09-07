## 1. Admin registration

- [x] 1.1 Extend `ourlives/admin.py` import to include `Country`, `Rep`, `ContactType`, `CodeType`, `OrderType`
- [x] 1.2 Add `CountryAdmin(OurlivesModelAdminBase)` with globe icon, display/filter/search/editable/links and `has_add/delete_permission=False`
- [x] 1.3 Add `RepAdmin(OurlivesModelAdminBase)` with person icon, display `(first_name,last_name,email)` and matching search
- [x] 1.4 Add `ContactTypeAdmin`, `CodeTypeAdmin` (incl. `max_codes` display), `OrderTypeAdmin` with contacts/sell/shopping_bag icons, `(code,name[,max_codes],active)` display, `active` filter, `(code,name)` search, inline `active` toggle
- [x] 1.5 Tune `InvitationCodeAdmin`: add `autocomplete_fields=(project,organization)` and `list_editable=(is_active,)` keeping `list_display_links=(code,)`

## 2. Verification

- [x] 2.1 Run `python manage.py check` — passes with no admin `ImproperlyConfigured` (editable-vs-link) errors
- [x] 2.2 Run `pytest ourlives/tests.py -q` — existing suite green (no model/fixture changes)
- [x] 2.3 Admin smoke: 5 changelists render with expected filters/search; Country shows no Add button and blocks direct add/delete; inline `active` toggles persist; InvitationCode FKs render as autocomplete
- [x] 2.4 Export smoke: per-model `Export to Excel` on a new changelist + header `Export all app data` workbook contains the 5 new sheets
