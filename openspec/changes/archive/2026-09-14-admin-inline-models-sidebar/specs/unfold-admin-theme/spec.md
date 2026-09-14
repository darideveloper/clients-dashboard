## MODIFIED Requirements

### Requirement: Unfold config block
`settings.UNFOLD` SHALL set `SITE_TITLE` (lambda resolving from `utils.callbacks.site_title`), `SITE_HEADER` (lambda resolving from `utils.callbacks.site_header`), `SITE_SUBHEADER` (lambda resolving from `utils.callbacks.site_subheader`), `SITE_URL="/"`, `SITE_ICON` (lambda resolving from `utils.callbacks.site_icon`), `SITE_SYMBOL`, `SITE_FAVICONS` containing a 32×32 PNG whose `href` is resolved by `utils.callbacks.site_favicon`, `SHOW_HISTORY=True`, `SHOW_VIEW_ON_SITE=True`, `ENVIRONMENT` pointing to `utils.callbacks.environment_callback`, `THEME="light"`, an OKLCH `primary` color palette covering shades 50–950 (static fallback), and a `SIDEBAR` block with `show_search=True`, `show_all_applications=False`, and the curated four-group `navigation` (operational ourlives models, collapsible Reference data, Credits, Core — see the `manual-admin-sidebar` capability for the group contract). All branding callbacks resolve the active brand through the unified 4-tier priority chain: URL override (`?brand=<slug>`) → user's brand (`Membership`) → default brand (`is_default=True`) → hardcoded fallback. The primary color palette is injected per-request via `utils.context_processors.user_palette` (not `UNFOLD["STYLES"]`). The sidebar body SHALL be rendered by Unfold's bundled sidebar from `SIDEBAR.navigation` (the override template `project/templates/unfold/helpers/navigation.html` is deleted); see the `manual-admin-sidebar` capability for the rendering contract. `SITE_LOGO` SHALL NOT be set (removed so the per-brand logo from `SITE_ICON` is not shadowed).

#### Scenario: Site branding
- **WHEN** the admin loads for an authenticated user whose brand has `name="Acme Corp"`
- **THEN** the sidebar shows the site icon and the site header text "Acme Corp" with subtitle "Dashboard"
- **WHEN** the admin loads for an unauthenticated user (login page) or an authenticated user with no brand (no `Membership` row) and a `Brand` marked `is_default=True` exists
- **THEN** the sidebar shows the default brand's icon/logo, name, and primary color palette
- **WHEN** the admin loads and no default brand exists (`is_default=True` row absent)
- **THEN** the sidebar shows the site icon and the site header text "clients" with subtitle "Dashboard" (hardcoded fallback)

#### Scenario: Per-brand favicon in browser tab
- **WHEN** an authenticated user with a brand logo loads the admin
- **THEN** the browser tab icon SHALL be the brand's generated 32×32 favicon (sourced from `utils.callbacks.site_favicon`)

#### Scenario: Fallback favicon for brands without logo
- **WHEN** an authenticated user whose brand has no logo loads the admin
- **THEN** the browser tab icon SHALL fall back to `static("favicon.png")`

#### Scenario: Environment badge
- **WHEN** `ENV=dev` and `utils.callbacks.environment_callback` runs
- **THEN** it returns `["Development", "info"]`

#### Scenario: Sidebar uses manual navigation with permission filter
- **WHEN** a user loads any admin page
- **THEN** the sidebar body is populated from `UNFOLD["SIDEBAR"]["navigation"]` (four groups; per-item `permission` callbacks filter links by the request user's permissions), `show_all_applications` is `False` (no All-applications drawer), and `UNFOLD["SIDEBAR"]["navigation"]` is not `[]`.
