## 1. Template overrides for singleton header

- [x] 1.1 Create `project/templates/admin/solo/change_form.html` extending `admin/change_form.html`, loading `i18n admin_urls`, preserving `breadcrumbs` block with `skip_object_list_page` guard (matching `solo/templates/admin/solo/change_form.html`), and replacing `object-tools-items` with Unfold `unfold/helpers/tab_action.html` includes for History (`icon="history"`, `add_preserved_filters`) and View on site (`icon="open_in_new"`, `blank=1`).
- [x] 1.2 Create `project/templates/unfold/helpers/tab_actions.html` as copy of stock `unfold` `tab_actions.html` with `gap-2` / `lg:gap-2` added to the header `<ul>` so History and Export have small spacing at desktop (row) and mobile (col) and remain vertically centered (`flex items-center` chain).
- [x] 1.3 Verify no Python changes: `ourlives/admin.py:AppSettingsAdmin` MRO stays `SingletonModelAdmin, OurlivesExportMixin, ModelAdminUnfoldBase`; `project/admin_base.py` unchanged; only two new template files (`admin/solo/change_form.html`, `unfold/helpers/tab_actions.html`).

## 2. Verification (no automated test — template-only regression)

- [x] 2.1 Manual QA: runserver, log in as permitted `is_staff` with `has_module_perms("ourlives")`, load `/admin/ourlives/appsettings/` at ≥1024px and <1024px — confirm History and Export all app data are distinct `tab_action` `<li>` siblings (borders, `px-3 py-2`, no `-ml-px` text overlap), both clickable, and that the hamburger (`more_horiz`) shows both items when collapsed.
- [x] 2.2 Regression check: click History → verify route `admin:ourlives_appsettings_history` renders; click Export all app data → verify `ourlives_full_export_*.xlsx` downloads; verify breadcrumbs show `Home › Ourlives › App settings` when `SOLO_ADMIN_SKIP_OBJECT_LIST_PAGE=True`; verify a non-singleton page (e.g. `/admin/ourlives/project/`) is unaffected.
- [x] 2.3 Run existing tests / `python manage.py check` — ensure template loads without `TemplateDoesNotExist` and `migrate` is no-op.
