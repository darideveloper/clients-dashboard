## MODIFIED Requirements

### Requirement: Unfold config block
`settings.UNFOLD` SHALL set `SITE_TITLE`, `SITE_HEADER`, `SITE_SUBHEADER`, `SITE_URL="/"`, `SITE_ICON` resolving to `static("favicon.png")`, `SITE_LOGO` resolving to `static("logo.webp")`, `SITE_SYMBOL`, `SITE_FAVICONS` containing a 32×32 PNG pointing to `favicon.png`, `SHOW_HISTORY=True`, `SHOW_VIEW_ON_SITE=True`, `ENVIRONMENT` pointing to `utils.callbacks.environment_callback`, `THEME="light"`, an OKLCH `primary` color palette covering shades 50–950, and a `SIDEBAR` block with `show_search=True`, `show_all_applications=True`, and an empty `navigation: []`. The sidebar body SHALL be rendered by the override template `project/templates/unfold/helpers/navigation.html`, which auto-renders every registered `ModelAdmin` filtered by the request user's per-model permissions; see the `unfold-permission-sidebar` capability for the rendering contract.

#### Scenario: Site branding
- **WHEN** the admin loads
- **THEN** the sidebar shows the favicon/logo and the site header text "clients Admin"

#### Scenario: Environment badge
- **WHEN** `ENV=dev` and `utils.callbacks.environment_callback` runs
- **THEN** it returns `["Development", "info"]`

#### Scenario: Sidebar uses auto-render with permission filter
- **WHEN** a user loads any admin page
- **THEN** the sidebar body is populated from `available_apps` (permission-filtered by Django's `AdminSite.get_app_list`) via the override template at `project/templates/unfold/helpers/navigation.html`, and `UNFOLD["SIDEBAR"]["navigation"]` is `[]`.

## REMOVED Requirements

### Requirement: Authentication sidebar exposes Users and Groups
**Reason**: The sidebar is no longer driven by a hand-written `navigation` list. Users and Groups are auto-rendered from the registered `auth.User` and `auth.Group` `ModelAdmin` classes (in `core/admin.py`), subject to the request user's per-model permissions. The visibility contract is now covered by the `unfold-permission-sidebar` capability's "Sidebar auto-renders all registered apps and models" requirement.
**Migration**: No code migration needed. To restore a hand-pinned Users/Groups link, reintroduce an `Authentication` group in `UNFOLD["SIDEBAR"]["navigation"]` and switch the auto-render off by removing the override template; both changes are out of scope for this change.
