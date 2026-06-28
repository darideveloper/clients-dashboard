## ADDED Requirements

### Requirement: Sidebar auto-renders all registered apps and models
`project/templates/unfold/helpers/navigation.html` SHALL override Unfold's bundled template and render the sidebar body from `available_apps` (the permission-filtered app list provided by Django's `AdminSite.get_app_list(request)`). The override SHALL include the existing `unfold/helpers/navigation_header.html` and `unfold/helpers/search.html` partials above the body and `unfold/helpers/navigation_user.html` below it, preserving the current Unfold sidebar chrome.

#### Scenario: Superuser sees every registered model
- **WHEN** a superuser loads any admin page
- **THEN** the sidebar body lists one collapsible group per app that has at least one registered `ModelAdmin` in `INSTALLED_APPS`, and each group expands to one link per registered model whose `admin_url` points to the model's changelist.

#### Scenario: Non-superuser sees only permitted models
- **WHEN** a non-superuser with limited `view`/`change` permissions loads any admin page
- **THEN** each app group contains only the models for which the user has `view` or `change` permission (per `ModelAdmin.has_module_permission` and `get_model_perms`), and apps whose every model is filtered out are not rendered.

#### Scenario: User with no admin permissions
- **WHEN** a user with no `view`/`change` permission on any registered model loads any admin page
- **THEN** the sidebar body renders the message "You don't have permission to view or edit anything." (translated) and the rest of the Unfold chrome (header, search, user menu) remains.

#### Scenario: Adding a new ModelAdmin requires no settings change
- **WHEN** a developer registers a new `ModelAdmin` for an existing or new model
- **THEN** the new entry appears in the sidebar on next page load without any edit to `UNFOLD["SIDEBAR"]` or any other settings file.

### Requirement: Sidebar config in settings is empty nav plus show-all flag
`UNFOLD["SIDEBAR"]` SHALL set `navigation: []` (empty list) and `show_all_applications: True`. `show_search` SHALL remain `True`. The `Authentication` and `Core` group entries that were previously hard-coded in `navigation` SHALL be removed.

#### Scenario: Empty navigation in settings
- **WHEN** `project/settings.py` is read at startup
- **THEN** `UNFOLD["SIDEBAR"]["navigation"]` equals `[]` and contains no `Authentication` or `Core` group.

#### Scenario: Search input is still available
- **WHEN** the admin loads
- **THEN** the search input is rendered above the auto-generated sidebar body (because `show_search: True`).

### Requirement: Sidebar groups use Unfold styling
Each auto-rendered app group SHALL use the same DOM structure as Unfold's `unfold/helpers/app_list.html` group: a `<div>` wrapper with `x-data="{navigationOpen: ...}"`, an `<h2>` title with a chevron toggle, and an `<ol>` of model links. The first group SHALL NOT render a top `<hr>` separator; subsequent groups SHALL render a separator. Each model link SHALL use the same `<a>` class set Unfold uses for manual nav items (`flex h-[38px] items-center -mx-3 px-3 rounded-default hover:text-primary-600 dark:hover:text-primary-500`) and SHALL add the `active` classes (`bg-base-100 font-semibold text-primary-600 dark:bg-white/[.06] dark:text-primary-500`) when the link's `admin_url` is contained in the current request path. Model icons SHALL use the Material `database` symbol.

#### Scenario: Active model is highlighted
- **WHEN** the request path matches a model's `admin_url`
- **THEN** that model's link in the sidebar carries the `active` class set so it is visually distinguished from the others.

#### Scenario: Groups are collapsible
- **WHEN** a user clicks an app group header
- **THEN** the group's `<ol>` toggles open/closed via the `x-show` Alpine binding, matching the manual nav behavior.
