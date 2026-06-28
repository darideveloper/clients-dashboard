# brand-management Specification

## Purpose
TBD - created by archiving change profile-to-brand. Update Purpose after archive.
## Requirements
### Requirement: Brand entity
The system SHALL provide a `Brand` model (Django `app_label=core`) that represents a company/tenant and stores the company logo and primary brand color used to customize the admin chrome.

- Fields:
  - `logo`: `ImageField`, optional (`blank=True`), validated for image size (existing `validate_image_size`).
  - `primary_color`: `CharField(max_length=7)`, default `"#C92FFF"`, validated by `validate_hex_color` and `validate_contrast_against_white`.
- The model MUST replace the previous `Profile` model (renamed, not recreated). The schema migration is produced only by `makemigrations core` (no hand-edits). The data back-fill is performed by the `core/management/commands/seed_brands.py` command run once after the schema migration applies.

#### Scenario: Existing profile rows become brands
- **WHEN** `./manage.py seed_brands` is run against a database containing one or more `Brand` rows (formerly `Profile` rows)
- **THEN** each such row MUST be associated with the user it previously referenced (via the OneToOne column or a preserved `legacy_user_id` snapshot)
- **AND** the image file MUST be relocated from `media/avatars/user_<id>/` to `media/brands/brand_<pk>/`

#### Scenario: Logo is optional
- **WHEN** a `Brand` is saved without a logo
- **THEN** the system MUST accept the save and `brand.logo` MUST evaluate falsy
- **AND** admin chrome consumers (`site_icon`, primary palette) MUST fall back to defaults as defined in their own requirements

### Requirement: Brand logo upload size cap
The `core.Brand.logo` field SHALL reject any uploaded file whose size exceeds 2 MB (2 × 1024 × 1024 bytes). The cap MUST be implemented as a reusable validator in `core.validators` (`validate_image_size`) and attached to the `ImageField` so it applies to every save path (admin, shell, management commands, future DRF endpoints). This requirement is the direct successor of the retired `Avatar upload size cap` requirement from the `user-profile` capability.

#### Scenario: Image under 2 MB is accepted
- **WHEN** a superuser uploads a 1 MB logo through the `Brand` admin
- **THEN** the save succeeds and the logo is stored

#### Scenario: Image over 2 MB is rejected
- **WHEN** a superuser uploads a 3 MB logo through the `Brand` admin
- **THEN** the change form is invalid, the field shows a validation error, and no file is written to storage

### Requirement: Brand logo stored on configured backend
The `core.Brand.logo` field SHALL write uploads through the project's `default` storage backend — `S3` `PublicMediaStorage` in production and local `FileSystemStorage` in dev — exactly as the previous `Profile.avatar` field did. The upload path is rooted at `MEDIA_ROOT/brands/brand_<pk>/<filename>` (after the `seed_brands` command relocates legacy files). No public URL, view, or form is exposed for editing logos outside the Django admin. This requirement is the direct successor of `Avatar file is stored on the configured backend` from `user-profile`.

#### Scenario: Logo file is stored on the configured backend
- **WHEN** a superuser uploads a valid logo through the `Brand` admin
- **THEN** the file is written through the project's `default` storage backend (S3 `PublicMediaStorage` in production, local `FileSystemStorage` in dev)

#### Scenario: No public upload URL exists
- **WHEN** the URL configuration is inspected
- **THEN** no URL pattern accepts a logo upload outside the Django admin

### Requirement: User belongs to exactly one brand
The system SHALL associate each `User` with exactly one `Brand` via the `Membership` model (a `OneToOneField(User, on_delete=CASCADE, related_name="membership")` carrying a `ForeignKey(Brand, on_delete=PROTECT, related_name="memberships")`). `User.brand` is exposed as a settable property that reads/writes through the user's `Membership` row, preserving the `user.brand` API while keeping the schema auto-detectable by Django's migration framework.

- A user MUST NOT be deletable-by-cascade when their brand is deleted; instead, the `Membership.brand` `on_delete=PROTECT` MUST prevent brand deletion while memberships reference it.
- The `User.brand` property MUST return `None` if the user has no `Membership` row; assigning `None` deletes the row.

> **Note on schema shape.** The proposal originally described `User.brand` as a direct ForeignKey. Django's migration autodetector cannot see fields attached to `auth.User` from another app's `models.py`, which forced either a custom User model, a hand-edited schema migration, or — chosen here — a `Membership` OneToOne carrier with a property accessor on `User`. The `brand` lookup key on `User` is the same (`user.brand` returns a `Brand`), and the DB-level `PROTECT` semantics are preserved on `Membership.brand`.

#### Scenario: User cannot exist without a brand (admin path)
- **WHEN** a `User` is created via the Django admin without a brand
- **THEN** `UserAdmin.save_model` MUST assign the Default Brand via `Brand.get_or_create_default()`
- **AND** a `Membership(user=..., brand=...)` row MUST be created as a side effect of the property setter

