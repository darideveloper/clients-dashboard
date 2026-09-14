## MODIFIED Requirements

### Requirement: Favicon is exposed via a callback
The system SHALL provide a `utils.callbacks.site_favicon(request)` callable that returns the per-brand favicon URL when the user is authenticated, has a brand with a logo, and the generated `favicon.png` exists in storage, falling back to `static("favicon.png")` otherwise.

#### Scenario: Authenticated user with brand logo
- **WHEN** an authenticated user whose `Brand` has a logo loads the admin
- **THEN** `site_favicon(request)` SHALL return the URL of the generated `favicon.png` for that brand

#### Scenario: Authenticated user with brand but no logo
- **WHEN** an authenticated user whose `Brand` has no logo loads the admin
- **THEN** `site_favicon(request)` SHALL return `static("favicon.png")`

#### Scenario: Unauthenticated request
- **WHEN** an unauthenticated request reaches the favicon callback
- **THEN** `site_favicon(request)` SHALL return `static("favicon.png")`

#### Scenario: Brand logo present but generated favicon file missing
- **WHEN** an authenticated user whose `Brand` has a logo loads the admin but no `favicon.png` exists in storage at `brands/brand_<pk>/favicon.png` (e.g. logo predates auto-generation, arrived via fixtures, or was deleted out of band)
- **THEN** `site_favicon(request)` SHALL return `static("favicon.png")`
- **AND** the browser tab SHALL NOT reference a nonexistent storage object
