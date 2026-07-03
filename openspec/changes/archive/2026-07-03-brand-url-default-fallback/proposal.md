## Why

Every brand-driven visual element in the admin — logo, primary color, favicon, site titles — already resolves per-user from `Brand` (via `Membership`). But two gaps remain:

1. **Users without an explicit brand see hardcoded `"clients"` titles and static `favicon.png`** — no visual connection to the platform's default brand identity. The `Brand.get_or_create_default()` row exists but is only used for new-user assignment, never for branding fallback.

2. **The login page is always unbranded** — every brand's users see the same generic `"clients"` title/favicon/colors before logging in. There's no way to give each brand a unique login URL that pre-loads its branding.

Closing both gaps creates a consistent visual experience: a user (or visitor) always sees a brand's name, logo, and colors — whether they're unauthenticated, lack an explicit brand assignment, or are visiting a brand-specific login URL.

## What Changes

- **`Brand` model** gains two fields:
  - `slug` (`SlugField`, unique) — auto-generated from `name`, used in login URLs (`?brand=<slug>`)
  - `is_default` (`BooleanField`, default `False`) — designates the system's fallback brand; `save()` ensures only one brand holds this flag at a time
  - `get_or_create_default()` updated to set `is_default=True` on the auto-created row

- **New middleware** `utils.middleware.BrandUrlMiddleware`:
  - Extracts `?brand=<slug>` from the query string on the admin login page only
  - Resolves the brand via `slug` lookup and sets `request._brand_override`
  - Scoped to login path via `reverse_lazy('admin:login')`; silent fall-through on non-existent slug

- **`utils/callbacks.py`** refactored with a unified `_resolve_brand(request)` helper:
  - Adds lazy `from core.models import Brand` inside the function body (avoids Django startup circular import: `settings.py` → `callbacks.py` → `core.models` before app registry is ready)
  - Priority 1: URL override (`request._brand_override`, login page only)
  - Priority 2: User's brand (`request.user.brand` via `Membership`)
  - Priority 3: Default brand (`Brand.objects.filter(is_default=True).first()`)
  - Priority 4: `None` (hardcoded `"clients"` / static `favicon.png`)
  - Result cached on `request._brand_cache` to avoid redundant DB queries across multiple callbacks
  - Five callbacks refactored: `site_title`, `site_header`, `site_icon`, `site_favicon`, `primary_palette_css` (`site_subheader` is unchanged — always `"Dashboard"`)
  - `primary_palette_css` uses `:root:root` selector (higher specificity than Unfold's `:root` in `skeleton.html`) so brand palette wins against unfold-theme-colors regardless of DOM order

- **New login template** `project/templates/admin/login.html`:
  - Extends Unfold's `admin/login.html`
  - Overrides `{% block extrastyle %}` to inject `{{ user_palette_css|safe }}` as `<style id="user-palette">`
  - Required because the Unfold login page template chain (`skeleton.html` → `unauthenticated.html` → `login.html`) does NOT extend `admin/base.html`, so the existing `project/templates/admin/base.html` override does not apply to the login page

- **`core/admin.py`**: add `is_default` to `BrandAdmin.list_display` (boolean icon, superuser-edit only)

- **`project/settings.py`**: add `BrandUrlMiddleware` after `AuthenticationMiddleware`

## Capabilities

### New Capabilities

- `brand-url-override`: URL query parameter (`?brand=<slug>`) on the login page resolves a `Brand` by slug and applies its name, logo, favicon, and primary color palette to the login page rendering

### Modified Capabilities

- `brand-management`: `Brand` model gains `slug` and `is_default` fields; the system default brand is now explicitly marked rather than name-based; `Brand.name` driven site titles (spec requirement "Brand.name drives admin chrome site titles") now resolves through the 4-priority chain instead of the 2-priority chain (user → hardcoded)
- `per-user-primary-color`: `primary_palette_css` callback now falls back through the default brand's color before returning empty; the "Anonymous request" scenario now shows the default brand's palette (if one exists) instead of the static `UNFOLD["COLORS"]["primary"]`
- `unfold-admin-theme`: the `SITE_ICON`, `SITE_FAVICONS`, `SITE_TITLE`, and `SITE_HEADER` config values now resolve through the 4-priority chain

## Impact

| Area | Change |
|---|---|
| `core/models.py` | `Brand`: +2 fields (`slug`, `is_default`), update `save()` for slug generation + `is_default` enforcement, update `get_or_create_default()` |
| `utils/middleware.py` | **New file**: `BrandUrlMiddleware` (login-page `?brand=<slug>` lookup) |
| `utils/callbacks.py` | Unified `_resolve_brand(request)` helper, all 5 callbacks refactored, `:root:root` specificity for palette |
| `project/templates/admin/login.html` | **New file**: extends Unfold's `admin/login.html`, injects `user_palette_css` via `extrastyle` block |
| `core/admin.py` | `is_default` in `BrandAdmin.list_display` |
| `project/settings.py` | Add middleware to `MIDDLEWARE` |
| `core/tests.py` | Updated callback tests for 4-priority chain, new middleware tests, new model tests for slug + is_default |
| `openspec/specs/per-user-primary-color/spec.md` | Updated: stale `Profile` references replaced with `Brand`; anonymous scenario now reflects default brand fallback instead of static palette |
| `openspec/specs/unfold-admin-theme/spec.md` | Updated: "Site branding" scenario now describes default brand fallback for unauthenticated/login page |
| Migration | Auto-generated via `makemigrations` (see tasks): 2 schema migrations + 1 data migration for backfill |
| No new dependencies | Zero packages added |