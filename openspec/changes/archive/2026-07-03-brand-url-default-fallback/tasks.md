## 1. Brand Model Changes

- [x] 1.1 Add `slug` field: `SlugField(max_length=100, unique=False, blank=True)` — start with `unique=False` so the initial schema migration can add the column to tables with existing rows
- [x] 1.2 Add `is_default` field: `BooleanField(default=False)`
- [x] 1.3 Update `save()`:
  - If `not self.slug`: auto-generate from `name` via `slugify()`
  - If `self.is_default`: `Brand.objects.exclude(pk=self.pk).update(is_default=False)` before super call
  - Preserve existing logo-change detection and favicon generation logic (WARNING: wrap all additions around the existing `super().save()` call — do NOT duplicate favicon logic in a second save call)
  - Use `super().save(*args, **kwargs)` exactly once to avoid double-save bugs
- [x] 1.4 Update `get_or_create_default()`: add `"is_default": True` to `defaults` dict
- [x] 1.5 Update `Brand.__init__`: ensure `_original_logo_name` still snapshots before slug/is_default fields are available (no functional change — these fields don't interact with logo tracking)
- [x] 1.6 Run `python manage.py makemigrations core` — auto-generates migration `0004_*` adding `slug` (without unique) and `is_default` columns
- [x] 1.7 Run `python manage.py makemigrations core --empty --name backfill_brand_slugs` — generates empty `0005_*`. Manually fill in the `RunPython` operation:
  - Forward: iterate all `Brand` rows, compute `slugify(name)`, assign `slug`. On collision (same slug from different names), suffix with `-{pk}` (e.g., `"acme-2"`)
  - Forward: set `is_default=True` on the row where `name == Brand.DEFAULT_NAME`
  - Reverse: `RunPython.noop`
- [x] 1.8 Change `slug` field to `unique=True` in the model
- [x] 1.9 Run `python manage.py makemigrations core` — auto-generates migration `0006_*` with `AlterField` adding the unique constraint AFTER the backfill is applied

## 2. Brand Resolution Helper

- [x] 2.0 Add lazy `from core.models import Brand` inside `_resolve_brand()` function body (not top-level) to avoid Django startup circular import: `settings.py` → `callbacks.py` → `core.models` before app registry is ready
- [x] 2.1 Add `_resolve_brand(request)` function to `utils/callbacks.py`:
  - Priority 1: `getattr(request, '_brand_override', None)`
  - Priority 2: `request.user.brand` (if authenticated)
  - Priority 3: `Brand.objects.filter(is_default=True).first()`
  - Cache result on `request._brand_cache`
  - Return `Brand` instance or `None`
- [x] 2.2 Refactor `site_title(request)` and `site_header(request)`: call `_resolve_brand(request)`, return `brand.name` or `FALLBACK_TITLE`/`FALLBACK_HEADER`
- [x] 2.3 Refactor `site_icon(request)`: call `_resolve_brand(request)`, return `brand.logo.url` or `static("favicon.png")`
- [x] 2.4 Refactor `site_favicon(request)`: call `_resolve_brand(request)`, return `brand.favicon_url` or `static("favicon.png")`
- [x] 2.5 Refactor `primary_palette_css(request)`: call `_resolve_brand(request)`, return CSS palette from `brand.primary_color` or `""`
- [x] 2.6 Remove `_resolve_brand_name()` helper — no longer needed (superseded by `_resolve_brand()`)
- [x] 2.7 Remove `_request_attr = "_brand_name_cache"` module-level constant — no longer needed

## 3. Middleware

- [x] 3.1 Create `utils/middleware.py` with `BrandUrlMiddleware` class:
  - `login_path = reverse_lazy('admin:login')`
  - `__call__`: if `request.path.rstrip('/') == str(self.login_path).rstrip('/')` AND `request.GET.get('brand')` is truthy → `Brand.objects.get(slug=slug)` → set `request._brand_override`
  - Silent `except Brand.DoesNotExist`: pass (fall through to next priority)
- [x] 3.2 Add `"utils.middleware.BrandUrlMiddleware"` to `MIDDLEWARE` in `project/settings.py`, right after `AuthenticationMiddleware`

## 4. Admin

- [x] 4.1 Add `"is_default"` to `BrandAdmin.list_display` — Unfold will render it as a boolean icon automatically
- [x] 4.2 Include `"slug"` in `BrandAdmin.fields` or `fieldsets` if not already present (Django admin auto-includes all non-auto fields by default; verify slug is editable for superusers in the change form)

## 5. Tests

- [x] 5.1 `BrandModelTests` — new tests:
  - `test_is_default_enforcement`: save brand A with `is_default=True`, save brand B with `is_default=True`, verify only B has `is_default=True`
  - `test_slug_auto_generated_from_name`: save brand with name "Test Brand", verify slug is "test-brand"
  - `test_slug_preserved_on_update`: change brand name, verify slug stays the same
  - `test_get_or_create_default_sets_is_default`: verify row returned by `get_or_create_default()` has `is_default=True`
- [x] 5.2 `_resolve_brand` tests — call helper directly:
  - `test_url_override_wins`: set `request._brand_override`, verify it's returned over `user.brand`
  - `test_user_brand_wins_without_url_override`: authenticated user with brand, no URL override → returns user's brand
  - `test_is_default_wins_when_no_user_brand`: unauthenticated or user without brand, is_default brand exists → returns it
  - `test_returns_none_when_nothing_exists`: no URL override, no user brand, no is_default → returns None
  - `test_cache_avoids_duplicate_queries`: call twice on same request, verify only one `Brand.objects.filter` query via `assertNumQueries`
- [x] 5.3 Update callback tests for new priority chain:
  - `SiteTitleCallbackTests`: add `test_unauthenticated_with_default_brand` (returns default brand name, not "clients"), `test_unauthenticated_no_default_brand` (returns "clients"), `test_url_override_returns_brand_name`
  - `SiteIconCallbackTests` / `SiteFaviconCallbackTests`: add `test_returns_default_brand_logo_when_no_user_brand`, `test_url_override_returns_brand_logo`
  - `PrimaryPaletteCssTests`: add `test_returns_default_brand_palette_when_no_user_brand`, `test_url_override_returns_brand_palette`
  - `SiteFaviconCallbackTests`: add test for default brand favicon resolution
- [x] 5.4 `BrandUrlMiddlewareTests` — create new test class:
  - `test_login_page_extracts_brand`: GET `/admin/login/?brand=acme-corp`, verify `request._brand_override` is set
  - `test_non_existent_slug_ignored`: GET `/admin/login/?brand=nonexistent`, verify `request._brand_override` is None
  - `test_non_login_path_ignored`: GET `/admin/`, verify middleware doesn't set `_brand_override`
  - `test_post_login_preserves_branding`: POST `/admin/login/?brand=acme-corp`, verify branding still resolves (form re-render on error)
- [x] 5.5 `BrandAdminTests` — new tests:
  - `test_is_default_visible_in_list_display`: superuser sees is_default column
  - `test_non_superuser_no_brand_admin_access`: non-superuser cannot access BrandAdmin (existing behavior, verify)
- [x] 5.6 `SeedBrandsCommandTests` — update existing tests:
  - `test_creates_default_brand`: after command runs, also verify `Brand.get_or_create_default().is_default is True`
- [x] 5.7 Migration tests — verify back-fill (run against test DB):
  - `test_slug_backfilled_for_existing_brands`: brand with name "Test Brand" gets slug "test-brand" after migration
  - `test_is_default_backfilled_for_default_brand`: the "Default Brand" row gets `is_default=True`
- [x] 5.8 Spec file updates:
  - `openspec/specs/per-user-primary-color/spec.md`: replace stale `core.Profile` references with `core.Brand`; update anonymous scenario to describe default-brand fallback instead of empty/static-palette-only
  - `openspec/specs/unfold-admin-theme/spec.md`: update "Site branding" scenario to document that unauthenticated users with a default brand see that brand's name/icon/colors instead of hardcoded `"clients"`
- [x] 5.9 Login page palette test — new test:
  - `test_selector_has_higher_specificity_than_unfold`: verify `primary_palette_css()` outputs `:root:root` selector (specificity 0,2,0) rather than `:root` (0,1,0)

## 6. Verification

- [x] 6.1 Run existing test suite (`python manage.py test`) — confirm zero regressions (76/76 pass)
- [x] 6.2 Run new migrations forward and backward (`python manage.py migrate core <prev>`) across all 3 migration files — confirm reversibility
- [x] 6.3 Manual smoke test: set `is_default=True` on a brand with logo and color → visit `/admin/login/` → verify default brand shows
- [x] 6.4 Manual smoke test: visit `/admin/login/?brand=<existing-slug>` → verify that brand's identity shows on login page
- [x] 6.5 Manual smoke test: login → verify user.brand takes over after login regardless of what `?brand=` was on login page
- [x] 6.6 Run `seed_brands` — verify default brand has `is_default=True` and slug populated