#### Scenario: Brand with users cannot be deleted
- **WHEN** a superuser attempts to delete a `Brand` that has one or more `Membership` rows referencing it
- **THEN** the deletion MUST be prevented by `PROTECT`
- **AND** Django MUST surface a protected-reverse-cascade error instead of deleting the memberships (and therefore the users)

### Requirement: System default brand always exists
The system SHALL ensure that a `Brand` named `"Default Brand"` exists at all times so any user lacking an explicit assignment can be assigned to it.

- The `seed_brands` command MUST create the default brand if it does not already exist (idempotent).
- The default brand MUST be assigned to any user (including the superuser) that has no `User.brand` at command-run time.
- For users created via the admin, `UserAdmin.save_model` MUST assign the Default Brand when the user has no `Membership` (i.e., `getattr(obj, "brand", None) is None` on create). **Signal-driven auto-creation remains forbidden** — this is an explicit, gated assignment at the admin boundary only. The property setter writes a `Membership` row via `update_or_create`.

#### Scenario: Back-fill users without a brand
- **WHEN** `./manage.py seed_brands` runs and a `User` row has no `Membership`
- **THEN** a `Brand` named `"Default Brand"` MUST be created (if absent) via `Brand.get_or_create_default()`
- **AND** the user's `User.brand` MUST be set to that default brand (a `Membership(user=..., brand=...)` row is created by the property setter)

#### Scenario: Default brand persists
- **WHEN** the system is running after migration
- **THEN** the `"Default Brand"` row MUST continue to exist and be usable as the assignment target for users

### Requirement: New users do not auto-create a brand
The system SHALL NOT auto-create a `Brand` for newly created users via a `post_save` signal. Brand creation and user-to-brand assignment are superuser-driven actions performed in the admin.

- The previous `post_save` signal `create_profile_for_new_user` MUST be removed.
- New users created through the admin MUST be assigned the Default Brand by `UserAdmin.save_model` when no brand is provided. This explicit, gated assignment is **not** a signal and is **not** a side-effect of `User.save()`; it lives at the admin boundary only.
- New users created **outside** the admin (programmatic `User.objects.create_user`) MUST NOT auto-create a brand or `Membership`; the caller is explicitly responsible for setting `User.brand` (which writes a `Membership` row). Because the link lives on the separate `Membership` model (not as a NOT NULL column on `auth_user`), saving a `User` without a brand does NOT raise `IntegrityError` — the user row is saved successfully, `user.brand` evaluates to `None`, and the only enforcement is at the application boundary (`UserAdmin.save_model` for admin-created users, `seed_brands` for back-filling pre-existing rows). This is a documented consequence of the Membership architecture (see design.md Decision 2).

#### Scenario: Creating a user without brand assignment via code path
- **WHEN** a `User` is created programmatically (e.g., via `User.objects.create_user`) without setting a brand
- **THEN** no `Brand` row MUST be created for that user as a side effect
- **AND** the `User` row is saved successfully (no `IntegrityError`)
- **AND** `user.brand` MUST evaluate to `None` (no `Membership` row exists)
- **AND** the caller is responsible for setting `user.brand` to a `Brand` (which writes a `Membership` row) leaving the user with no brand link

#### Scenario: Admin-created user without explicit brand
- **WHEN** a superuser creates a `User` through the Django admin without selecting a brand
- **THEN** `UserAdmin.save_model` MUST assign the Default Brand (`Brand.get_or_create_default()`) before save
- **AND** no `post_save` signal handler MUST run

### Requirement: Top-left site icon reflects the user's brand logo
The `UNFOLD["SITE_ICON"]` callback (`utils.callbacks.site_icon`) SHALL source the admin header logo from `request.user.brand.logo.url`, falling back to the configured `static("favicon.png")` when the brand has no logo or the user is unauthenticated.

#### Scenario: User with a branded logo
- **WHEN** an authenticated user with a `Brand` that has a `logo` loads the admin
- **THEN** the top-left site icon MUST be served from the brand's logo URL

#### Scenario: User without a logo on their brand
- **WHEN** an authenticated user with a `Brand` whose `logo` is empty loads the admin
- **THEN** the top-left site icon MUST fall back to `static("favicon.png")`

#### Scenario: Unauthenticated request
- **WHEN** an unauthenticated request reaches the site icon callback
- **THEN** the system MUST return `static("favicon.png")`

### Requirement: Primary color palette reflects the user's brand
The `utils.callbacks.primary_palette_css` callback SHALL generate `:root { --color-primary-* }` CSS variables from `request.user.brand.primary_color` and MUST be referenced by `project/templates/admin/base.html` via the existing `user_palette_css` template context variable.

- When the user has no brand or the primary color is empty/missing, the callback MUST return an empty string and no inline palette MUST be rendered.

