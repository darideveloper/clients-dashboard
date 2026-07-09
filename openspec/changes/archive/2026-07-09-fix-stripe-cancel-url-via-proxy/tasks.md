## 1. Fix URL Resolution in create_checkout View

- [x] 1.1 Replace `request.build_absolute_uri()` with `request.META.get("HTTP_REFERER")` + `urlparse` fallback in `ourlives/views.py:59` (strip query params from Referer with `urlparse`)
- [x] 1.2 Add `from urllib.parse import urlparse` to imports
- [x] 1.3 Run existing test suite to confirm no regressions
- [x] 1.4 Verify manually that `referer` from `https://clients.localhost` produces correct external URLs