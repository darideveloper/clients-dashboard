# unfold-admin-theme Specification (Delta)

## MODIFIED Requirements

### Requirement: Unfold config block
`settings.UNFOLD` SHALL set `SITE_TITLE`, `SITE_HEADER`, `SITE_SUBHEADER`, `SITE_URL="/"`, `SITE_ICON` resolving to `static("favicon.png")` (overridden per-user by `utils.callbacks.site_icon`), `SITE_LOGO` resolving to `static("logo.webp")`, `SITE_SYMBOL`, `SITE_FAVICONS` containing a 32×32 PNG whose `href` resolves via `utils.callbacks.site_favicon(request)` (per-brand callback falling back to `static("favicon.png")`), `SHOW_HISTORY=True`, `SHOW_VIEW_ON_SITE=True`, `ENVIRONMENT` pointing to `utils.callbacks.environment_callback`, `THEME="light"`, an OKLCH `primary` color palette covering shades 50–950, and a `SIDEBAR` block with `show_search=True`, `show_all_applications=True`, and an empty `navigation: []`. The sidebar body SHALL be rendered by the override template `project/templates/unfold/helpers/navigation.html`, which auto-renders every registered `ModelAdmin` filtered by the request user's per-model permissions; see the `unfold-permission-sidebar` capability for the rendering contract.

#### Scenario: Site branding
- **WHEN** the admin loads
- **THEN** the sidebar shows the favicon/logo and the site header text "clients Admin"

#### Scenario: Per-brand favicon in browser tab
- **WHEN** an authenticated user with a brand logo loads the admin
- **THEN** the browser tab icon SHALL be the brand's generated 32×32 favicon (sourced from `utils.callbacks.site_favicon`)

#### Scenario: Fallback favicon for brands without logo
- **WHEN** an authenticated user whose brand has no logo loads the admin
- **THEN** the browser tab icon SHALL fall back to `static("favicon.png")`
