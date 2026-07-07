## MODIFIED Requirements

### Requirement: Brand palette renders on logout screen
The logout screen SHALL display the brand's primary color palette CSS (`user_palette_css`) injected into the page `<head>`. When a `?brand=<slug>` query parameter is present in the logout URL, the palette SHALL resolve to that brand. When no query parameter is present, the palette SHALL resolve to the default brand. The `:root:root` CSS custom properties SHALL override Unfold's static theme colors via higher specificity.

#### Scenario: Logged-out user sees query-string brand palette on /admin/logout/?brand=testbrand6
- **WHEN** a user visits `/admin/logout/?brand=testbrand6` and the brand slug resolves to a valid brand
- **THEN** the page SHALL include a `<style id="user-palette">` element containing the CSS custom properties
- **AND** the `:root:root` CSS variables SHALL match those rendered for the "testbrand6" brand

#### Scenario: Logged-out user sees default brand palette when no query string
- **WHEN** a user visits `/admin/logout/` without a `?brand=` query parameter and a default brand exists
- **THEN** the page SHALL include a `<style id="user-palette">` element containing the default brand's CSS custom properties

#### Scenario: Graceful fallback when palette is empty
- **WHEN** `user_palette_css` is empty or not available in the context
- **THEN** no extra `<style>` tag SHALL be rendered

### Requirement: Template override does not modify logout content
The custom template SHALL extend Unfold's existing `registration/logged_out.html` and SHALL add the palette CSS injection. The "Log in again" button SHALL target the admin login URL with the brand query parameter from the current request. All other logout page content, text, and layout SHALL remain unchanged from Unfold's default.

#### Scenario: Logout content unchanged
- **WHEN** a user visits `/admin/logout/`
- **THEN** the page SHALL display Unfold's default logout message ("You have been successfully logged out from the administration")
- **AND** the page SHALL display a "Log in again" button styled as primary

#### Scenario: Button links to branded login
- **WHEN** a user visits `/admin/logout/?brand=testbrand6`
- **THEN** the "Log in again" button SHALL link to `/admin/login/?brand=testbrand6`
