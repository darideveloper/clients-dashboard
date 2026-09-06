## MODIFIED Requirements

### Requirement: Brand entity
The system SHALL provide a `Brand` model (Django `app_label=core`) that represents a company/tenant and stores the company logo and primary brand color used to customize the admin chrome.

- Fields:
  - `slug`: `SlugField(max_length=100, unique=True, blank=True)` — URL-safe identifier auto-generated from `name`, used in login page `?brand=<slug>` query parameter.
  - `is_default`: `BooleanField(default=False)` — designates the system-wide fallback brand. `save()` enforces that only one brand holds `is_default=True` at a time.
  - `logo`: `ImageField`, optional (`blank=True`), validated for image size (existing `validate_image_size`).
  - `primary_color`: `CharField(max_length=7)`, default `"#C92FFF"`, validated by `validate_hex_color` and `validate_contrast_against_white`.
- The model MUST replace the previous `Profile` model (renamed, not recreated). The schema migration is produced only by `makemigrations core` (no hand-edits). The Default Brand row is provided by the base fixture `core/fixtures/core/Brand.json` loaded via `base_loaddata` on every deploy and test run; the legacy `seed_brands` command no longer exists (its file-relocation and Membership backfill role is now `backfill_brand_files`).

#### Scenario: Existing profile rows become brands
- **WHEN** `base_loaddata` is run against a database containing one or more `Brand` rows (formerly `Profile` rows), or `backfill_brand_files` is run after the fixture
- **THEN** each such row MUST be associated with the user it previously referenced (via the OneToOne column or a preserved `legacy_user_id` snapshot)
- **AND** the image file MUST be relocated from `media/avatars/user_<id>/` to `media/brands/brand_<pk>/`

#### Scenario: Logo is optional
- **WHEN** a `Brand` is saved without a logo
- **THEN** the system MUST accept the save and `brand.logo` MUST evaluate falsy
- **AND** admin chrome consumers (`site_icon`, primary palette) MUST fall back to defaults as defined in their own requirements

### Requirement: System default brand always exists
The system SHALL ensure that a `Brand` named `"Default Brand"` exists at all times so any user lacking an explicit assignment can be assigned to it.

- The base fixture `core/fixtures/core/Brand.json` loaded by `base_loaddata` MUST provide the default brand (idempotent; re-runs update the row in place).
- The `backfill_brand_files` command MUST assign the default brand to any user (including the superuser) that has no `User.brand` at command-run time, and MUST fail loudly if the fixture row is missing (it MUST NOT call `Brand.get_or_create_default()` to create the row).
- For users created via the admin, `UserAdmin.save_model` MUST assign the Default Brand when the user has no `Membership` (i.e., `getattr(obj, "brand", None) is None` on create). **Signal-driven auto-creation remains forbidden** — this is an explicit, gated assignment at the admin boundary only. The property setter writes a `Membership` row via `update_or_create`.

#### Scenario: Back-fill users without a brand
- **WHEN** `python manage.py base_loaddata` has been run and then `python manage.py backfill_brand_files` runs and a `User` row has no `Membership`
- **THEN** a `Brand` named `"Default Brand"` MUST exist from the fixture
- **AND** the user's `User.brand` MUST be set to that default brand (a `Membership(user=..., brand=...)` row is created by the property setter)

#### Scenario: Default brand persists
- **WHEN** the system is running after migration
- **THEN** the `"Default Brand"` row MUST continue to exist and be usable as the assignment target for users

### Requirement: File relocation is idempotent and reversible (via `backfill_brand_files` command)
The `backfill_brand_files` management command SHALL relocate image files from `media/avatars/user_<id>/` to `media/brands/brand_<pk>/` on forward, and SHALL move them back on `--reverse`. The schema migrations are produced only by `makemigrations core` and MUST NOT contain hand-edited `RunPython` for file moves.

- File moves MUST tolerate missing source files (e.g., already deleted) as no-ops.
- File moves MUST target paths rooted at `settings.MEDIA_ROOT` so behavior is identical across environments.
- The command MUST be idempotent: running forward twice MUST NOT break or duplicate files.
- If the Default Brand fixture row is missing, the command MUST error and MUST NOT create it via `Brand.get_or_create_default()`.
- A `Brand.get_or_create_default()` classmethod MUST continue to exist on the model and be reusable by admin and callbacks, but it is no longer the provisioning mechanism for the Default Brand row (the fixture is).

#### Scenario: Forward command moves files
- **WHEN** `python manage.py backfill_brand_files` runs and a `Brand.logo` path exists on disk at `media/avatars/user_<id>/<filename>`
- **THEN** the file MUST be moved to `media/brands/brand_<pk>/<original_filename>`
- **AND** the `Brand.logo` field MUST point at the new path

#### Scenario: Reverse command restores files
- **WHEN** `python manage.py backfill_brand_files --reverse` runs
- **THEN** files MUST be moved back to `media/avatars/user_<id>/<original_filename>` whenever the reverse mapping is known (i.e., a preserved `legacy_user_id` or other snapshot is available)
- **AND** missing source files MUST be silently skipped without raising

#### Scenario: Command is idempotent
- **WHEN** `python manage.py backfill_brand_files` is run a second time on a database already back-filled
- **THEN** no duplicate `Brand` rows MUST be created
- **AND** no files MUST be re-moved (a no-op when the destination already exists or the source is already at the destination)
