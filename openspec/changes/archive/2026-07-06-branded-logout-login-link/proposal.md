## Why

The logout page (branded via `branded-logout`) shows brand colors and palette, but the "Log in again" button links to `/admin/` — which redirects to `/admin/login/?next=/admin/` without a `?brand=` parameter. The brand context is lost across the logout boundary, breaking the branded experience: users who logged out from "testbrand6" land on the default brand's login page instead.

## What Changes

- Add `current_brand_slug` to the `user_palette` context processor (exposes the resolved brand slug in templates)
- Override Unfold's `unfold/helpers/account_links.html` to add `?brand={{ current_brand_slug }}` to the logout form action
- Modify `project/templates/registration/logged_out.html` to change the "Log in again" button from `/admin/` to `/admin/login/?brand=<slug>`
- Extend `BrandUrlMiddleware` to also handle `?brand=` query parameter on the logout path, ensuring `user_palette_css` resolves to the correct brand on the logout page

## Capabilities

### New Capabilities
- `branded-logout-login-link`: The logout page preserves the user's brand through the logout boundary. The logout form action carries the brand slug via query string, and the "Log in again" button links to the branded login page (`/admin/login/?brand=<slug>`). Both the logout page palette AND the redirected login page reflect the same brand.

### Modified Capabilities
- `branded-logout`: The logout page template now passes brand context through the query string. The "Log in again" button targets the branded login URL instead of the bare admin index.

## Impact

- **Modified file**: `utils/context_processors.py` — 1 new context variable (`current_brand_slug`)
- **Modified file**: `utils/middleware.py` — 1 additional path check (logout) in `BrandUrlMiddleware`
- **Modified file**: `project/templates/registration/logged_out.html` — button href change
- **New file**: `project/templates/unfold/helpers/account_links.html` — overrides Unfold's logout form
- No model, view, or dependency changes
