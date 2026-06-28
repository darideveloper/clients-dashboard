## REMOVED Requirements

The capability `user-profile` is fully retired by the `brand-management` capability introduced in this change. Each requirement below is removed; its replacement (where applicable) is listed in `openspec/changes/profile-to-brand/specs/brand-management/spec.md`.

### Requirement: Profile model linked to User
**Reason**: The `Profile` model (one-to-one with `User`, `avatar` field) is renamed to `Brand` and the relationship is reversed to a many-users-to-one-brand `ForeignKey`. There is no longer a `Profile` concept; the successor requirement is `Brand entity` in `brand-management`.

### Requirement: Avatar upload size cap
**Reason**: The 2 MB cap on `Profile.avatar` is re-stated on the new `Brand.logo` field. The validator (`core.validators.validate_image_size`) is reused; the requirement itself lives in `brand-management` as `Brand logo upload size cap`.

### Requirement: User.avatar_url template property
**Reason**: The `User.avatar_url` property is removed. Consumers (`site_icon` callback, `navigation_user.html` template) now read directly from `user.brand.logo` or are repointed. The new `User.brand` property is unrelated to avatars — it is a brand-association accessor backed by the `Membership` model.

### Requirement: Profile auto-creation signal
**Reason**: The `post_save` signal that auto-creates a `Profile` per new `User` is removed. New users no longer auto-create a brand; admin-created users are assigned the Default Brand via `UserAdmin.save_model`, and programmatic `create_user` requires an explicit `brand`. The "no signal" rule is formalized in `brand-management` (`New users do not auto-create a brand`).

### Requirement: Admin can edit any user's avatar
**Reason**: The `ProfileAdmin` and `ProfileInline` registrations are removed. The avatar editing UX is replaced by the `BrandAdmin` (logo + primary_color) plus the `brand` field on `UserAdmin`, restricted to superusers. Replacement requirements: `Admin manages brands and assigns users to brands` in `brand-management`.

### Requirement: Admin user changelist shows avatar thumbnail
**Reason**: The `User.avatar_thumb` column is removed (and the property on `UserAdmin` is gone). A `brand` column on `UserAdmin.list_display` replaces it. See `Admin manages brands and assigns users to brands` in `brand-management`.

### Requirement: Existing users are backfilled
**Reason**: The data migration that created one `Profile` per `User` (`core/migrations/0002_backfill_profiles.py`) is preserved historically but is no longer the mechanism for new user safety. The successor mechanism is the `seed_brands` management command (`Brand.get_or_create_default()` + `--reverse`), covered by the `File relocation is idempotent and reversible (via seed_brands command)` requirement in `brand-management`.

### Requirement: Sidebar SITE_ICON reflects the viewer
**Reason**: The site icon callback (`utils.callbacks.site_icon`) no longer reads `user.avatar_url`. It now reads `user.brand.logo.url` (with the same favicon fallback for missing logo / unauthenticated). Replacement requirement: `Top-left site icon reflects the user's brand logo` in `brand-management`.

#### Scenario: Logged-in user with avatar
- **WHEN** an authenticated user with a `User.brand.logo` triggers an admin render
- **THEN** the `SITE_ICON` `src` equals `user.brand.logo.url`
- **AND** this scenario now lives in `brand-management` requirement `Top-left site icon reflects the user's brand logo`

#### Scenario: Logged-in user without avatar
- **WHEN** an authenticated user with no logo on their brand triggers an admin render
- **THEN** the `SITE_ICON` `src` falls back to `static("favicon.png")`
- **AND** this scenario now lives in `brand-management` requirement `Top-left site icon reflects the user's brand logo`

#### Scenario: Anonymous request
- **WHEN** an unauthenticated request reaches the site icon callback
- **THEN** `utils.callbacks.site_icon` returns `static("favicon.png")` and does not raise
- **AND** this scenario now lives in `brand-management` requirement `Top-left site icon reflects the user's brand logo`

#### Scenario: Settings delegate to the callback
- **WHEN** `project/settings.py` is inspected
- **THEN** `UNFOLD["SITE_ICON"]` resolves to a callable that delegates to `utils.callbacks.site_icon`
- **AND** this contract is preserved (the lambda path is unchanged; only the callback's read source changes)
