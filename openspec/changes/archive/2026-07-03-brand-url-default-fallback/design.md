## Context

The admin already resolves per-user branding (logo, favicon, color, titles) via `utils/callbacks.py` → `request.user.brand` through the `Membership` link table. The two gaps are:

1. **No default brand fallback**: users without a brand or unauthenticated visitors hit hardcoded `"clients"` strings instead of a system-wide default brand.
2. **No pre-login brand switching**: every brand's users see identical login page branding. A URL parameter enables brand-specific login URLs (e.g., `/admin/login/?brand=acme`).

Unfold's `UnfoldAdminSite.each_context(request)` calls all branding callbacks on every page including the login page. The callbacks receive the `request` object — so middleware can inject an override that the callbacks consume.

## Goals / Non-Goals

**Goals:**
- Designate one `Brand` as the system default (`is_default=True`), used as branding fallback for users without an explicit brand and for unauthenticated visitors
- Support `?brand=<slug>` query param on the admin login page to pre-load a brand's visual identity (name, logo, favicon, color)
- Unify branding resolution into a single helper function with 4-tier priority
- Scope URL-based branding to the login page only (no impact on authenticated admin pages)
- Auto-generate a URL-safe `slug` from `Brand.name`
- Cache the resolved brand on the request object to avoid redundant DB queries

**Non-Goals:**
- Brand-specific login page templates (same Unfold login page, just different data)
- Subdomain-based or path-based brand routing (e.g., `acme.example.com/admin/`)
- Persisting `?brand=` across the login redirect to post-login pages (after login, `user.brand` takes over)
- On-the-fly brand resolution (all resolution is at request time via middleware + callbacks, no async)

## Decisions

### D1: `is_default` BooleanField with `save()` enforcement over UniqueConstraint

**Chosen: BooleanField + `save()` override that un-sets other brands' `is_default`.**

The new `is_default`/`slug` logic runs **before** `super().save()`, while the existing favicon generation (logo-change detection, `_generate_favicon()`) runs **after** — same as today. Merged `save()`:

```python
def save(self, *args, **kwargs):
    if self.is_default:
        Brand.objects.exclude(pk=self.pk).update(is_default=False)
    if not self.slug:
        self.slug = slugify(self.name)
    super().save(*args, **kwargs)
    # --- existing favicon logic (unchanged) ---
    current_name = self.logo.name if self.logo else None
    if current_name != self._original_logo_name:
        if current_name:
            self._generate_favicon()
        else:
            self._delete_favicon_if_exists()
    self._original_logo_name = current_name
```

For new (unsaved) brands, `self.pk` is `None` — `exclude(pk=None)` excludes nothing in SQL, so ALL other brands get `is_default=False`. This is correct: the new brand becomes the sole default.

| Alternative | Why not chosen |
|---|---|
| `UniqueConstraint(condition=Q(is_default=True))` | Partial unique indexes vary across backends (Postgres ✓, SQLite 3.37+ ✓ in Django 4.2+, MySQL 8.0.13+ limited). The project targets multiple backends. `save()` override is backend-agnostic. |
| Name-based lookup (use `get_or_create_default()`) | Fragile — renaming "Default Brand" silently breaks the fallback. `is_default` is explicit and admin-visible. |
| Settings-based `DEFAULT_BRAND_ID` | Requires restart on change, not admin-manageable. |

Race condition (two admins saving `is_default=True` simultaneously) is theoretically possible but practically negligible for an admin-only operation.

### D2: `slug` field auto-generated from `name`

**Chosen: `SlugField(max_length=100, unique=True, blank=True)`, auto-populated in `save()` when empty.**

`Brand.name` can contain spaces and special characters — ugly in URLs (`?brand=Acme+Corp`). `slug` gives clean, URL-safe identifiers (`?brand=acme-corp`).

Auto-generation on save when slug is empty means:
- New brands get a slug automatically
- Existing brands get back-filled by migration
- Admins can manually override the slug (admin form exposes it)
- `unique=True` prevents collisions

Lookup in middleware: `Brand.objects.get(slug=brand_slug)` — exact match, not case-insensitive (slugs are already lowercase).

**Migration strategy:** The `slug` field starts with `unique=False` so `makemigrations` can add the column for existing rows. The migration sequence is:

