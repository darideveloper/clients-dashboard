## 1. Callbacks — Add site title resolvers to utils/callbacks.py

- [x] 1.1 Add module-level fallback constants (`FALLBACK_TITLE`, `FALLBACK_HEADER`, `FALLBACK_SUBHEADER`) set to the current hardcoded strings
- [x] 1.2 Add `_resolve_brand_name(request)` shared helper that extracts `request.user.brand.name` or returns `None`
- [x] 1.3 Add `site_title(request)` callback — returns `name` or `FALLBACK_TITLE`
- [x] 1.4 Add `site_header(request)` callback — returns `name` or `FALLBACK_HEADER`
- [x] 1.5 Add `site_subheader(request)` callback — returns `"Dashboard"`

## 2. Config — Wire lambdas in UNFOLD dict

- [x] 2.1 Import the three new callbacks in `project/settings.py`
- [x] 2.2 Change `SITE_TITLE` from static string to `lambda request: site_title(request)`
- [x] 2.3 Change `SITE_HEADER` from static string to `lambda request: site_header(request)`
- [x] 2.4 Change `SITE_SUBHEADER` from static string to `lambda request: site_subheader(request)`
- [x] 2.5 Verified by test `test_unauthenticated_returns_fallback_title` — same callback, same code path
- [x] 2.6 Run existing tests to confirm no regressions

## 3. Tests — Add callback test cases

- [x] 3.1 Add `SiteTitleCallbackTests` class following `SiteIconCallbackTests` pattern with test cases:
    - unauthenticated returns fallback title
    - authenticated no brand returns fallback title
    - authenticated with brand returns `brand.name`
    - authenticated with brand returns `"Dashboard"` for subheader
    - default brand renders its name
- [x] 3.2 Import `site_title`, `site_header`, `site_subheader` in test imports
- [x] 3.3 Run full test suite and confirm all pass

## 4. Archive — Finalize spec updates

- [x] 4.1 Archive via `/opsx-archive` when ready (no `tidy` command — archive merges delta specs into live specs)
