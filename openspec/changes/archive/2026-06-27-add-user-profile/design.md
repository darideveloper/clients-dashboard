## Context

The project is a Django 5.2 + DRF backend with `django-unfold` for the admin theme. It already runs on S3 for media in production via `project.storage_backends.PublicMediaStorage` (public-read ACL, `file_overwrite=False`) and on the local filesystem in dev (`MEDIA_ROOT=media/`, `MEDIA_URL=/media/`). Pillow is in `requirements.txt`. The default `django.contrib.auth.models.User` is in use; there is no `AUTH_USER_MODEL` override and no custom user model.

User and Group admin registration recently moved from `project/admin.py` (now deleted) to `core/admin.py`, where it sits on top of `project.admin_base.ModelAdminUnfoldBase`. The Unfold sidebar template at `unfold/helpers/navigation_user.html` looks up `request.user.avatar_url` and falls back to a generic `person` icon if it is falsy — that is the only template hook we need to satisfy for the sidebar to render a real avatar.

The operator (admin) is the only person who sets or changes avatars. End users have no upload UI, no DRF endpoint, no self-service page. The entire avatar pipeline is contained in the Django admin plus one settings callback.

## Goals / Non-Goals

**Goals:**

- A `Profile` model that is guaranteed to exist for every `User` (signal + data migration).
- A `User.avatar_url` property that the Unfold sidebar template and any future template can consume without conditional logic or template-side error handling.
- Admin inline + standalone + changelist thumbnail for staff to upload, replace, or clear any user's avatar.
- A 2 MB upload cap enforced at the model layer so it applies to every save path (admin, shell, future scripts).
- A `SITE_ICON` callback that swaps the static favicon for the viewer's avatar when present.
- A per-user `primary_color` field on `Profile`, validated for hex format and WCAG AA contrast (4.5:1) against white.
- A per-request CSS injection that derives the 11-shade Unfold `primary` palette from the viewer's `primary_color` via browser-native `oklch(from <color> L C h)` (with `oklch(L 0 0)` grayscale fallback for achromatic sources), with graceful fallback to the static `UNFOLD["COLORS"]["primary"]` for anonymous requests and pre-2024 browsers. The injection uses a context processor + `{% block base %}` template override (not `UNFOLD["STYLES"]`, which only accepts URL strings).

**Non-Goals:**

- Custom user model or `AUTH_USER_MODEL` swap.
- Image resizing, thumbnailing beyond the 32×32 admin preview, or EXIF stripping.
- Gravatar or external avatar fallback.
- DRF endpoints or any JSON API for avatars.
- Group avatars.
- Any change to `auth.User` fields, permissions, or admin forms.
- Self-service `/profile/` page, public upload form, or any per-user upload UI.
- Multi-file uploads, drag-and-drop, or client-side image processing.
- Per-user `base` or `font` palette overrides (only `primary` is per-user in this change).
- Per-user `SITE_LOGO`, `BORDER_RADIUS`, or other static theming settings (only `SITE_ICON` and the `primary` palette swap).
- Server-side palette computation (Python pre-compute of OKLCH shades); we use browser-native `oklch(from)` instead.

## Decisions

### D1. Profile model is a sibling, not a User subclass

We add `core.Profile` with a `OneToOneField(User, related_name="profile")` rather than swapping to a custom user model.

- **Why**: zero impact on `auth_user`, `rest_framework.authtoken`, the existing Unfold `UserAdmin` inheritance chain, and existing migrations. Reversible by dropping one table.
- **Alternative considered**: `AbstractUser` subclass with an `avatar` field. Rejected because it requires an `AUTH_USER_MODEL` swap before the first migration, breaks `rest_framework.authtoken`'s swappable dependency, and changes the `User` PK contract.
- **Alternative considered**: monkey-patch `User` with a property only. Rejected because the property still needs a place to store the file, and a model gives us admin, signals, and migrations for free.

### D2. `User.avatar_url` is a property attached at module import time, not a method on `Profile`

We define `avatar_url` on `User` itself (in `core/models.py`) and have it lazily fetch `self.profile`.