1. **Schema migration (auto-generated):** Add `slug` field to model with `unique=False, blank=True`, add `is_default` field. Run `python manage.py makemigrations core` to generate `0004_*`.
2. **Data migration (manually written `RunPython`):** `python manage.py makemigrations core --empty --name backfill_brand_slugs` generates an empty `0005_*`. Manually fill in: `RunPython(set_slugs_and_default, RunPython.noop)` — iterates all brands, generates `slugify(name)`, assigns slugs (with `-<pk>` suffix on collision), sets `is_default=True` on the row matching `Brand.DEFAULT_NAME`.
3. **Schema migration (auto-generated):** Change `slug` to `unique=True` in the model. Run `python manage.py makemigrations core` to generate `0006_*` with `AlterField`.

No migration file is written by hand — schema migrations are always `makemigrations` output. Only the RunPython body in the empty data migration is authored manually.

### D3: Middleware scoped to login page only via `reverse_lazy`

**Chosen: `BrandUrlMiddleware` that checks `request.path` against `reverse_lazy('admin:login')`.**

```python
class BrandUrlMiddleware:
    login_path = reverse_lazy('admin:login')

    def __call__(self, request):
        if request.path.rstrip('/') == str(self.login_path).rstrip('/'):
            slug = request.GET.get('brand')
            if slug:
                try:
                    request._brand_override = Brand.objects.get(slug=slug)
                except Brand.DoesNotExist:
                    pass  # silent fall-through to next priority
        return self.get_response(request)
```

| Alternative | Why not chosen |
|---|---|
| Middleware activates on ALL paths | `?brand=acme` on `/admin/core/brand/` would override the authenticated user's actual brand — wrong behavior |
| No middleware; callbacks parse `?brand=` themselves | Duplicated logic across 5 callbacks, harder to test |
| `resolve()` to detect login page at runtime | `resolve()` is expensive (URL resolution runs twice). `reverse_lazy` is computed once at module load |
| Session storage of brand param across redirect | Over-engineering — after login, `user.brand` takes over naturally |

Timing: middleware runs before `UnfoldAdminSite.each_context()`, so `request._brand_override` is set before callbacks execute.

POST form submissions preserve `?brand=` in the URL (form `action=""`), so failed logins re-render with the same branding. Successful logins redirect to `/admin/` — `?brand=` is dropped, `user.brand` takes over.

### D4: Unified `_resolve_brand(request)` helper with request-scoped cache

**Chosen: Single helper function cached on `request._brand_cache`.**

Uses a lazy `import` inside the function body (`from core.models import Brand`) to avoid a Django startup circular import: `project/settings.py` imports `utils.callbacks` at module level, which would trigger `core.models` loading before the app registry is ready. The lazy import defers model resolution to request time, when all apps are fully loaded. Safe — `core/models.py` has no dependency on `utils/callbacks.py`, so no circular import risk at runtime.

```python
def _resolve_brand(request):
    from core.models import Brand
    if hasattr(request, '_brand_cache'):
        return request._brand_cache

    # 1. URL override (login page ?brand=<slug>)
    brand = getattr(request, '_brand_override', None)

    # 2. User's brand (Membership link)
    if not brand:
        user = getattr(request, 'user', None)
        if user and user.is_authenticated:
            brand = getattr(user, 'brand', None)

    # 3. Default brand (is_default=True)
    if not brand:
        brand = Brand.objects.filter(is_default=True).first()

    request._brand_cache = brand
    return brand
```

Priority chain:
```
1. ?brand=<slug>      → URL override (login page only, set by middleware)
2. user.brand          → Membership link (authenticated users)
3. is_default Brand    → System fallback (unauthenticated, no brand)
4. None                → Hardcoded "clients" / static favicon (safety net)
```

| Alternative | Why not chosen |
|---|---|
| Each callback does its own resolution | 5× redundant DB queries, harder to maintain consistency |
| Cache key uses a separate request attribute name than before | The old `_brand_name_cache` only cached the name string. The new cache stores the whole Brand object, enabling logo/color resolution in a single query |
| `threading.local` or `contextvars` for cache | Unnecessary — Django's request-per-thread model means `request` is the natural scope |

### D5: `_get_or_create_default()` sets `is_default=True`

