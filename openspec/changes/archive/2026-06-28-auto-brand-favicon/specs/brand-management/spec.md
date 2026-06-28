# brand-management Specification (Delta)

## ADDED Requirements

### Requirement: Brand logo auto-generates a square favicon
The `Brand` model SHALL auto-generate a 32×32 square PNG favicon from its `logo` ImageField whenever the logo is uploaded or changed. The favicon SHALL be stored as `brands/brand_<pk>/favicon.png` on the same storage backend as the logo. When the logo is removed or the brand is deleted, the favicon SHALL be cleaned up.

#### Scenario: Logo uploaded generates favicon
- **WHEN** a superuser uploads a logo to a Brand via the admin
- **THEN** a 32×32 PNG favicon center-cropped from the logo SHALL be created at `brands/brand_<pk>/favicon.png`

#### Scenario: Logo replaced regenerates favicon
- **WHEN** a superuser replaces an existing logo on a Brand
- **THEN** the old favicon SHALL be deleted and a new one generated from the new logo

#### Scenario: Logo removed deletes favicon
- **WHEN** a superuser clears the logo field on a Brand
- **THEN** the existing favicon SHALL be deleted

#### Scenario: Brand deleted cleans up favicon
- **WHEN** a Brand instance is deleted
- **THEN** its favicon file SHALL be deleted from storage

### Requirement: Favicon serves through UNFOLD SITE_FAVICONS callback
The system SHALL expose `utils.callbacks.site_favicon(request)` that resolves to the brand's generated favicon URL or falls back to `static("favicon.png")`. The `UNFOLD["SITE_FAVICONS"]` config SHALL use this callback as its `href`.

#### Scenario: Per-brand favicon in admin tab
- **WHEN** an authenticated user with a brand logo loads the admin
- **THEN** the `UNFOLD["SITE_FAVICONS"]` link SHALL point to the brand's auto-generated favicon URL
