## Requirements

### Requirement: Brand slug available in template context
The `user_palette` context processor SHALL expose a `current_brand_slug` variable containing the resolved brand's slug string in every admin template context, including unauthenticated pages like logout.

#### Scenario: Authenticated user gets their brand slug
- **WHEN** an authenticated user with a brand views any admin page
- **THEN** `current_brand_slug` SHALL equal the user's brand slug

#### Scenario: Anonymous user gets default brand slug
- **WHEN** an anonymous user views the logout page
- **THEN** `current_brand_slug` SHALL equal the default brand's slug
- **AND** the variable SHALL be an empty string if no default brand exists

### Requirement: Brand identity preserved via _brand_cache across logout
The brand identity SHALL be preserved on the logout page through Django's `_brand_cache` mechanism: `AdminSite.logout()` calls `each_context()` before `auth_logout()`, which triggers `_resolve_brand()` and caches the result. The `user_palette` context processor reads from this cache during template rendering after logout.

#### Scenario: User's brand slug available on logout page
- **WHEN** an authenticated user with brand "testbrand6" logs out via POST to `/admin/logout/`
- **THEN** the logout page SHALL have `current_brand_slug` equal to `"testbrand6"`
- **AND** `user_palette_css` SHALL contain the brand's palette CSS

#### Scenario: Default brand slug on logout page without user brand
- **WHEN** an authenticated user without a brand logs out and a default brand exists
- **THEN** `current_brand_slug` SHALL equal the default brand's slug

#### Scenario: Empty slug when no brand at all
- **WHEN** an authenticated user without a brand logs out and no default brand exists
- **THEN** `current_brand_slug` SHALL be an empty string

### Requirement: "Log in again" button links to branded login
The "Log in again" button on the logout page SHALL link to the admin login page with the `?brand=` query parameter populated from the `current_brand_slug` context variable, preserving the brand for the redirected login experience.

#### Scenario: Button links to branded login for user with brand
- **WHEN** an authenticated user with brand "testbrand6" logs out via POST to `/admin/logout/`
- **THEN** the "Log in again" button SHALL link to `/admin/login/?brand=testbrand6`

#### Scenario: Button links to branded login for default brand
- **WHEN** an authenticated user without a brand logs out and a default brand "default-co" exists
- **THEN** the "Log in again" button SHALL link to `/admin/login/?brand=default-co`

#### Scenario: Button falls back to admin index without brand
- **WHEN** an authenticated user without a brand logs out and no default brand exists
- **THEN** the "Log in again" button SHALL link to `/admin/` (default brand fallback, matching Unfold's original behavior)
