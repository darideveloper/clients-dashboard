## Why

The admin sidebar already shows per-brand logos via `SITE_ICON` (sourced from `Brand.logo.url`), but the browser tab icon (`SITE_FAVICONS`) is always the same static `favicon.png`. In a multi-tenant setup where admins manage multiple brands, tab icons are indistinguishable — every brand tab shows the same generic icon. Auto-generating a 32×32 favicon from each brand's logo gives admins instant visual brand recognition in their browser tabs.

## What Changes

- **Brand model** gains favicon generation: on logo upload/change, a 32×32 square PNG is auto-generated (center-crop + resize) and stored alongside the logo
- **`utils/callbacks.py`** gains a `site_favicon(request)` callback that resolves `brand.favicon.url` with fallback to `static("favicon.png")`
- **`project/settings.py`** `UNFOLD["SITE_FAVICONS"]` `href` is updated to call the per-brand callback instead of a static lambda
- **Cleanup**: when a brand logo is deleted or the brand itself is deleted, the generated favicon file is removed
- **Storage**: generated favicon uses the same storage backend as the logo (S3 `PublicMediaStorage` in production, local filesystem in dev) — no new storage configuration needed
- **No new user-facing fields**: the favicon is derived automatically, not uploaded separately. No form changes, no migration for new DB columns

## Capabilities

### New Capabilities
- `auto-favicon-generation`: center-crop brand logo to a square, resize to 32×32 PNG, store alongside logo on same storage backend, clean up on logo change/delete

### Modified Capabilities
- `unfold-admin-theme`: `SITE_FAVICONS` is no longer a static `favicon.png` lambda — it uses a per-brand callback; the spec requirement for favicon resolution needs updating
- `brand-management`: the `Brand` model now auto-generates a favicon from its `logo` field; the spec needs a new requirement covering favicon lifecycle

## Impact

| Area | Change |
|------|--------|
| `core/models.py` | `Brand` model: override `save()`, add `delete()` cleanup, favicon generation method |
| `utils/callbacks.py` | New `site_favicon(request)` callback |
| `project/settings.py` | Update `UNFOLD["SITE_FAVICONS"]` `href` |
| `core/tests.py` | New tests: favicon generation, S3 storage, callback resolution, cleanup |
| `requirements.txt` | No new dependencies (Pillow already listed) |
| Storage (S3 / local) | One additional file per brand: `brands/brand_<pk>/favicon.png` (~1 KB) |
| Existing fallback | `static/favicon.png` remains unchanged as the fallback for brands without a logo |