- **Why**: the Unfold template (`navigation_user.html`) already calls `request.user.avatar_url`. Templates that need a single attribute lookup stay simple, and any template that doesn't know about `Profile` still works.
- **Why not a method on `Profile`**: forces every caller to know about the related model.
- **Risk**: monkey-patching `User` couples our app to auth. Mitigation — gate the patch behind a `hasattr` check so it is idempotent across reloads, and document the dependency.

### D3. `post_save` signal in `CoreConfig.ready()`, plus a `RunPython` data migration

Signal covers forward saves; migration backfills existing users on first deploy.

- **Why both**: signal alone leaves historical users without a `Profile` until they next save, which would break `user.avatar_url` lookups in the interim. The `RunPython` migration is idempotent (`get_or_create`) and is the only way to make `User.avatar_url` safe on day one.
- **Why `ready()` not `AppConfig.__init__`**: Django forbids model imports during app init; signals need apps to be ready.

### D4. `ProfileInline` is a `StackedInline` on the existing `core.UserAdmin`

- **Why stacked**: the avatar field renders cleanly with the existing `ClearableFileInput` widget; tabular inline would force the image preview into a cramped row.
- **Why not a custom change-form template**: the inline uses Unfold's default form rendering, which is already in place.
- **Why attach to `UserAdmin` and not a separate URL**: admins expect user management to live at `/admin/auth/user/`. Avatars live with the user.

### D5. `avatar_thumb` is a computed `list_display` column, not a stored field

We render the `<img>` with `format_html` in a `@admin.display(description="Avatar")` method, excluded from `list_display_links`.

- **Why not store a thumbnail**: out of scope per Non-Goals; we only need a 32×32 visual cue, which the browser scales on the fly.
- **Why exclude from `list_display_links`**: the column is purely visual; clicking the username still opens the change form.

### D6. 2 MB cap as a model field validator, not a form validator

The `Profile.avatar` field uses a `validate_image_size` validator that rejects any file larger than 2 MB (2 × 1024 × 1024 bytes). The cap lives in `core/validators.py` and is referenced from the model.

- **Why model-level**: there is no public form in this change, so the only form in play is the Django admin's `ModelForm`, which honors field validators automatically. Putting the rule on the model also covers any future shell, management command, or DRF endpoint that touches `Profile`.
- **Why not a `clean_*` method on a form**: form-level cap would have to be duplicated in every form that ever edits the field.
- **Why not `DATA_UPLOAD_MAX_MEMORY_SIZE` globally**: that would break unrelated large uploads (admin imports, future bulk endpoints).
- **Why a custom validator rather than relying on Pillow's `Image.MAX_IMAGE_PIXELS` or similar**: the cap is on byte size, not dimensions; Pillow has no built-in size cap.

### D7. Storage key layout: `avatars/user_<id>/<original_filename>`

We use a callable `upload_to` (`avatar_upload_to`) instead of a static string.

- **Why a function**: lets us scope uploads under the user's ID, which is stable, makes S3 lifecycle rules trivial to write, and keeps avatars from one user from clobbering another when `file_overwrite=False`.
- **Why not UUID-prefixed**: we want predictable paths for support and S3 inspection; collisions are rare and the user-id prefix already mitigates them.

### D8. No new dependencies

Pillow (already in `requirements.txt`) is the only image library we need. No `django-cleanup` (old avatars are not auto-deleted — a known trade-off, see Risks).

### D9. Avatar as SITE_ICON via a dedicated callback (with SITE_LOGO removed)

The Unfold `SITE_ICON` config accepts a `lambda request: ...` and is invoked per request. We add `utils.callbacks.site_icon(request)` that returns `request.user.avatar_url` when present, else `static("favicon.png")`. The `SITE_ICON` lambda in `project/settings.py` is a one-liner that delegates to the callback. The project's previous `SITE_LOGO = static("logo.webp")` is **removed entirely** from `UNFOLD`.