#### Scenario: Authenticated user with brand primary color
- **WHEN** an authenticated user with a `Brand` whose `primary_color` is set loads the admin
- **THEN** an inline `<style id="user-palette">` MUST be rendered containing a full `--color-primary-50..950` palette derived from the brand color
- **AND** achromatic colors (grayscale inputs) MUST use the achromatic branch (`oklch(L 0 0)`)

#### Scenario: User without a brand (post-deploy edge)
- **WHEN** an authenticated user has no `brand` association (transient state)
- **THEN** the callback MUST return an empty string
- **AND** the admin MUST fall back to the default Unfold `COLORS["primary"]` palette from `settings.UNFOLD`

### Requirement: Bottom-left user menu shows the default person icon
The bottom-left user menu (`unfold/helpers/navigation_user.html`) SHALL always render the default `person` material-symbols icon. The system MUST NOT render a personal avatar image in that location.

- The implementation MUST override `unfold/helpers/navigation_user.html` via the project's template directory so that Django resolves it before Unfold's packaged copy.
- The override MUST NOT reference `request.user.avatar_url`, `User.avatar_url`, or any per-user profile picture.

#### Scenario: Authenticated user loads the admin
- **WHEN** any authenticated user loads the admin
- **THEN** the bottom-left user menu MUST display the `person` material-symbols-outlined icon
- **AND** no `<img>` or background-image pointing at a personal avatar MUST be rendered in that location

#### Scenario: Template override takes precedence
- **WHEN** Django renders the bottom-left navigation user block
- **THEN** the template loader MUST resolve `<project template dir>/unfold/helpers/navigation_user.html` before `unfold`'s packaged copy

### Requirement: Admin manages brands and assigns users to brands
The Django admin SHALL provide a `BrandAdmin` (registered for `Brand`) and SHALL expose `Brand` assignment for `User` via `UserAdmin`, restricted to **superusers only**.

- `BrandAdmin` list display SHALL include: brand logo thumbnail, `primary_color`, and user count.
- `UserAdmin` SHALL include a `brand` field in its form, gated so that only superusers can set or change it; non-superusers MUST see the field read-only (or have it absent).
- The previous `ProfileAdmin` and `ProfileInline` registrations MUST be removed.
- The previous `UserAdmin.avatar_thumb` column MUST be removed; a `brand` column SHOULD replace it.
- `User.avatar_url` property MUST be removed from `core/models.py`; consumers MUST be repointed to `user.brand.logo.url` via callbacks.

#### Scenario: Superuser manages a brand
- **WHEN** a superuser opens the `Brand` admin changelist
- **THEN** the superuser MUST be able to add, change, and delete (subject to PROTECT on delete) brands

#### Scenario: Non-superuser cannot reassign brand
- **WHEN** a non-superuser staff user opens the `User` change form
- **THEN** the `brand` field MUST be read-only or hidden
- **AND** submitting the form MUST NOT change the user's brand

#### Scenario: No more per-user avatar inline
- **WHEN** the `User` change form is rendered
- **THEN** there MUST be no `ProfileInline` rendering an avatar field
- **AND** the form MUST NOT display the `profile.avatar` widget from the previous one-to-one relationship

### Requirement: File relocation is idempotent and reversible (via `seed_brands` command)
The `seed_brands` management command SHALL relocate image files from `media/avatars/user_<id>/` to `media/brands/brand_<pk>/` on forward, and SHALL move them back on `--reverse`. The schema migrations are produced only by `makemigrations core` and MUST NOT contain hand-edited `RunPython` for file moves.

- File moves MUST tolerate missing source files (e.g., already deleted) as no-ops.
- File moves MUST target paths rooted at `settings.MEDIA_ROOT` so behavior is identical across environments.
- The command MUST be idempotent: running forward twice MUST NOT break or duplicate files.
- A `Brand.get_or_create_default()` classmethod MUST exist on the model and be reusable by both the command and the admin.

#### Scenario: Forward command moves files
- **WHEN** `./manage.py seed_brands` runs and a `Brand.logo` path exists on disk at `media/avatars/user_<id>/<filename>`
- **THEN** the file MUST be moved to `media/brands/brand_<pk>/<original_filename>`
- **AND** the `Brand.logo` field MUST point at the new path

#### Scenario: Reverse command restores files
- **WHEN** `./manage.py seed_brands --reverse` runs
- **THEN** files MUST be moved back to `media/avatars/user_<id>/<original_filename>` whenever the reverse mapping is known (i.e., a preserved `legacy_user_id` or other snapshot is available)
- **AND** missing source files MUST be silently skipped without raising

#### Scenario: Command is idempotent
- **WHEN** `./manage.py seed_brands` is run a second time on a database already back-filled
- **THEN** no duplicate `Brand` rows MUST be created
- **AND** no files MUST be re-moved (a no-op when the destination already exists or the source is already at the destination)

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

