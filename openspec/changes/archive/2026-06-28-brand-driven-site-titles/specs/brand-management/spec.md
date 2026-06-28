## ADDED Requirements

### Requirement: Brand.name drives admin chrome site titles
The `Brand.name` field SHALL serve as the source for the admin's `SITE_TITLE` and `SITE_HEADER` Unfold config values, formatted as `brand.name`. The `SITE_SUBHEADER` SHALL always be `"Dashboard"`. Anonymous users and users without a brand SHALL see fallback values `"clients"` / `"Dashboard"`.

- The callbacks `utils.callbacks.site_title` and `utils.callbacks.site_header` SHALL resolve `request.user.brand.name`
- The default brand row (`name="Default Brand"`) SHALL produce `"Default Brand"` / `"Dashboard"` — no special-case filtering
- Each callback SHALL fall back to its application-default string when the user is unauthenticated or has no brand

#### Scenario: Branded site header text
- **WHEN** an authenticated user whose brand has `name="Acme Corp"` loads the admin
- **THEN** the sidebar header SHALL display "Acme Corp"
- **AND** the sidebar subtitle SHALL display "Dashboard"
- **AND** the browser tab title SHALL be "Acme Corp"

#### Scenario: Fallback for anonymous user
- **WHEN** an unauthenticated request reaches any site-title callback
- **THEN** the callback SHALL return the hardcoded fallback string

#### Scenario: Default brand produces generic titles
- **WHEN** an authenticated user with the Default Brand (`name="Default Brand"`) loads the admin
- **THEN** the sidebar header SHALL display "Default Brand"
- **AND** the sidebar subtitle SHALL display "Dashboard"
- **AND** the browser tab title SHALL be "Default Brand"