- **Why a callback module**: matches the existing `utils.callbacks.environment_callback` pattern (already referenced from `project/settings.py:224`).
- **Why not inline in `settings.py`**: the anonymous-user fallback plus the per-user branch is more than a one-liner; keeping it out of `settings.py` preserves readability and makes the logic unit-testable.
- **Why remove `SITE_LOGO`**: Unfold's `unfold/templates/unfold/layouts/skeleton.html` includes `navigation_header.html`, which renders `site_logo.html` if `site_logo` is set and falls back to `site_icon.html` only when it is not. Setting both `SITE_LOGO` and `SITE_ICON` shadows the avatar — the static brand logo wins and the avatar is never shown in the header. Removing `SITE_LOGO` makes `SITE_ICON` (the avatar callback) the visible header image while preserving the brand text "clients Admin" / "clients Dashboard" (rendered in `site_icon.html`, not in `site_logo.html`).
- **Cross-user safety**: the lambda runs server-side per request and only ever returns the current viewer's own avatar URL. There is no path for one user to inject their avatar into another user's sidebar.
- **Anonymous handling**: `request.user` on the login page is `AnonymousUser`, which has no `avatar_url`. The callback must return the static fallback and not raise.
- **Tradeoff acknowledged**: the static `logo.webp` brand mark no longer appears in the sidebar header. Acceptable for an operator-only admin; if the brand mark is needed in the future, a custom template (`navigation_header.html`) can render both the avatar and a small brand mark side-by-side.

### D10. `Profile.primary_color` is a single hex string, default `#C92FFF`

We add a `CharField(max_length=7, default="#C92FFF", validators=[validate_hex_color, validate_contrast_against_white])` on `core.Profile`. The default matches the project's current brand purple (`oklch(0.68 0.28 296)`, hex `#C92FFF`), so users who never touch the field see no visual change.

- **Why one hex field, not 11 OKLCH shades**: the user only thinks in hex; the fan-out is mechanical and lives in the browser at render time. Storing 11 derived values would be redundant, would diverge on hue drift, and would bloat the table.
- **Why model default `#C92FFF`**: matches the existing `UNFOLD["COLORS"]["primary"][500]` token, so the change is invisible until a user picks a different color.
- **Why hex and not `ColorField` from a third-party package**: no new dependency, validation is a 7-line regex.
- **Why include a contrast validator**: the primary-600 button uses white text. A near-white base color would make primary actions unreadable. The validator computes the relative luminance of the candidate color against `#ffffff` and rejects anything below WCAG AA (4.5:1) at the effective primary-500 level. The form shows a clear error: `"Color must contrast with white at WCAG AA (4.5:1)"`.
- **Where the validator lives**: `core/validators.py` (file already created in D6 for the 2 MB cap).

### D11. `oklch(from <color> L C h)` in CSS for the 11-shade fan-out (with achromatic-source grayscale fallback)

The palette injection is **pure CSS** with no Python color math for chromatic sources. We hard-code the 11 `(L, C)` anchor pairs from the project's existing `primary` palette and let the browser derive the corresponding `oklch()` value for the user's hex color, preserving its hue:

```css
:root {
  --color-primary-50:  oklch(from #C92FFF 0.97 0.02 h);
  --color-primary-100: oklch(from #C92FFF 0.92 0.04 h);
  /* ... */
  --color-primary-600: oklch(from #C92FFF 0.60 0.25 h);
  --color-primary-950: oklch(from #C92FFF 0.20 0.08 h);
}
```

For **achromatic sources** (R≈G≈B, tolerance < 5 — covers pure black, pure white, and near-grays), the callback emits a grayscale palette:

```css
:root {
  --color-primary-50:  oklch(0.97 0 0);
  --color-primary-600: oklch(0.60 0 0);
  /* ... */
  --color-primary-950: oklch(0.20 0 0);
}
```

