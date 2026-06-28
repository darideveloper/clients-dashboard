## Why

The current Unfold sidebar uses a manually curated `navigation` list with `show_all_applications=False`, so the team has to hand-write an entry for every new model and links stay visible to users who lack permission to act on them. The goal is an Unfold-styled sidebar body that auto-renders every registered `ModelAdmin`, is filtered by the request user's per-model permissions, and supports a custom Material icon per admin. Non-superusers see only the apps and models they are actually allowed to use, and adding a new model in `core/` requires no sidebar change.

**Important constraint discovered during investigation:** Unfold's `UNFOLD["SIDEBAR"]` config has no setting that auto-populates the sidebar body from registered `ModelAdmin` classes. The documented `show_all_applications` flag adds a single "All applications" **modal button** at the bottom of the sidebar — it does not render apps inline. An empty `navigation` causes Unfold to fall back to Django's classic `admin/app_list.html` (table markup, not Unfold styling). Therefore, an Unfold-styled permission-filtered auto sidebar requires a **template override** at `project/templates/unfold/helpers/navigation.html`, in addition to the settings change.

## What Changes

- **Template override**: a new `project/templates/unfold/helpers/navigation.html` that renders `available_apps` (Django's permission-filtered app list, provided by `AdminSite.get_app_list(request)`) using Unfold's sidebar group/link DOM. The override preserves Unfold's `navigation_header`, `search`, and `navigation_user` partials so the surrounding chrome is unchanged. This is the load-bearing change.
- **Settings change** in `project/settings.py`: `UNFOLD["SIDEBAR"]["navigation"]` becomes `[]`; `show_all_applications` becomes `True`. The hand-written `Authentication` and `Core` groups are removed from `navigation`. The now-unused `reverse_lazy` and `gettext_lazy as _` imports are removed in the same edit. The `TEMPLATES[0]["OPTIONS"]` dict gains a `libraries` entry that registers `sidebar_extras` (otherwise the template tag library under `utils/templatetags/` is not auto-discovered, since `utils` is not in `INSTALLED_APPS`).
- **Permission filter**: each model link is gated by Django's `ModelAdmin.has_module_permission` + `get_model_perms` (the same filter Django's admin index uses, applied automatically inside `available_apps`). Apps whose every model is filtered out are not rendered. No per-item `permission` callback is needed; the override iterates a pre-filtered list.
- **Per-model icon support** via a new `sidebar_icon` class attribute on `ModelAdminUnfoldBase` (default `"database"`). The icon is looked up by the template from a `sidebar_icons` context map built by `utils.admin_icons.build_sidebar_icon_map()` (walks `admin.site._registry` once per request) and injected by the existing `utils.context_processors.user_palette` context processor (which now returns both `user_palette_css` and `sidebar_icons`). The template reads the map through a `get_item` filter defined in a new `utils.templatetags.sidebar_extras` library. Admins override the icon by setting the class attribute on their `ModelAdmin` subclass.
- **Superusers** see every registered app and model (current behavior, preserved).
- **User with no admin permissions** sees the existing "You don't have permission to view or edit anything." message; the rest of the admin chrome (header, search, user menu) is intact.
- `project/templates/admin/base_site.html` and the `utils/callbacks.py` env badge are unchanged.

## Capabilities

### New Capabilities

- `unfold-permission-sidebar`: Permission-aware auto sidebar — overrides Unfold's `unfold/helpers/navigation.html` to render the sidebar body from `available_apps` (Django's permission-filtered app list) using Unfold styling. Configures `UNFOLD["SIDEBAR"]` with `navigation: []` and `show_all_applications: True`. Supports per-model Material icons via a `sidebar_icon` class attribute on `ModelAdminUnfoldBase`, resolved at render time through a context-injected icon map and a `get_item` template filter.

### Modified Capabilities

- `unfold-admin-theme`: The `SIDEBAR` requirement changes from `show_all_applications=False` + manual `Authentication` group with `Users`/`Groups` items to `show_all_applications=True`, empty `navigation`, with rendering delegated to a new template override. The standalone "Authentication sidebar exposes Users and Groups" requirement is replaced by a permission-filtered auto-rendering contract from the `unfold-permission-sidebar` capability.

## Impact

- `project/settings.py`: `UNFOLD["SIDEBAR"]["navigation"]` → `[]`, `show_all_applications` → `True`, the curated `Authentication` and `Core` groups removed; the `reverse_lazy` and `gettext_lazy as _` imports are removed because nothing in `settings.py` uses them anymore; `TEMPLATES[0]["OPTIONS"]` gains a `libraries` entry mapping `"sidebar_extras"` to `"utils.templatetags.sidebar_extras"`.
- `project/templates/unfold/helpers/navigation.html` (new file): the override that renders `available_apps` in Unfold styling. The icon for each model is resolved via `{{ sidebar_icons|get_item:app.app_label|add:"."|add:model.object_name|lower|default:"database" }}`. Same dir as the existing override `project/templates/admin/base_site.html` (per `django-unfold-admin.md §6`); no new templates-dir config needed.
- `project/admin_base.py`: `ModelAdminUnfoldBase` gains a `sidebar_icon = "database"` class attribute.
- `utils/admin_icons.py` (new file): `build_sidebar_icon_map()` walks `admin.site._registry` and returns a `{model._meta.label_lower: model_admin.sidebar_icon}` mapping.
- `utils/context_processors.py`: the existing `user_palette(request)` context processor now also returns `sidebar_icons: build_sidebar_icon_map()` alongside the existing `user_palette_css` key.
- `utils/templatetags/__init__.py` (new, empty) and `utils/templatetags/sidebar_extras.py` (new): a `get_item` template filter that returns `mapping.get(key)`.
- No new pip packages, no DB migrations, no custom `AdminSite` subclass, no `permission` callback.
- The override assumes Unfold keeps `{% include "unfold/helpers/navigation.html" %}` at `nav_sidebar.html:10` and the helper's context contract (`available_apps`, `sidebar_navigation`, `sidebar_show_all_applications`, `sidebar_show_search`) stable. The include site is a single line in a stable template; the context contract has been stable since at least Unfold 0.55. Pin to `django-unfold==0.77.1` is already in `requirements.txt` per `django-unfold-admin.md §1`.
- Verifiable manually: log in as a non-superuser, confirm only permitted apps appear; log in as superuser, confirm all apps appear; log in as a user with no admin perms, confirm the "no permission" message. To confirm per-model icons: open the `/admin/` page in a browser and inspect each sidebar link; the Material symbol rendered inside each link matches the admin's `sidebar_icon` attribute (or `"database"` if not set).
