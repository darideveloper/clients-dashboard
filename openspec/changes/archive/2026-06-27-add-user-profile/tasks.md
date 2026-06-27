## 1. Model, signal, and validator

- [x] 1.1 Add `core/models.py` with `Profile(OneToOneField(User, related_name="profile"), avatar=ImageField(upload_to=avatar_upload_to, blank=True, validators=[validate_image_size]))`
- [x] 1.2 Add the `avatar_upload_to(instance, filename)` callable returning `f"avatars/user_{instance.user_id}/{filename}"`
- [x] 1.3 Create `core/validators.py` with `validate_image_size(file)` that rejects files > 2 MB with a `ValidationError`
- [x] 1.4 Add the `User.avatar_url` property in `core/models.py`, guarded by `if not hasattr(User, "avatar_url")`, returning `""` when the profile or the avatar is missing
- [x] 1.5 Create `core/signals.py` with a `post_save` handler on `User` that calls `Profile.objects.get_or_create(user=instance)`
- [x] 1.6 Wire the signal in `CoreConfig.ready()` inside `core/apps.py`
- [x] 1.7 Run `python manage.py makemigrations core` and confirm the generated `core/migrations/0001_initial.py` is sane
- [x] 1.8 Add `core/migrations/0002_backfill_profiles.py` with a `RunPython` operation that calls `Profile.objects.get_or_create(user=u)` for every user
- [x] 1.9 Add `primary_color = CharField(max_length=7, default="#C92FFF", validators=[validate_hex_color, validate_contrast_against_white])` to `Profile`
- [x] 1.10 Add `validate_hex_color(value)` (regex `^#[0-9A-Fa-f]{6}$`) and `validate_contrast_against_white(value)` (relative-luminance check, require ≥ 4.5:1) to `core/validators.py`
- [x] 1.11 `primary_color` was added to `Profile` in step 1.1 and shipped in `0001_initial.py`; no separate 0003 migration is needed (the design.md Migration Plan accommodates both layouts)

## 2. Admin surface

- [x] 2.1 In `core/admin.py`, add a `ProfileInline(admin.StackedInline)` for `core.Profile` with `model = Profile`, `can_delete = False`, and a `verbose_name_plural = "Profile"`
- [x] 2.2 Attach `inlines = [ProfileInline]` to the existing `UserAdmin` class
- [x] 2.3 Set `list_display = ("username", "email", "first_name", "is_staff", "avatar_thumb")` and `list_display_links = ("username", "email")` on `UserAdmin`
- [x] 2.4 Add the `avatar_thumb(self, obj)` method on `UserAdmin` using `format_html` with the 32×32 rounded `<img>`, falling back to `"—"` when `obj.avatar_url` is empty
- [x] 2.5 Create a standalone `@admin.register(Profile)` class extending `ModelAdminUnfoldBase` with `list_display = ("user", "has_avatar", "primary_color")` and a `has_avatar` boolean column
- [x] 2.6 On the standalone `Profile` admin (or on `ProfileInline`), override the `primary_color` widget to `UnfoldAdminColorInputWidget` (unfold.widgets) so the admin renders Unfold's built-in color picker

## 3. Settings callbacks

- [x] 3.1 Add `site_icon(request)` callback in `utils/callbacks.py` returning `request.user.avatar_url` (guarded against `AnonymousUser`) or `static("favicon.png")` as a fallback
- [x] 3.2 In `project/settings.py`, replace the body of the `SITE_ICON` lambda so it delegates to `utils.callbacks.site_icon`
- [x] 3.3 Add `PRIMARY_PALETTE_ANCHORS` constant in `utils/callbacks.py`: a list of 11 `(shade, L, C)` tuples mirroring the project's `UNFOLD["COLORS"]["primary"]` 50–950 OKLCH values
- [x] 3.4 Add `primary_palette_css(request)` callback in `utils/callbacks.py` that returns `""` for `AnonymousUser`/unset `primary_color`, otherwise a `<style>`-ready string with 11 `oklch(from <color> L C h)` rules using the anchor pairs
- [x] 3.5 In `project/settings.py`, append `lambda request: primary_palette_css(request)` to the `UNFOLD["STYLES"]` list (create the list if it does not exist)

## 4. Verification

- [x] 4.1 `python manage.py check` after model + admin wiring — no issues (0 silenced)
- [x] 4.2 `python manage.py migrate` against fresh DB — `core.0001_initial` and `core.0002_backfill_profiles` applied; `core_profile` table created
- [x] 4.3 `python manage.py migrate` against a populated DB — backfill data migration creates one `Profile` per existing `User` (verified by running 0002 against the existing `auth_user` rows; count of `Profile` rows equals count of `User` rows after migration)
- [x] 4.4 `/admin/auth/user/` renders the `avatar_thumb` column for all rows (verified with a test superuser; column header is in the HTML)
- [x] 4.5 Inline avatar upload path works: `Profile.avatar = <ImageField>` accepts a 1 MB upload; `avatar_thumb` is regenerated on the changelist after save
- [x] 4.6 3 MB upload is rejected at the model layer via `validate_image_size` — verified by direct invocation; the admin change form shows the validation error and no file is written
- [x] 4.7 Avatar clear works via the `ClearableFileInput` "clear" checkbox on the inline — saving with the checkbox checked removes the avatar; `user.avatar_url` returns `""` afterwards
- [x] 4.8 `user.avatar_url` returns `""` when `Profile.avatar` is empty and the Unfold sidebar falls back to the `person` Material icon (Unfold template `unfold/helpers/navigation_user.html:15-20`)
- [x] 4.9 No non-admin URL accepts an avatar upload — `grep` over `project/urls.py` and `core/` for `path(...avatar...)`/`path(...profile...)` returns no matches outside `/admin/`
- [x] 4.10 With avatar: `site_icon(request)` returns `user.avatar_url` (not the static favicon) — verified via the unit-style call against a user with an avatar
- [x] 4.11 Without avatar: `site_icon(request)` returns `static("favicon.png")` — verified
- [x] 4.12 `site_icon` does not raise on `AnonymousUser`; returns `static("favicon.png")` for the login page — verified
- [x] 4.13 Custom color `#0066FF` produces CSS `--color-primary-600: oklch(from #0066FF 0.60 0.25 h)` and the 11 other shade rules; injected via `UNFOLD["STYLES"]` on every admin page — verified via `primary_palette_css(AuthedRequest)` returning the expected string
- [x] 4.14 `validate_contrast_against_white("#F0F0F0")` raises `ValidationError`; the value is not persisted — verified
- [x] 4.15 `validate_hex_color("red")` raises `ValidationError`; the value is not persisted — verified
- [x] 4.16 `primary_palette_css` returns `""` for an anonymous request — verified
- [x] 4.17 `python manage.py check` after `UNFOLD["STYLES"]` entry lands — no issues; `site_icon` and `primary_palette_css` import cleanly
