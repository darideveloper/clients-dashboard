# auto-favicon-generation Specification

## Purpose
Auto-generate a 32×32 square PNG favicon from each brand's logo, stored alongside the logo on the same storage backend, so that the admin tab icon reflects the user's brand identity.

## Requirements

### Requirement: Brand logo changes trigger favicon generation
When a `Brand.logo` is uploaded or replaced, the system SHALL generate a derived favicon file: center-crop the logo to a square, resize to 32×32 pixels, and save as a PNG named `favicon.png` in the same storage directory as the logo (`brands/brand_<pk>/favicon.png`).

#### Scenario: Logo uploaded for first time
- **WHEN** a superuser uploads a logo to a `Brand` instance via the admin form
- **THEN** a file at `brands/brand_<pk>/favicon.png` SHALL be created on the same storage backend
- **AND** the favicon SHALL be a 32×32 PNG, center-cropped to square from the original logo
- **AND** the original logo image SHALL be unchanged

#### Scenario: Logo replaced
- **WHEN** a superuser replaces the logo on an existing `Brand`
- **THEN** the old `favicon.png` SHALL be deleted
- **AND** a new `favicon.png` SHALL be generated from the new logo

#### Scenario: Logo removed (set to empty)
- **WHEN** a superuser clears the logo field on a `Brand` (sets it to blank/empty)
- **THEN** the existing `favicon.png` at `brands/brand_<pk>/favicon.png` SHALL be deleted

#### Scenario: Logo not provided
- **WHEN** a `Brand` is created without a logo
- **THEN** no favicon file SHALL be generated
- **AND** no error SHALL be raised

#### Scenario: Brand with non-square logo
- **WHEN** a `Brand` has a logo with unequal width and height (e.g., 1200×800)
- **THEN** the generated favicon SHALL center-crop to the shorter dimension, making a square before resizing to 32×32

### Requirement: Favicon uses same storage backend as logo
The generated favicon SHALL be saved using the same storage backend as the logo field to ensure S3/local consistency without additional configuration.

#### Scenario: S3 storage in production
- **WHEN** `STORAGE_AWS=True` and a logo is on S3 `PublicMediaStorage`
- **THEN** the favicon SHALL be stored in the same S3 bucket and location prefix as the logo (`<PUBLIC_MEDIA_LOCATION>/brands/brand_<pk>/favicon.png`)
- **AND** the favicon SHALL inherit the same `CacheControl` and `ACL` settings as the logo via the shared storage backend

#### Scenario: Local storage in development
- **WHEN** `STORAGE_AWS=False` and a logo is on the local filesystem
- **THEN** the favicon SHALL be stored at `<MEDIA_ROOT>/brands/brand_<pk>/favicon.png`

### Requirement: Brand deletion cleans up favicon
When a `Brand` instance is deleted, the generated favicon file SHALL be removed from storage.

#### Scenario: Brand with logo is deleted
- **WHEN** a `Brand` that has a logo (and therefore a generated favicon) is deleted
- **THEN** the favicon file at `brands/brand_<pk>/favicon.png` SHALL be deleted
- **AND** the deletion SHALL happen before or during the brand's database deletion (not as a lazy/orphaned cleanup)

#### Scenario: Brand without logo is deleted
- **WHEN** a `Brand` without a logo is deleted
- **THEN** no favicon deletion SHALL be attempted
- **AND** no error SHALL be raised

### Requirement: Favicon is exposed via a callback
The system SHALL provide a `utils.callbacks.site_favicon(request)` callable that returns the per-brand favicon URL when the user is authenticated and has a brand with a logo, falling back to `static("favicon.png")` otherwise.

#### Scenario: Authenticated user with brand logo
- **WHEN** an authenticated user whose `Brand` has a logo loads the admin
- **THEN** `site_favicon(request)` SHALL return the URL of the generated `favicon.png` for that brand

#### Scenario: Authenticated user with brand but no logo
- **WHEN** an authenticated user whose `Brand` has no logo loads the admin
- **THEN** `site_favicon(request)` SHALL return `static("favicon.png")`

#### Scenario: Unauthenticated request
- **WHEN** an unauthenticated request reaches the favicon callback
- **THEN** `site_favicon(request)` SHALL return `static("favicon.png")`

### Requirement: Favicon generation uses Pillow with LANCZOS resampling
The image processing pipeline SHALL use `PIL.Image.LANCZOS` (or `PIL.Image.Resampling.LANCZOS` on Pillow >= 10) for high-quality downscaling.

#### Scenario: Downscaling preserves visual quality
- **WHEN** a large logo (e.g., 2000×2000) is resized to 32×32
- **THEN** the resulting favicon SHALL be generated using LANCZOS resampling to minimize aliasing artifacts
