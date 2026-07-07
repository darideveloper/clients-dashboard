## 1. Context Processor

- [x] 1.1 Add `current_brand_slug` to `utils/context_processors.py` — import `_resolve_brand`, resolve brand, expose `brand.slug` (or empty string if no brand)

## 2. Templates

- [x] 3.1 Modify `project/templates/registration/logged_out.html` — add `{% block content %}` override with the "Log in again" button linking to `/admin/login/?brand={{ current_brand_slug }}` when a brand is resolved, falling back to `/admin/` when not. Uses `{% with %}` wrapper for URL concatenation to avoid Django `add` filter coercion edge cases

## 3. Verification

- [x] 4.1 Verify: authenticated user with brand clicks logout → logout page shows correct brand palette and title (covered by existing `LogoutBrandRenderingTests`)
- [x] 4.2 Verify: "Log in again" button links to `/admin/login/?brand=<slug>` when user has a brand (covered by `test_button_links_to_branded_login_with_user_brand`)
- [x] 4.3 Verify: login page after clicking button shows correct brand (via `?brand=` param) — manually verified; `?brand=` is appended to login URL
- [x] 4.4 Verify: logout and button work correctly without brand (covered by `test_button_falls_back_to_admin_without_brand`)
- [x] 4.5 Run test suite to confirm no regressions — 83/83 pass

## 4. Test Coverage

- [x] 4.1 Add test: button links to branded login when user has a brand (`test_button_links_to_branded_login_with_user_brand`)
- [x] 4.2 Add test: button links to branded login when default brand exists (`test_button_links_to_branded_login_with_default_brand`)
- [x] 4.3 Add test: button falls back to `/admin/` without brand (`test_button_falls_back_to_admin_without_brand`)
- [x] 4.4 Add test: button falls back without any brand or default (`test_no_brand_no_default_falls_back`)

## Design Revision

**Key discovery during implementation:**

Adding `?brand=` to the logout form action URL (task 2.1 + 3.1) causes Django's `LogoutView.post()` to redirect:
`LogoutView` checks `get_success_url() != request.get_full_path()`. With `?brand=` in the query string, the full path differs from the redirect URL, triggering a 302 redirect to `/admin/logout/` (without the query string). The browser then GETs `/admin/logout/` which `admin_view` redirects to login for anonymous users. Result: **the logout page is never rendered**.

**Revised approach:**
- Remove middleware logout-path extension (reverts to login-path only)
- Remove `account_links.html` override — logout form action remains `/admin/logout/` (no redirect)
- Brand identity is preserved by `_brand_cache`: `each_context()` in `AdminSite.logout()` calls `_resolve_brand(request)` **before** `auth_logout()`, caching the brand. The context processor's `current_brand_slug` reads from this cache during template rendering (after `auth_logout()`), so the correct brand slug is available.
- The "Log in again" button uses `current_brand_slug` (not `request.GET.brand`)
