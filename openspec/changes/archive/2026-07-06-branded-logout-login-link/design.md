## Context

The logout page currently resolves brand identity as follows:

User clicks logout (authenticated, brand: testbrand6)
  |
  v POST /admin/logout/
  | each_context() called -> _resolve_brand() caches brand in _brand_cache
  | auth_logout(request)   <-- flushes session, user becomes AnonymousUser
  |
  v Template renders (logged_out.html)
  |  +-- site_title = "testbrand6" (from each_context extra_context)
  |  +-- _resolve_brand(request) uses _brand_cache -> returns testbrand6
  |  |   -> user_palette_css shows testbrand6 brand palette (matches title)
  |  +-- "Log in again" button: <a href="/admin/">
  |      -> click redirects to /admin/login/?next=/admin/ (no ?brand=)
  |      -> login page shows default brand
  |
  +-- Result: palette and title match, but button links to unbranded login

The logout form (`account_links.html`) POSTs to `/admin/logout/`. The template override (`logged_out.html`) adds palette CSS but the button href is inherited from Unfold's template. No `?brand=` is passed through the logout boundary.

### Key files

| File | Role |
|------|------|
| `utils/context_processors.py` | Provides `user_palette_css` to templates |
| `utils/middleware.py` | `BrandUrlMiddleware` sets `_brand_override` from `?brand=` on login path |
| `utils/callbacks.py` | `_resolve_brand()` resolves brand per request |
| `unfold/templates/registration/logged_out.html` | Unfold's logout template with "Log in again" button |
| `unfold/templates/unfold/helpers/account_links.html` | Logout form (POST action) |
| `project/templates/registration/logged_out.html` | Project's logout template override (adds `user_palette_css`) |

## Goals / Non-Goals

**Goals:**
- "Log in again" button on logout links to branded login: `/admin/login/?brand=<slug>`
- Brand is preserved from authenticated session through the logout boundary
- Both logout page palette AND redirected login page show the same brand
- Minimal code changes: 1 context variable, 1 middleware path, 2 template overrides

**Non-Goals:**
- Not preserving brand across session expiry (only logout -> login flow)
- Not changing Unfold's logout behavior or redirect logic
- Not adding new database queries (brand slug comes from already-resolved brand object)
- Not supporting multi-brand logout (cookie approach would be needed for session expiry)

## Decisions

| Decision | Choice | Rationale |
|---|---|---|
| Brand passthrough mechanism | `_brand_cache` from `each_context()` | `AdminSite.logout()` calls `each_context()` before `auth_logout()`. `_resolve_brand()` caches the result. The context processor reads from cache during template rendering (after logout). No query string, session, or cookie needed |
| Context variable name | `current_brand_slug` | Descriptive, avoids collision with `brand` or `brand_slug` in other contexts |
| Context processor location | `utils/context_processors.py` (existing `user_palette` function) | Already resolves `_resolve_brand(request)` -- no additional DB query. The brand object is already fetched |
| Middleware extension | **Not needed** | `_brand_cache` from `each_context()` preserves the brand. Adding `?brand=` to the logout form action would cause Django's `LogoutView` to redirect (see "Design Revision" below) |
| Account links form override | **Not needed** | POST to `/admin/logout/` (no query string) works without redirect. Brand identity is in context, not query string |
| Button URL target | `admin:login` with `?brand=current_brand_slug` | Direct login link with brand slug from cached brand context |
| Fallback when no brand | Link to `admin:index` (Unfold's default) | Graceful -- login page resolves to default brand via existing `_resolve_brand()` fallback |

### Alternatives considered

**Cookie approach**: Store `last_brand_slug` cookie on admin pages, check in middleware. Rejected for this change because:
- Requires response-middleware to set cookies (more complex)
- Cookie survives session expiry (a feature, but also means brand "sticks" even if user changes context)
- Overkill for the specific logout-to-login flow

**Session approach**: Store brand in session before `auth_logout()`. Rejected because `auth_logout()` calls `request.session.flush()`, wiping all session data.

**Query string approach**: Add `?brand=` to the logout form action so the brand passes through the POST boundary. **Rejected during implementation** because Django's `LogoutView.post()` redirects when `get_full_path()` differs from `get_success_url()`. The query string causes the paths to differ, triggering a 302 redirect that strips the brand context. See "Design Revision" below.

## Template chains

### Logout page override
```
logged_out.html (project override)     <-- extrastyle block + content block override (duplicates layout, changes button URL)
  -> registration/logged_out.html (Unfold)
    -> unfold/layouts/unauthenticated.html
      -> unfold/layouts/skeleton.html
```

## Risks / Trade-offs

| Risk | Mitigation |
|------|-----------|
| `logged_out.html` content block duplicates Unfold's entire logout layout HTML | Override must duplicate `<h1>`, `<p>`, and button component with all Tailwind classes from Unfold's template. If Unfold changes the heading text, paragraph, or layout classes in a future version, the project override renders stale HTML. Minimized by copying the complete block from the current Unfold template and pinning Unfold version |
| Brand slug in URL is user-modifiable | `BrandUrlMiddleware` already handles invalid slugs (catches `Brand.DoesNotExist`). No injection risk |
| Context processor adds `current_brand_slug` to every request context | Minimal overhead -- `_resolve_brand()` already called; `.slug` is a model field access, no extra query |
| `add` filter in template URL concatenation is fragile | Django's `add` filter tries numeric coercion before string concatenation. Works correctly for brand slugs (non-numeric strings like `testbrand6`), but would break if a slug were purely numeric. Use `{% with branded_url=login_page|add:"?brand="|add:current_brand_slug %}` wrapper for clarity and to isolate the concatenation from the component tag |

## Design Revision

During implementation (2026-07-06), the original design was revised after discovering that Django's `LogoutView.post()` has a POST/redirect/GET pattern:

1. **Orginal plan**: Add `?brand={{ current_brand_slug }}` to the logout form action in `account_links.html`, extend `BrandUrlMiddleware` to handle the logout path, and use `request.GET.brand` in the "Log in again" button URL.
2. **Problem**: `LogoutView.post()` at line 139 of `django/contrib/auth/views.py`:
   ```python
   def post(self, request, *args, **kwargs):
       auth_logout(request)
       redirect_to = self.get_success_url()
       if redirect_to != request.get_full_path():
           return HttpResponseRedirect(redirect_to)
       return super().get(request, *args, **kwargs)
   ```
   When `?brand=` is appended to the form action URL, `request.get_full_path()` returns `/admin/logout/?brand=testbrand6` while `get_success_url()` returns `/admin/logout/`. They differ, triggering a 302 redirect. The browser then GETs `/admin/logout/` without `?brand=`, and `admin_view` redirects anonymous users to login. **The logout page is never rendered.**
3. **Resolution**: Remove the `?brand=` from the form action. Instead, rely on `_brand_cache`: `AdminSite.logout()` calls `self.each_context(request)` BEFORE `auth_logout()`, which triggers `_resolve_brand()` and caches the result in `request._brand_cache`. The `user_palette` context processor reads from this cache during template rendering, so `current_brand_slug` reflects the user's brand even after logout. The "Log in again" button uses `current_brand_slug` directly, without needing a query string parameter.