**Chosen: Update the existing classmethod to include `is_default=True` in `defaults`.**

```python
@classmethod
def get_or_create_default(cls):
    obj, _ = cls.objects.get_or_create(
        name=cls.DEFAULT_NAME,
        defaults={
            "primary_color": cls.DEFAULT_PRIMARY_COLOR,
            "is_default": True,
        },
    )
    return obj
```

This means:
- `seed_brands` command (which calls `get_or_create_default()`) automatically marks the brand as default — no command changes needed
- `UserAdmin.save_model` (which assigns default brand to new users) is unaffected
- If a migration back-fills `is_default=True` on the existing "Default Brand" row, subsequent calls to `get_or_create_default()` are a no-op (row already exists with correct values)

### D6: Middleware position after `AuthenticationMiddleware`

**Chosen: Insert after `AuthenticationMiddleware` in `MIDDLEWARE` list.**

The middleware doesn't strictly need `request.user` (it only reads `request.GET`), but placing it near auth middleware is semantically appropriate (brand resolution is user-adjacent). Position is:

```python
MIDDLEWARE = [
    ...
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "utils.middleware.BrandUrlMiddleware",                    # NEW
    "django.contrib.messages.middleware.MessageMiddleware",
    ...
]
```

### D7: `is_default` in admin: display-only, superuser-edit

**Chosen: Add to `BrandAdmin.list_display`, editable in form (which is already superuser-gated by `has_change_permission`).**

Unfold renders `BooleanField` with a checkmark/cross icon in list display — zero template work. The field is available in the change form for superusers only (consistent with existing `BrandAdmin.has_change_permission` → `request.user.is_superuser`).

### D8: Login page palette injection via `project/templates/admin/login.html`

**Chosen: Override `admin/login.html` in project templates, injecting `user_palette_css` into `{% block extrastyle %}`.**

The Unfold login page uses a different template chain (`unfold/layouts/unauthenticated.html` → `unfold/layouts/skeleton.html`) that does NOT extend `admin/base.html`. The existing `project/templates/admin/base.html` override injects `user_palette_css` in `{% block base %}` after `{{ block.super }}`, which works for authenticated admin pages but has no effect on the login page.

```django
{% extends "admin/login.html" %}
{% block extrastyle %}
    {{ block.super }}
    {% if user_palette_css %}
    <style id="user-palette">
        {{ user_palette_css|safe }}
    </style>
    {% endif %}
{% endblock %}
```

`extrastyle` renders inside `<head>` in `skeleton.html` (line 48), before the `unfold-theme-colors` style tag in `<body>`. This means the palette tag appears earlier in the DOM — the cascade fix (D9) is therefore essential.

| Alternative | Why not chosen |
|---|---|
| Override `unfold/layouts/unauthenticated.html` | Too broad — would affect all unauthenticated pages, not just login |
| Inject via `UNFOLD["STYLES"]` | Static URLs only, cannot inject dynamic CSS per-request |
| Inject via `{% block base %}` in login template | `base` block wraps the entire page content in `unauthenticated.html` — overriding it means duplicating the full HTML structure |

### D9: `:root:root` CSS selector for higher specificity over Unfold's `:root`

**Chosen: Use `:root:root` (specificity 0,2,0) instead of `:root` (specificity 0,1,0) in the CSS output of `primary_palette_css()`.**

`skeleton.html` renders the static `unfold-theme-colors` style tag in `<body>` (line 65) using a `:root` selector. Because the login page injects the user palette in `extrastyle` (inside `<head>`), the DOM order is:

```
<head>
  <style id="user-palette"> :root { ... } </style>    ← from extrastyle
</head>
<body>
  <style id="unfold-theme-colors"> :root { ... } </style>  ← from skeleton.html
</body>
```

Both use `:root` — same specificity — so `unfold-theme-colors` wins because it comes later in source order. Using `:root:root` gives the user palette higher specificity (0,2,0 vs 0,1,0), making it win regardless of DOM order. On authenticated admin pages, `user-palette` already comes after `unfold-theme-colors` in the `{% block base %}` injection, so the `:root:root` is redundant but harmless.

```python
# Before (specificity 0,1,0 — loses to later :root in DOM):
return f":root {{\n{rules}\n}}"

# After (specificity 0,2,0 — always wins):
return f":root:root {{\n{rules}\n}}"
```

