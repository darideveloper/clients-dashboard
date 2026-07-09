## Context

The `create_checkout` view in `ourlives/views.py` generates a `purchase_url` and passes it to Stripe as both `success_url` and `cancel_url`. Stripe then redirects the user's browser to this URL after payment completes or is cancelled.

Currently the URL is built with:
```python
purchase_url = request.build_absolute_uri("/admin/ourlives/appsettings/purchase/")
```

`request.build_absolute_uri()` calls `request.get_host()`, which returns the value of the HTTP `Host` header. When Django is behind a TLS-terminating reverse proxy like portless (dev.sh), nginx, or traefik, the proxy rewrites this header to the internal address (`127.0.0.1:8000`). Additionally, Django sees `http` as the scheme because the connection from proxy to Django is plain HTTP.

The result: Stripe receives `cancel_url = http://127.0.0.1:8000/admin/.../purchase/` and the user's browser ends up on the wrong host after cancelling.

## Goals / Non-Goals

**Goals:**
- Generate correct external `success_url` and `cancel_url` regardless of proxy configuration
- Zero proxy configuration changes (no `USE_X_FORWARDED_HOST`, no proxy header config)
- Single-line change in `ourlives/views.py`

**Non-Goals:**
- Not changing the Stripe session creation logic (`ourlives/stripe.py`)
- Not changing the webhook handler
- Not adding a general URL resolution utility for the entire project
- Not modifying Django middleware or settings

## Decisions

1. **Use `HTTP_REFERER` header instead of `request.build_absolute_uri()`**
   - The `Referer` header is sent by the browser when submitting the form from `https://clients.localhost/admin/ourlives/appsettings/purchase/`. It always contains the correct scheme, host, and path → `https://clients.localhost/admin/ourlives/appsettings/purchase/`.
   - This completely bypasses proxy header rewriting — the value originates from the browser's address bar, not from the proxy's Host header.
   - **Query param handling**: After a successful Stripe redirect, the purchase page URL includes `?session_id=cs_xxx`. If the user makes another purchase, the Referer would include this stale query param. Using `urlparse` to strip query params ensures a clean base URL.
   - Alternatives considered:
     - **`USE_X_FORWARDED_HOST = True` in settings**: Requires Django setting change + proxy-specific X-Forwarded-Host configuration. Does not fix the scheme (HTTP vs HTTPS) without also enabling `SECURE_PROXY_SSL_HEADER`. More config surface, more proxy-dependent.
     - **Reading `settings.HOST`**: Already exists in `.env.dev` as `HOST=https://clients.localhost`. Previous version of the code used this but was changed. It's static and works everywhere, but was already removed — this fix is simpler and more maintainable.
     - **Hardcode the path and return relative URL `/admin/...`**: Stripe requires absolute URLs for redirect. Relative URLs would fail.

2. **Fallback to `request.build_absolute_uri()` when Referer is empty**
   - Some requests (e.g., programmatic API calls, tests, privacy browsers) may not have a `Referer` header. The existing behavior serves as a reasonable fallback, even though it still has the proxy-bug. The fallback only triggers for non-browser callers where URL correctness is less critical.

## Risks / Trade-offs

- **Missing Referer header**: Some privacy-focused browsers/extensions strip the `Referer` header. → Falls back to `request.build_absolute_uri()` which is the current (imperfect) behavior. No regression. The purchase form uses normal `<form method="POST">` (not fetch()), so all major browsers send a Referer for HTTPS→HTTPS form submissions.
- **Referrer-Policy**: If the Django admin or the purchase page sets `<meta name="referrer" content="no-referrer">` or a restrictive `Referrer-Policy` header in the future, the Referer header would be absent. → Low risk (current code doesn't set any referrer policy). If added later, the fallback covers it.
- **Fallback retains original bug**: When Referer is absent, `request.build_absolute_uri()` still produces wrong URL through a proxy. This is acceptable because: (1) all normal browser interactions include Referer, (2) the fallback only covers non-browser callers, (3) the bug existed before this change so there's no regression.