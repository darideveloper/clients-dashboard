## ADDED Requirements

### Requirement: Brand palette renders on logout screen
The logout screen SHALL display the default brand's primary color palette CSS (`user_palette_css`) injected into the page `<head>`, matching the brand appearance of the login and admin pages. The `:root:root` CSS custom properties SHALL override Unfold's static theme colors via higher specificity.

#### Scenario: Logged-out user sees brand palette on /admin/logout/
- **WHEN** a user visits `/admin/logout/` and `user_palette_css` is available in the template context
- **THEN** the page SHALL include a `<style id="user-palette">` element containing the CSS custom properties
- **AND** the `:root:root` CSS variables SHALL match those rendered on the login page for the default brand

#### Scenario: Graceful fallback when palette is empty
- **WHEN** `user_palette_css` is empty or not available in the context
- **THEN** no extra `<style>` tag SHALL be rendered

### Requirement: Template override does not modify logout content
The custom template SHALL extend Unfold's existing `registration/logged_out.html` and SHALL only add the palette CSS injection — the page content, text, and button SHALL remain unchanged.

#### Scenario: Logout content unchanged
- **WHEN** a user visits `/admin/logout/`
- **THEN** the page SHALL display Unfold's default logout message ("You have been successfully logged out from the administration")
- **AND** the "Log in again" button SHALL link to `admin:index`
