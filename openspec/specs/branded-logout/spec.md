## Requirements

### Requirement: Brand palette renders on logout screen
The logout screen SHALL display the brand's primary color palette CSS (`user_palette_css`) injected into the page `<head>`. The brand identity SHALL be resolved via `_resolve_brand()` which caches during `each_context()` (called before `auth_logout()`) and reads from `_brand_cache` during template rendering. The `:root:root` CSS custom properties SHALL override Unfold's static theme colors via higher specificity.

#### Scenario: Logged-out user sees brand palette
- **WHEN** a user visits `/admin/logout/` and `user_palette_css` is available in the template context
- **THEN** the page SHALL include a `<style id="user-palette">` element containing the CSS custom properties

#### Scenario: Graceful fallback when palette is empty
- **WHEN** `user_palette_css` is empty or not available in the context
- **THEN** no extra `<style>` tag SHALL be rendered

### Requirement: Template override updates "Log in again" button
The custom template SHALL extend Unfold's existing `registration/logged_out.html` and SHALL add the palette CSS injection. The "Log in again" button SHALL target the admin login URL with the brand slug from the `current_brand_slug` context variable. All other logout page content, text, and layout SHALL remain unchanged from Unfold's default.

#### Scenario: Button links to branded login
- **WHEN** a user logs out and `current_brand_slug` is set
- **THEN** the "Log in again" button SHALL link to `/admin/login/?brand=<slug>`

#### Scenario: Button falls back to admin index
- **WHEN** a user logs out and `current_brand_slug` is empty
- **THEN** the "Log in again" button SHALL link to `/admin/`
