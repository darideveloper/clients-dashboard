## Why

The project uses `django-unfold` for a modern admin UI, but the user menu in the sidebar (driven by `unfold/helpers/navigation_user.html`) renders a generic `person` icon for every user. There is no mechanism to associate a profile image with a user, so staff cannot identify people at a glance in the admin. The operator (admin) needs to set and update avatars on behalf of every user — there is no self-service surface in this change.

On top of the avatar, the Unfold admin renders every primary-colored element (buttons, links, badges, focus rings, active states) from a single static palette in `UNFOLD["COLORS"]["primary"]`. Every operator who logs in sees the same purple. Giving each user a per-row `primary_color` on the same `Profile` makes the admin feel like their own without touching the project brand for visitors or the login page. The operator picks the color; the system derives the 11 OKLCH shades at render time.

## What Changes

- Add a `core.Profile` model with a one-to-one relation to `django.contrib.auth.models.User` and an `avatar` `ImageField` stored under `avatars/user_<id>/`. The field has a 2 MB upload cap enforced at the model layer.
- Expose the avatar URL to templates via a `User.avatar_url` property (returns `""` when no avatar is set) so the unfold sidebar and any future template can render it with a single attribute lookup.
- Auto-create a `Profile` row for each user via a `post_save` signal so the relation is always present.
- Surface the avatar in the Django admin: a stacked `ProfileInline` on the user change form, a `Profile` standalone admin, and a 32×32 rounded thumbnail column in the user changelist for quick scanning. Avatars are edited **only by staff via the Django admin**; there is no public-facing form or endpoint.
- Use the viewer's avatar as the Unfold `SITE_ICON` in the **sidebar header** (small ~38px, alongside the "clients Admin" / "clients Dashboard" brand text), falling back to the static `favicon.png` for anonymous users (login page). The project's previous static `SITE_LOGO` is removed because Unfold's `navigation_header.html` renders `SITE_LOGO` if set and falls back to `SITE_ICON` only when `SITE_LOGO` is absent — keeping both would shadow the avatar. Resolved by a dedicated `utils.callbacks.site_icon` callback invoked from the `SITE_ICON` lambda in `project/settings.py`.
- Add a per-user primary color picker on the same `Profile` model (`primary_color` CharField, default `#C92FFF`, validated hex + WCAG AA contrast against white). On every admin request, a `utils.context_processors.user_palette(request)` context processor puts a per-user CSS string into the template context, and a `{% block base %}` override in `project/templates/admin/base.html` injects a `<style id="user-palette">` block (with the 11 `--color-primary-{50..950}` overrides) into the response after Unfold's static `unfold-theme-colors` block, so it wins the cascade. Achromatic colors (R≈G≈B, e.g. `#000000`) use `oklch(L 0 0)` (grayscale) instead of `oklch(from <color> L C h)` to avoid the browser defaulting undefined hue to red. Anonymous users and the login page keep the static `UNFOLD["COLORS"]["primary"]` from settings. Color is edited **only by staff via the Django admin**; there is no self-service form.
- Verify storage works against the existing `PublicMediaStorage` (S3, public-read) and the local `FileSystemStorage` fallback in dev.

## Capabilities

### New Capabilities

- `user-profile`: User profile model, one-to-one with `auth.User`, exposing an `avatar` image that staff manage through the Django admin. Avatar edits happen only via `/admin/auth/user/<id>/change/` (via the `ProfileInline`) or `/admin/core/profile/`. There is no self-service form, DRF endpoint, or template-side upload widget.
- `per-user-primary-color`: Each user's `Profile` carries a `primary_color` (hex string, default `#C92FFF`) that staff set via the Django admin. The 11-shade Unfold `primary` palette is derived at render time via the browser-native `oklch(from <color> L C h)` CSS function (with an `oklch(L 0 0)` grayscale fallback for achromatic sources) and injected as a per-request `<style id="user-palette">` block through a context processor + a `{% block base %}` override in `project/templates/admin/base.html`. Anonymous requests fall back to the static `UNFOLD["COLORS"]["primary"]` from settings.

### Modified Capabilities

_None._ The `unfold-admin-theme` and `s3-media-storage` capabilities are not changing at the requirement level — we only add new fields and admin wiring that consume the existing storage and theming. The `auth.User` model itself is untouched (still the default `django.contrib.auth.models.User`), so no spec under `project-bootstrap` changes either.

## Impact

- **New app code**: `core/models.py`, `core/signals.py`, `core/admin.py` (extended with `ProfileInline`, `avatar_thumb`, standalone `Profile` registration), `core/apps.py` (wire signal), `core/validators.py` (size + hex + contrast validators), `core/migrations/0001_initial.py`, `core/migrations/0002_backfill_profiles.py`.
- **New callback**: `utils.callbacks.site_icon(request)` appended to `utils/callbacks.py`.
- **New callback**: `utils.callbacks.primary_palette_css(request)` appended to `utils/callbacks.py` (with achromatic detection).
- **New context processor**: `utils.context_processors.user_palette(request)` calls `primary_palette_css` and exposes the CSS as a template variable; registered under `TEMPLATES[0]["OPTIONS"]["context_processors"]` in `project/settings.py`.
- **New template override**: `project/templates/admin/base.html` (Django's admin base template convention; the file was previously `base_site.html`, renamed to be picked up by Django) extends `admin/base.html` and adds a `{% block base %}{% endblock %}` override that renders `<style id="user-palette">{{ user_palette_css|safe }}</style>` after `{{ block.super }}` so the per-user palette wins the cascade against Unfold's static `unfold-theme-colors` block in the body.
- **Touched settings**: `project/settings.py` — `SITE_ICON` lambda body delegates to `site_icon`; `SITE_LOGO` is removed entirely (Unfold's `navigation_header.html` renders `SITE_LOGO` over `SITE_ICON` when both are set, so keeping `SITE_LOGO` would shadow the avatar); the `TEMPLATES` context_processors list adds `utils.context_processors.user_palette`. No new top-level settings keys.
- **Storage**: relies on the existing `PublicMediaStorage` (S3) and `MEDIA_URL` / `MEDIA_ROOT` plumbing — no settings changes required.
- **Dependencies**: `Pillow>=11.1.0` already in `requirements.txt`. No new packages.
- **Data migration**: existing users need a `Profile` row. A `RunPython` data migration in `core/migrations/0002_backfill_profiles.py` (with `Profile.objects.get_or_create(user=u)`) will backfill them.
- **No new URL patterns, no new views, no new forms** — the user-facing surface is the Django admin, plus a single context processor and one template override (`base.html`).
- **Out of scope**: image resizing/thumbnails beyond the 32×32 admin preview, gravatar/external avatar fallback, DRF endpoints, group avatars, self-service `/profile/` page, allauth integration, password/email self-service, light/dark per-user `base` or `font` palette overrides, server-side OKLCH pre-compute (we use browser-native `oklch(from)` with an achromatic-source grayscale fallback at render time).
