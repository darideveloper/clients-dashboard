## ADDED Requirements

### Requirement: Profile model linked to User

The system SHALL provide a `core.Profile` model with a one-to-one relation to `django.contrib.auth.models.User` (related name `profile`) and an `avatar` `ImageField` that stores uploads under `avatars/user_<user.id>/` using the active `default` storage backend. The `avatar` field SHALL be optional (`blank=True`).

#### Scenario: Profile row exists for every user
- **WHEN** a `User` instance is created (or already exists before this capability is deployed)
- **THEN** a corresponding `Profile` row exists and is reachable as `user.profile`

#### Scenario: User can have at most one Profile
- **WHEN** code attempts to create a second `Profile` for the same user
- **THEN** the database rejects it with an `IntegrityError`

#### Scenario: Avatar file is stored on the configured backend
- **WHEN** a staff user uploads a valid image through the `Profile` model in the admin
- **THEN** the file is written through the project's `default` storage backend (S3 `PublicMediaStorage` in production, local `FileSystemStorage` in dev)

### Requirement: Avatar upload size cap

The `core.Profile.avatar` field SHALL reject any uploaded file whose size exceeds 2 MB (2 × 1024 × 1024 bytes). The cap MUST be implemented as a reusable validator in `core.validators` and attached to the `ImageField` so it applies to every save path (admin, shell, management commands, future DRF endpoints).

#### Scenario: Image under 2 MB is accepted
- **WHEN** a staff user uploads a 1 MB image through the admin
- **THEN** the save succeeds and the avatar is stored

#### Scenario: Image over 2 MB is rejected
- **WHEN** a staff user uploads a 3 MB image through the admin
- **THEN** the change form is invalid, the field shows a validation error, and no file is written to storage

### Requirement: User.avatar_url template property

The system SHALL expose `user.avatar_url` as a string property on `django.contrib.auth.models.User` instances. The property MUST return the absolute URL of `user.profile.avatar` when an avatar is set, and MUST return an empty string (`""`) when the profile has no avatar or the profile row is missing. The property MUST NOT raise if the profile row is absent.

#### Scenario: Avatar URL is present
- **WHEN** `user.profile.avatar` is set to a non-empty file
- **THEN** `user.avatar_url` returns the URL of that file

#### Scenario: Avatar URL is empty when unset
- **WHEN** `user.profile.avatar` is empty
- **THEN** `user.avatar_url` returns `""`

#### Scenario: Missing profile does not raise
- **WHEN** `user.profile` does not exist (e.g. before backfill completes)
- **THEN** accessing `user.avatar_url` returns `""` and does not raise

### Requirement: Profile auto-creation signal

The system SHALL register a `post_save` signal handler for `django.contrib.auth.models.User` that creates a `Profile` row on first save if one does not already exist. The handler MUST be idempotent and MUST be wired in `core.apps.CoreConfig.ready()`.

#### Scenario: New user gets a profile
- **WHEN** a new `User` is saved
- **THEN** a `Profile` row with `user=<that user>` is created

#### Scenario: Re-saving a user does not duplicate the profile
- **WHEN** an existing `User` with a `Profile` is saved again
- **THEN** no new `Profile` row is created

### Requirement: Admin can edit any user's avatar

The system SHALL register `core.Profile` in the Django admin using `project.admin_base.ModelAdminUnfoldBase` and SHALL attach a stacked inline (`ProfileInline`) to the existing `core.UserAdmin` so that the avatar field appears on the user change form. Avatars are editable ONLY by staff with the appropriate Django admin permissions; the system SHALL NOT expose any public URL, view, or form for editing avatars.

#### Scenario: Staff opens the user change form
- **WHEN** a staff user visits `/admin/auth/user/<id>/change/`
- **THEN** a `Profile` section is rendered inline with the `avatar` field, a clearable file widget, a `primary_color` field with Unfold's color picker widget, and the existing user fields

#### Scenario: Color picker uses Unfold's built-in widget
- **WHEN** the `primary_color` field is rendered in the inline (or in the standalone Profile admin)
- **THEN** the widget is `unfold.widgets.UnfoldAdminColorInputWidget`

#### Scenario: Staff uploads an avatar for another user
- **WHEN** a staff user picks an image in the `Profile` inline and saves
- **THEN** the avatar is stored on the target user's `Profile` and the `User.avatar_url` for that user returns its URL

#### Scenario: Staff clears the avatar
- **WHEN** a staff user submits the user change form with the "clear" checkbox for the avatar checked
- **THEN** the avatar is removed and the target user's `User.avatar_url` returns `""`

#### Scenario: Standalone profile admin lists all profiles
- **WHEN** a staff user visits `/admin/core/profile/`
- **THEN** all `Profile` rows are listed with their associated user and the `primary_color` column shows each profile's hex value

#### Scenario: No public upload URL exists
- **WHEN** the URL configuration is inspected
- **THEN** no URL pattern accepts an avatar upload outside the Django admin

### Requirement: Admin user changelist shows avatar thumbnail

The system SHALL add an `avatar_thumb` column to the `User` changelist (`/admin/auth/user/`) that renders a 32×32 rounded image when an avatar exists, and an em-dash (`—`) when it does not. The column MUST NOT be a link target (`list_display_links` must exclude it).

#### Scenario: User with avatar
- **WHEN** a user listed at `/admin/auth/user/` has an avatar
- **THEN** a 32×32 image is shown in the `avatar_thumb` column

#### Scenario: User without avatar
- **WHEN** a user listed at `/admin/auth/user/` has no avatar
- **THEN** an em-dash is shown in the `avatar_thumb` column

### Requirement: Existing users are backfilled

The system SHALL ship a data migration that creates a `Profile` row for every `User` that does not already have one, so that the `User.avatar_url` property is safe to call for every user immediately after deployment.

#### Scenario: Migration runs against a populated database
- **WHEN** `migrate` is executed on a database that already contains `auth_user` rows
- **THEN** the count of `Profile` rows equals the count of `User` rows after migration

### Requirement: Sidebar SITE_ICON reflects the viewer

The system SHALL render the Unfold `SITE_ICON` slot in the admin sidebar using the currently authenticated user's avatar URL when an avatar is present, and SHALL fall back to the static `favicon.png` for anonymous users (for example, the login page) and for authenticated users without an avatar. The resolution MUST happen in a dedicated `utils.callbacks.site_icon(request)` callback invoked from the `SITE_ICON` lambda in `project/settings.py`. The callback MUST NOT raise on `AnonymousUser` and MUST return a string URL.

#### Scenario: Logged-in user with avatar
- **WHEN** an authenticated user with an avatar triggers a request that renders the admin sidebar
- **THEN** the `SITE_ICON` image `src` equals `user.avatar_url`

#### Scenario: Logged-in user without avatar
- **WHEN** an authenticated user without an avatar triggers a request that renders the admin sidebar
- **THEN** the `SITE_ICON` image `src` equals the static URL for `favicon.png`

#### Scenario: Anonymous request
- **WHEN** an unauthenticated request (for example `GET /admin/login/`) is rendered
- **THEN** `utils.callbacks.site_icon` returns the static `favicon.png` URL and does not raise

#### Scenario: Settings delegate to the callback
- **WHEN** `project/settings.py` is inspected
- **THEN** `UNFOLD["SITE_ICON"]` resolves to a callable that delegates to `utils.callbacks.site_icon`