| Alternative | Why not chosen |
|---|---|
| Move user palette injection to `{% block base %}` for login page | Requires duplicating the entire page wrapper HTML from `unauthenticated.html` |
| `!important` in palette CSS | Overly aggressive — would break manual theme overrides and is technically wrong for CSS custom properties |
| Inject palette twice (both extrastyle and base) | Duplicate `<style>` tags, waste bytes, no clear benefit |

## Data Flow

```
┌─────────────────────────────────────────────────────────────────────┐
│ REQUEST FLOW                                                         │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  GET /admin/login/?brand=acme                                        │
│  ──────────────────────────────▶                                     │
│    │                                                                 │
│    ├─ BrandUrlMiddleware                                             │
│    │  path == admin:login? → YES                                     │
│    │  brand_slug = "acme"                                            │
│    │  Brand.objects.get(slug="acme") → Brand(id=2, name="Acme Corp") │
│    │  request._brand_override = Brand(id=2)                          │
│    │                                                                 │
│    ├─ UnfoldAdminSite.each_context(request)                          │
│    │  site_title(request) → _resolve_brand(request)                  │
│    │    → request._brand_override → Brand(id=2) ✓                    │
│    │    → return "Acme Corp"                                         │
│    │  site_icon(request) → same Brand(id=2)                          │
│    │    → return brand.logo.url                                      │
│    │  site_favicon(request) → same Brand(id=2)                       │
│    │    → return brand.favicon_url                                   │
│    │  primary_palette_css(request) → same Brand(id=2)                │
│    │    → return ":root:root { --color-primary-500: oklch(...) }"    │
│    │                                                                 │
│    └─ Template renders with Acme Corp branding                       │
│                                                                     │
│  POST /admin/login/?brand=acme (form submit)                         │
│  ──────────────────────────────▶                                     │
│    Same middleware + callbacks execution                             │
│    Login succeeds → redirect 302 to /admin/                          │
│                                                                     │
│  GET /admin/ (post-redirect)                                         │
│  ──────────────────────────────▶                                     │
│    BrandUrlMiddleware                                                │
│    path != admin:login → SKIP                                        │
│    request._brand_override = (not set)                               │
│                                                                     │
│    _resolve_brand(request)                                           │
│    → request._brand_override → None (skip)                           │
│    → user.is_authenticated → YES                                     │
│    → user.brand → Brand(id=2) ✓                                     │
│    → return "Acme Corp"                                              │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

## Risks / Trade-offs

| Risk | Impact | Mitigation |
|---|---|---|
| **`is_default` race condition on concurrent saves** | Two brands could temporarily both hold `is_default=True` | Two superusers saving simultaneously is extremely unlikely in a single-admin setup. The `save()` override runs in a single DB query before the actual write, minimizing the window. If it occurs, the last save wins — acceptable. |
| **Slug collision on auto-generation** | Two brands with same slugified name (e.g., "Acme" and "ACMÉ") | `unique=True` enforces DB-level constraint. The second save raises `IntegrityError`. Admin sees the error and manually adjusts the slug. |
| **`Brand.objects.filter(is_default=True)` query on every unauth request** | One DB query per login page load | Acceptable — login page is low traffic. The cache on `request._brand_cache` means subsequent callback calls within the same request are free. |
| **Existing brands don't have a slug (before migration)** | `IntegrityError` on migration if multiple brands have conflicting slugs | Migration back-fills slugs sequentially using `slugify(name)`. If collision, suffix with `-<pk>`. Tested in migration test. |
| **Brand.delete() doesn't clear `is_default`** | If the default brand is deleted, no brand has `is_default=True` | `on_delete=PROTECT` on `Membership.brand` blocks deletion of any brand with users. The only deletable brand is one with zero members. If an admin deletes the default brand and no other brand is flagged, the system falls back to hardcoded strings (tier 4) — consistent with current behavior. |
| **`reverse_lazy` import from `django.urls`** | Module import order — `reverse_lazy` is importable before URL conf is loaded (that's its purpose) | The lazy object resolves only when `__str__()` is called, which happens at request time (URL conf fully loaded). This is standard Django middleware practice. |