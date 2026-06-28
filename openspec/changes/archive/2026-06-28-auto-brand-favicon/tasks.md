## 1. Brand Model Changes

- [x] 1.1 Add `__init__` to `Brand` — snapshot `self.logo.name` (string, not FieldFile) as `self._original_logo_name`
- [x] 1.2 Add `favicon_url` property — constructs `storage.url(f"brands/brand_{self.pk}/favicon.png")`, guards against `not self.logo or not self.pk`
- [x] 1.3 Add `_generate_favicon()` method: open logo via Pillow, center-crop to square, resize to 32×32 with LANCZOS, **delete old favicon if exists** (critical for `file_overwrite=False` S3 compat), save as PNG to `brands/brand_<pk>/favicon.png` via `self.logo.storage`
- [x] 1.4 Override `save()` — compare `self.logo.name` with `_original_logo_name`, call `_generate_favicon()` on change, let exceptions propagate (D8)
- [x] 1.5 Override `delete()` — delete `favicon.png` from storage before `super().delete()`, log warning on failure (don't block deletion)

## 2. Backfill Management Command

- [x] 2.1 Create `core/management/commands/backfill_brand_favicons.py` that iterates all brands with logos and generates their `favicon.png`

## 3. Favicon Callback

- [x] 3.1 Add `utils/callbacks/site_favicon(request)` that returns `brand.favicon_url` or falls back to `static("favicon.png")`

## 4. Unfold Config Update

- [x] 4.1 Update `UNFOLD["SITE_FAVICONS"]` in `project/settings.py` — change `href` from `lambda request: static("favicon.png")` to `lambda request: site_favicon(request)`

## 5. Tests

- [x] 5.1 `SiteFaviconCallbackTests` — mirror `SiteIconCallbackTests` pattern: unauthenticated, authenticated without brand, authenticated with brand no logo, authenticated with brand with logo
- [x] 5.2 `BrandFaviconGenerationTests` — test favicon generated on logo upload, regenerated on logo replace (verify old favicon deleted, new one at correct path with `file_overwrite=False` semantics), deleted on logo remove, deleted on brand delete
- [x] 5.3 `BrandFaviconImageTests` — verify output is 32×32 PNG, center-cropped from non-square input, uses LANCZOS resampling
- [x] 5.4 `BrandFaviconErrorTests` — verify corrupt image raises exception that propagates through save() and blocks the save

## 6. Verification

- [x] 6.1 Run existing test suite to confirm no regressions
- [x] 6.2 Run `backfill_brand_favicons` management command to generate favicons for any existing brands with logos
- [x] 6.3 Manually verify in browser that admin tab icon reflects per-brand logo
