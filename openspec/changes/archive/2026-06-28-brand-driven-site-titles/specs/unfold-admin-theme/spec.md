## MODIFIED Requirements

### Requirement: Unfold config block
`settings.UNFOLD` SHALL set `SITE_TITLE` (lambda resolving from `utils.callbacks.site_title`), `SITE_HEADER` (lambda resolving from `utils.callbacks.site_header`), `SITE_SUBHEADER` (lambda resolving from `utils.callbacks.site_subheader`), `SITE_URL="/"`, `SITE_ICON` (lambda resolving from `utils.callbacks.site_icon`), `SITE_SYMBOL`, `SITE_FAVICONS` containing a 32×32 PNG pointing to `favicon.png`, `SHOW_HISTORY=True`, `SHOW_VIEW_ON_SITE=True`, `ENVIRONMENT` pointing to `utils.callbacks.environment_callback`, `THEME="light"`, an OKLCH `primary` color palette covering shades 50–950, and a `SIDEBAR` block with `show_search=True`, `show_all_applications=True`, and an empty `navigation: []`. The sidebar body SHALL be rendered by the override template `project/templates/unfold/helpers/navigation.html`, which auto-renders every registered `ModelAdmin` filtered by the request user's per-model permissions; see the `unfold-permission-sidebar` capability for the rendering contract. `SITE_LOGO` SHALL NOT be set (removed so the per-user brand logo from `SITE_ICON` is not shadowed).

#### Scenario: Site branding
- **WHEN** the admin loads for an authenticated user whose brand has `name="Acme Corp"`
- **THEN** the sidebar shows the site icon and the site header text "Acme Corp" with subtitle "Dashboard"
- **WHEN** the admin loads for an unauthenticated user (login page) or an authenticated user with no brand (no `Membership` row)
- **THEN** the sidebar shows the site icon and the site header text "clients" with subtitle "Dashboard"