- **Why achromatic fallback**: `oklch(from <achromatic> L C h)` is a CSS spec footgun — achromatic sources have no hue, the browser defaults `h` to `0` (red in OKLCH), and the result is a vivid red-pink instead of the intended grayscale. Detecting achromatic in the callback and emitting `oklch(L 0 0)` avoids this. The contrast validator (D10) rejects white and most light grays at the WCAG AA level, but black passes — and black is the canonical case that motivated this fallback.
- **Why CSS interpolation over Python pre-compute**: zero DB bloat (one hex string per user vs a 22-element JSON), no recomputation on color change, and the `oklch(from)` function was added to CSS specifically for this use case.
- **Why fixed `(L, C)` anchors for chromatic sources**: they are the result of a single design decision (the project's brand palette). Hard-coding them in the callback keeps the fan-out deterministic — every shade stays perceptually equivalent across users.
- **Browser support**: Chrome 119+, Firefox 128+, Safari 16.4+, all Edge 119+ (2023–2024). The login page and `AnonymousUser` cases don't use the callback, so the static `UNFOLD["COLORS"]["primary"]` still applies. For supported browsers, no fallback is needed.
- **Graceful degradation on pre-2024 browsers**: the entire `oklch(from ...)` value is invalid CSS → the custom property falls back to its initial value (`initial` or, because of Unfold's `var(--color-primary-600, ...)` double-bind, to the static settings palette). No broken styling, just the static brand color.
- **Why not also override `base` and `font`**: out of scope (Non-Goals). Only the brand `primary` palette is per-user; neutrals and text roles stay tied to the settings-level palette so the admin chrome keeps a coherent background regardless of who is logged in.

### D12. Context processor + `{% block base %}` template override (NOT `UNFOLD["STYLES"]`)

The per-user palette CSS is delivered through a context processor + a `{% block base %}` override in `project/templates/admin/base.html` (Django's admin base template convention; the file was previously `base_site.html`, renamed to be auto-picked-up).

1. `utils.context_processors.user_palette(request)` calls `utils.callbacks.primary_palette_css(request)` and exposes the result as the template variable `user_palette_css`. The function is added to `TEMPLATES[0]["OPTIONS"]["context_processors"]` in `project/settings.py`.
2. `project/templates/admin/base.html` extends `admin/base.html` and overrides `{% block base %}`:
   ```django
   {% block base %}
   {{ block.super }}
   {% if user_palette_css %}
   <style id="user-palette">
   {{ user_palette_css|safe }}
   </style>
   {% endif %}
   {% endblock %}
   ```
   The `{{ block.super }}` call renders Unfold's default page content first; the `<style id="user-palette">` block comes after, so it wins the CSS cascade against Unfold's static `<style id="unfold-theme-colors">` block (which lives earlier in the body).

- **Why not `UNFOLD["STYLES"]`**: `UNFOLD["STYLES"]` accepts a list of callables that must return **URL strings** (which Unfold wraps in `<link rel="stylesheet" href="...">`). Returning a CSS rule body (`:root { ... }`) makes Unfold render the rule as the `href`, which the browser then tries to load as a URL — yielding a 404. We considered `!important` to win the cascade but it would still need to be delivered as a stylesheet, and the URL-as-`<link>` problem remains. The template override is the documented Django mechanism for injecting admin-wide content.
- **Why a context processor and not a template tag or middleware**: a context processor runs on every template render automatically (no manual `{% load %}` needed in every template), and it places the computation at the boundary the rest of the system already uses (Django admin already calls `each_context(request)` which invokes context processors). A template tag would require `{% load %}` in `base.html`; middleware would add complexity and break the layered approach Django expects.
- **Why `<style id="user-palette">` and not inline `style=""`**: `<style>` blocks are scope-correct (apply to the whole page), cacheable by the browser, and respect cascade order. Inline `style=""` on `:root` is not valid CSS — custom properties are set via `<style>` or external stylesheets.
- **Why place the `<style>` inside `{% block base %}` and not `{% block extrahead %}`**: `{% block extrahead %}` is in the `<head>`, before Unfold's body-level `<style id="unfold-theme-colors">`. Head-level rules lose the cascade to body-level rules of the same specificity. Placing the per-user `<style>` in the body (via `{% block base %}`) ensures it renders after `unfold-theme-colors` and wins the cascade.
- **Why `{{ user_palette_css|safe }}`**: the callback returns a pre-built CSS string. `|safe` prevents Django from auto-escaping the CSS (which would break `oklch(...)` and other CSS syntax).
- **Anonymous safety**: when `primary_palette_css` returns `""` for `AnonymousUser`/unset color, the `{% if user_palette_css %}` guard skips the `<style>` block entirely, and the static `UNFOLD["COLORS"]["primary"]` from settings applies unchanged.

## Risks / Trade-offs

- **Old avatar files leak on S3 / disk when a user replaces their avatar** → Acceptable for v1. We can add `django-cleanup` later, or a `post_delete` signal on `Profile` that calls `avatar.delete(save=False)`. Documented in the tasks file as a follow-up.
- **`User.avatar_url` does a DB hit on every template render** → Two queries (signal guarantees the profile row, so it's effectively one `Profile` lookup). The Unfold sidebar renders the property once per page. Acceptable.
- **Monkey-patched `User.avatar_url`** → If another app also defines `avatar_url`, the second import wins. Mitigation: `if not hasattr(User, "avatar_url")` guard in `core/models.py`.
- **`FileSystemStorage` in dev, S3 in prod** → No environment switch for upload handling is needed. `ImageField.url` returns the right URL for whichever backend is active. Dev needs `runserver` (or any DEBUG=True setup) for the URL to be servable — already wired in `project/urls.py`.
- **`rest_framework.authtoken` schema is unchanged** → Existing tokens keep working; no DRF code path is touched.
- **No per-user upload UX** → Staff can set avatars for everyone, but a non-staff user has no way to upload or change their own avatar from the application surface. This matches the operator-only requirement; if self-service is needed later it is a follow-up change.
- **Validation error UX in admin** → When an oversized file is rejected by the model validator, the admin change form shows a field error. No custom JS, but the standard Django validation error styling from Unfold applies.
- **Per-user primary color loses brand cohesion** → Each logged-in user sees a different admin palette. This is a deliberate UX choice (personalization) but it means screenshots, support docs, and recorded walkthroughs will look different per user. Acceptable for an internal operator-only tool; reconsider if the admin ever ships to external tenants.
- **WCAG AA contrast check rejects valid brand palettes** → A handful of saturated colors (e.g. `#FFEB3B` yellow) fail 4.5:1 against white. The form error points the user at a darker alternative. The default `#C92FFF` passes 4.5:1 against white, so out-of-the-box there is no friction.
- **CSS injection runs on every admin request** → One ~500-byte string per page; cost is negligible. No DB hit per request — the value is on the cached `User` object the admin already loads.
- **Cross-user color injection is impossible** → The `oklch(from)` rule carries only the viewer's own color. A user can never influence what another user sees in the admin. The mechanism has two layers of safety: (1) the `validate_hex_color` + `validate_contrast_against_white` validators run at save time on the server, so a malicious payload (`<script>`, oversized strings, non-hex values, low-contrast colors) is filtered before it reaches the database; (2) the CSS injection is rendered only into the **current viewer's own response**, so even if the validator were bypassed, the worst case is a user setting their own admin palette to a weird value — never affecting anyone else's view. Each user only sees their own CSS; there is no shared CSS asset.

## Migration Plan

Two migrations under `core/migrations/`, applied in order on `migrate core`:

1. `0001_initial.py` — creates `core_profile` with `user` (OneToOneField), `avatar` (ImageField, validators=[validate_image_size]), and `primary_color` (CharField, default `#C92FFF`, validators=[validate_hex_color, validate_contrast_against_white]) columns. All three fields are added in this single migration.
2. `0002_backfill_profiles.py` — `RunPython` that calls `Profile.objects.get_or_create(user=u)` for every user, so the relation is present immediately and `User.avatar_url` is safe to call for every user.

**Forward**:

1. Deploy code with the new model, signal, validators, admin wiring, the `site_icon` + `primary_palette_css` callbacks, the `user_palette` context processor, the new `project/templates/admin/base.html` template, and the updated `project/settings.py` (`SITE_ICON` → `site_icon`, `SITE_LOGO` removed, context processor registered).
2. `python manage.py migrate core` runs both migrations in order.
3. Admins immediately see thumbnails in the user changelist and can upload, replace, or clear avatars AND pick a `primary_color` via the Unfold color widget in `/admin/auth/user/<id>/change/` and `/admin/core/profile/`. The avatar appears in the sidebar header (with the "clients Admin" / "clients Dashboard" brand text) and the per-user palette takes effect immediately.

**Rollback**:

1. `python manage.py migrate core zero` reverts both migrations. The `User` model and auth tokens are untouched, so user authentication keeps working.
2. Avatars already uploaded to S3 remain in the bucket; clean up with a one-liner S3 CLI by prefix `avatars/` if needed.
3. `primary_color` defaults to `#C92FFF` after rollback if the column is dropped, so no orphan values.

**Data safety**:

- `OneToOneField` + signal guarantee no orphan profiles.
- `Profile.avatar` and `Profile.primary_color` are both optional with sensible defaults, so the migration is safe on a database with or without media.

## Deferred Decisions

The following items were considered during planning and intentionally deferred to follow-up changes or left out of scope. They are listed here so future contributors do not re-litigate the same tradeoffs.

- **Avatar file cleanup on replace** — When a user replaces their avatar, the previous file is not deleted. Acceptable for v1. Add `django-cleanup` or a `post_delete` signal in a follow-up.
- **Non-staff user surfaces for avatars or colors** — Out of scope. The operator (admin) is the only one who sets these. Add a follow-up change if the product needs user-level upload UX.
- **Per-user `base` and `font` palettes** — Only `primary` is per-user in this change. The `base` (neutrals) and `font` (text roles) palettes stay tied to settings so the admin chrome keeps a coherent background. Extend in a follow-up if personalization depth matters.
- **Per-user `SITE_LOGO`, `BORDER_RADIUS`, or other static theming settings** — Out of scope. Only `SITE_ICON` and the `primary` palette swap.
- **Self-service `/profile/` page** — Rejected earlier in the design. The operator-only requirement stands.
- **Image resizing, EXIF stripping, thumbnailing beyond 32×32** — Out of scope. The 2 MB size cap is the only image constraint.

## Resolved Decisions (recap)

For traceability, the questions answered during planning and validation:

- _Resolved_: Should users self-service? → No. Only the operator (admin) sets avatars via the Django admin.
- _Resolved_: Image constraints? → 2 MB cap at the model validator layer, no resize.
- _Resolved_: Admin changelist thumbnail? → Yes, 32×32 rounded.
- _Resolved_: SITE_ICON vs SITE_LOGO? → `SITE_LOGO` was removed entirely from `UNFOLD` so the avatar can render in the sidebar header. The brand text "clients Admin" / "clients Dashboard" still shows (rendered in `site_icon.html`, not `site_logo.html`). The static `logo.webp` brand mark is gone from the admin.
- _Resolved_: How are the 11 OKLCH shades computed from the single hex? → CSS-native `oklch(from <color> L C h)` for chromatic sources, `oklch(L 0 0)` for achromatic sources (R≈G≈B), with hard-coded `(L, C)` anchors matching the existing `primary` palette.
- _Resolved_: How is the per-user CSS injected? → Context processor `utils.context_processors.user_palette` + `{% block base %}` override in `project/templates/admin/base.html` (NOT `UNFOLD["STYLES"]`, which only accepts URL strings).
- _Resolved_: What color picker widget? → Unfold's built-in `UnfoldAdminColorInputWidget` (unfold/widgets.py:373).
- _Resolved_: Who gets a per-user color? → All users, including superuser. The login page keeps the static palette.
- _Resolved_: Contrast guard algorithm? → Raw-hex relative luminance check, threshold `< 0.4` against white, calibrated so any OKLCH derivation at the project's primary-500 L/C anchors also fails WCAG AA when the raw check fails.
- _Resolved_: Why does black become a grayscale palette and not a red one? → Achromatic-source detection in the callback switches from `oklch(from <color> L C h)` to `oklch(L 0 0)` when R≈G≈B. Without this, the browser would default the undefined hue of an achromatic source to `0` (red in OKLCH), producing a pink palette.
