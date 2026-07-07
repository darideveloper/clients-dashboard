## Context

The project uses django-unfold for admin theming. Custom branding (logo, primary color, favicon) resolves per-request via `_resolve_brand()` in `utils/callbacks.py`. Palette CSS is injected into admin pages via a context processor (`user_palette`) which provides `user_palette_css` — a set of `:root:root` CSS custom properties (`--color-primary-50` through `--color-primary-950`) in OKLCH.

Currently:
- **Login page**: Custom `project/templates/admin/login.html` injects `user_palette_css` in `{% block extrastyle %}`
- **Admin pages**: Custom `project/templates/admin/base.html` injects `user_palette_css` in `{% block base %}`
- **Logout page**: No override exists — Unfold's default `registration/logged_out.html` renders without brand colors

Unfold's logout template (`registration/logged_out.html`) extends `unfold/layouts/unauthenticated.html`, which does NOT extend `admin/base.html`. Therefore neither the base.html override nor the login.html override covers it.

The fix requires a new template at `project/templates/registration/logged_out.html` mirroring the login override's pattern.

### CSS injection order in skeleton.html

Unfold's layout root `skeleton.html` loads CSS in this order:

```
Line 32: unfold/css/styles.css              ← Unfold's base styles (defines --color-primary-* via CSS variables)
  ...
Line 47: {% block extrastyle %}{% endblock %} ← OUR INJECTION POINT (user_palette_css via :root:root)
  ...
Line 73: {% if colors %}
         <style id="unfold-theme-colors">    ← Unfold's static UNFOLD.COLORS values
           :root { --color-primary-50: ... }
         </style>
         {% endif %}
  ...
Line 89: {% block base %}{% endblock %}
```

The `#unfold-theme-colors` style (body) comes AFTER `extrastyle` (head) in DOM order, so it would normally override `#user-palette` values. However, `user_palette_css` uses the `:root:root` selector (double class, specificity 0,0,2,0) which beats Unfold's single `:root` (specificity 0,0,1,0). This ensures brand colors always win regardless of DOM position.

### Palette resolution on logout

`_resolve_brand()` on logout:
1. `request._brand_cache` — not set (first call)
2. `request._brand_override` — NOT set (`BrandUrlMiddleware` only handles `admin:login`, not `admin:logout`)
3. `request.user.brand` — skipped (user is `AnonymousUser`, `is_authenticated` is `False`)
4. Falls to **default brand** via `Brand.objects.filter(is_default=True).first()`

The logout page will always show the **default brand's** colors. The `?brand=` query parameter (handled by `BrandUrlMiddleware` on login) is NOT preserved on logout. This is intentional — brand-based URL overrides apply only to the login entry point; unauthenticated global pages show the default identity.

## Goals / Non-Goals

**Goals:**
- Brand palette CSS (`user_palette_css`) renders on the logout screen
- Same injection pattern as login — `{% block extrastyle %}` override
- No changes to Python code, views, middleware, or settings
- Works with or without a logged-in user (context processor already handles unauthenticated requests)

**Non-Goals:**
- Not adding new content or UI elements to the logout page
- Not modifying Unfold's logout behavior or redirect logic
- Not changing the login template

## Template

The override at `project/templates/registration/logged_out.html`:

```django
{% extends "registration/logged_out.html" %}
{% block extrastyle %}
    {{ block.super }}
    {% if user_palette_css %}
    <style id="user-palette">
        {{ user_palette_css|safe }}
    </style>
    {% endif %}
{% endblock %}
```

Inheritance chain: `logged_out.html` (project) → `registration/logged_out.html` (Unfold) → `unfold/layouts/unauthenticated.html` → `unfold/layouts/skeleton.html`

`{% extends "registration/logged_out.html" %}` resolves through Django loaders, skipping the project override (current source) and falling through to Unfold's version — same mechanism already proven by `admin/login.html`.

## Decisions

| Decision | Choice | Rationale |
|---|---|---|
| Template location | `project/templates/registration/logged_out.html` | Matches Unfold's template path; Django's template resolution finds it automatically |
| extends target | `"registration/logged_out.html"` (name, not full path) | Reuses Unfold's template chain; Django skips current source on resolution |
| Injection point | `{% block extrastyle %}` | Matches login template; exists in `skeleton.html:48`, inherited by unauthenticated layout |
| Palette source | `{{ user_palette_css }}` from context processor | Already available on logout page — context processor fires for every request, including unauthenticated ones |
| Safety check | `{% if user_palette_css %}` guard | Graceful fallback if context processor is removed or returns empty |

## Risks / Trade-offs

| Risk | Mitigation |
|---|---|
| Unfold upgrades change logout template structure | Override only injects CSS in `extrastyle` block — if template chain changes, the block may not exist. Test on Unfold upgrade. |
| `user_palette_css` returns empty for some users | If/guard prevents broken `<style>` tag from rendering |
| `?brand=` query param lost on logout | Palette always resolves to default brand — documented behavior, not a bug. If brand-on-logout is needed, it's a separate change (extend `BrandUrlMiddleware` or use session). |
