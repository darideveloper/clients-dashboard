# fixture-system Specification

## Purpose
TBD - created by archiving change add-fixture-system. Update Purpose after archive.
## Requirements
### Requirement: Auto-discovering fixture loaders in core

The system SHALL provide two management commands in `core/management/commands/` that auto-discover and load fixtures from every installed app without a maintained list: `base_loaddata` loads all `<app>/fixtures/<app>/*.json` (always-needed reference data) and `seed_loaddata` loads all `<app>/fixtures/<app>/seed/*.json` plus committed sample media under `seed/images/` to `default_storage`. Both SHALL iterate `apps.get_app_configs()`, load `*.json` in sorted order per app, call `call_command("loaddata", f"{label}/{name}")`, and continue on per-fixture failure with a printed error.

#### Scenario: Load base fixtures from any app without loader edits

- **WHEN** a new app adds `<app>/fixtures/<app>/Foo.json` and `python manage.py base_loaddata` is run
- **THEN** the fixture rows are inserted/updated via `loaddata` without any change to loader code

#### Scenario: Per-fixture failure does not block other fixtures

- **WHEN** one fixture fails to load (e.g., bad JSON or constraint error)
- **THEN** the command prints the error and continues loading remaining fixtures

#### Scenario: Sorted load within an app respects numeric prefixes

- **WHEN** an app's fixture dir contains `00_Foo.json` and `01_Bar.json` where `Bar` FKs to `Foo`
- **THEN** `Foo` loads before `Bar` due to sorted order and the FK resolves

### Requirement: Default Brand base fixture

The system SHALL provide a base fixture at `core/fixtures/core/Brand.json` that creates the system Default Brand row (`pk=1`, `name="Default Brand"`, `slug="default-brand"`, `is_default=true`, `primary_color="#C92FFF"`, no logo) via `base_loaddata`. The `slug` SHALL be explicit because `loaddata` bypasses `Model.save()`.

#### Scenario: base_loaddata creates the Default Brand row

- **WHEN** `python manage.py base_loaddata` is run on a fresh database (after `migrate`)
- **THEN** a `Brand` row with `pk=1`, `name="Default Brand"`, `slug="default-brand"`, `is_default=true`, `primary_color="#C92FFF"` exists

#### Scenario: Re-running base_loaddata is idempotent for Brand

- **WHEN** `python manage.py base_loaddata` is run a second time
- **THEN** the `Brand` row is updated in place (no duplicate) and still satisfies the fields above

### Requirement: Brand backfill and file relocation command

The system SHALL provide `core/management/commands/backfill_brand_files.py` that, on forward, assigns the Default Brand (from the base fixture) to any `User` lacking a `Membership` and relocates logo files from `avatars/user_<id>/` to `brands/brand_<pk>/`; on `--reverse`, it best-effort moves files back. The command SHALL fail loudly if the Default Brand fixture row is missing (enforcing `base_loaddata` first), SHALL tolerate missing source files as no-ops, SHALL be idempotent, and SHALL not create the Default Brand row itself.

#### Scenario: Backfill users without a brand

- **WHEN** `python manage.py backfill_brand_files` is run and a `User` has no `Membership`
- **THEN** a `Membership(user, brand=Default Brand)` row is created

#### Scenario: Forward file move

- **WHEN** a `Brand.logo` path exists at `avatars/user_<id>/<file>` on disk under `MEDIA_ROOT`
- **THEN** the file is moved to `brands/brand_<pk>/<file>` and `Brand.logo` points at the new path

#### Scenario: Missing fixture row fails loudly

- **WHEN** `backfill_brand_files` is run without `base_loaddata` having loaded the Default Brand
- **THEN** the command errors and does not create the Default Brand via `get_or_create_default()`

#### Scenario: Reverse is best-effort

- **WHEN** `python manage.py backfill_brand_files --reverse` is run
- **THEN** files are moved back to `avatars/user_<id>/` where the membership mapping is known, and missing sources are skipped
