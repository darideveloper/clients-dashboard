## REMOVED Requirements

### Requirement: Sidebar auto-renders all registered apps and models

**Reason**: Replaced by explicit curated navigation (`manual-admin-sidebar` capability): the main sidebar must show a Reference data group and fixed group order, which the `available_apps` auto-render cannot express.
**Migration**: Every registered model gets exactly one entry in `UNFOLD["SIDEBAR"]["navigation"]` (enforced by the registry-coverage test); the `project/templates/unfold/helpers/navigation.html` override is retired in favor of Unfold's bundled sidebar.

### Requirement: Sidebar config in settings is empty nav plus show-all flag

**Reason**: `navigation` is now the curated four-group list and `show_all_applications` is `False` (drawer removed to avoid duplicate entries).
**Migration**: See `manual-admin-sidebar` spec for the required `navigation` content; `show_search` remains `True`.

## MODIFIED Requirements

### Requirement: Sidebar groups use Unfold styling

Each manually-configured sidebar group SHALL use Unfold's `unfold/helpers/app_list.html` group structure: a `<div>` wrapper with `x-data="{navigationOpen: ...}"`, an `<h2>` title with a chevron toggle for the collapsible Reference data group, and an `<ol>` of model links. Each model link SHALL use Unfold's nav item `<a>` class set (`flex h-[38px] items-center -mx-3 px-3 rounded-default hover:text-primary-600 dark:hover:text-primary-500`) and SHALL add the `active` classes (`bg-base-100 font-semibold text-primary-600 dark:bg-white/[.06] dark:text-primary-500`) when the link's URL is contained in the current request path. Model icons SHALL reuse each `ModelAdmin.sidebar_icon` value.

#### Scenario: Active model is highlighted

- **WHEN** the request path matches a sidebar item's link
- **THEN** that item carries the `active` class set so it is visually distinguished from the others.

#### Scenario: Groups are collapsible

- **WHEN** a user clicks the Reference data group header
- **THEN** the group's `<ol>` toggles open/closed via the `x-show` Alpine binding, matching the manual nav behavior.
