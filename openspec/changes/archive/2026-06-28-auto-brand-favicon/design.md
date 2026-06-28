## Context

The admin sidebar already resolves per-brand logos via `utils.callbacks.site_icon(request)` → `Brand.logo.url`. The browser tab icon (`SITE_FAVICONS`), however, is always the static `favicon.png` for every user regardless of brand. No DB column or user-facing form field is needed — the favicon is derived from the existing logo at save time.

The project uses Pillow (already in requirements.txt), django-storages with S3 (`PublicMediaStorage`) in production, and local filesystem in dev. The favicon must work identically across both.

## Goals / Non-Goals

**Goals:**
- Auto-generate a 32×32 square PNG favicon from `Brand.logo` on upload/change
- Store it on the same storage backend as the logo (S3 or local)
- Clean up when logo is removed or brand is deleted
- Expose via `utils.callbacks.site_favicon(request)` callback
- Wire into `UNFOLD["SITE_FAVICONS"]` for per-brand tab icons
- Zero new dependencies (Pillow is already in)

**Non-Goals:**
- No new DB column on Brand (favicon is derived, not stored as a model field)
- No new user-facing form fields or admin UI changes
- No favicon upload UI (it's auto-derived from the existing logo)
- No multi-resolution ICO generation (32×32 PNG covers all modern browsers)
- No on-the-fly image processing (generated at save time, not request time)

## Decisions

### D1: Pillow + `Brand.save()` override over django-imagekit

**Chosen: Pillow + `Brand.save()` override.**

Alternatives considered:

| Alternative | Why not chosen |
|---|---|
| **django-imagekit `ImageSpecField`** | Adds a new dependency for ~20 lines of Pillow code. `ImageSpecField` is lazy (generates on first access) — cold-start latency on S3. `file_overwrite=False` on `PublicMediaStorage` could conflict with derivative filename hashing. |
| **django-imagekit `ProcessedImageField`** | Requires a DB column (new migration, field management). Overkill for a derived file that needs no querying. |
| **On-the-fly view** | Request-time latency, needs URL routing and caching. Added complexity for no benefit. |
| **Raw logo as favicon (no generation)** | Non-square logos stretch/crop unpredictably by the browser. Large files (multi-MB) downloaded as favicons. Poor visual quality. |

`Brand.save()` override with Pillow is the simplest path: Pillow is already a dep, the code is ~20 lines, no cold-start latency, and full control over the S3 integration.

### D2: Center-crop to square

When the logo is non-square, center-crop to the shortest dimension, then resize to 32×32. This ensures:
- No distortion (aspect ratio preserved)
- No padding/background color needed
- The center of the logo (typically the most visually important region) is preserved

Alternative: "fit within with padding" (adds white/matte background) was rejected because brand logos on white backgrounds would blend into the browser tab.

### D3: Same storage backend, deterministic path

Path: `brands/brand_<pk>/favicon.png` (same directory as the uploaded logo).

Storage: `self.logo.storage` — the exact same storage backend instance used by the logo ImageField. This guarantees:

```
Production (STORAGE_AWS=True):
  <PUBLIC_MEDIA_LOCATION>/brands/brand_42/favicon.png  → S3 via PublicMediaStorage
  CacheControl: max-age=86400, ACL: public-read

Development (STORAGE_AWS=False):
  <MEDIA_ROOT>/brands/brand_42/favicon.png  → local filesystem via FileSystemStorage
```

**Critical: `file_overwrite=False` on `PublicMediaStorage`.** `_generate_favicon()` MUST explicitly delete the old `favicon.png` before saving the new one. Without this, django-storages appends a suffix (`favicon_1.png`) instead of overwriting, while `favicon_url` always points to `favicon.png` — stale favicon continues to be served.

### D4: `__init__` tracking for change detection, string-based comparison

Track the original logo storage path in `Brand.__init__` via `self.logo.name`. Compare `self.logo.name` (string) rather than the FieldFile object — strings are unambiguous, FieldFile `__eq__` can be unreliable with freshly-uploaded temp files.

Alternative: `pre_save` signal + read from DB — rejected because it adds an unnecessary query and signal wiring.

### D5: Favicon URL via `Brand.favicon_url` property

A read-only `@property` on `Brand` constructs the storage URL deterministically. Must guard against `pk=None` (unsaved instance) to avoid `brands/brand_None/favicon.png`:

```python
@property
def favicon_url(self):
    if not self.logo or not self.pk:
        return None
    return self.logo.storage.url(f"brands/brand_{self.pk}/favicon.png")
```

This keeps URL construction in one place (the model) and lets the callback stay thin.

### D6: LANCZOS resampling

`PIL.Image.Resampling.LANCZOS` (or `PIL.Image.LANCZOS` for Pillow < 10) for the 32×32 resize. LANCZOS produces the sharpest results at small sizes compared to BILINEAR or BICUBIC.

### D7: Cleanup on delete via `Brand.delete()` override

Override `Brand.delete()` to delete the favicon file before calling `super().delete()`. This is synchronous and happens within the same transaction context as the DB deletion.

Alternative: `post_delete` signal — rejected because signals are disconnected during bulk operations and test setup/teardown, making cleanup unreliable.

### D8: Generation failure fails the save

If Pillow raises an exception during `_generate_favicon()` (corrupt image, OOM), the exception SHALL propagate up through `save()` to the caller. The admin form will show an error, the DB transaction is rolled back, and no favicon is written. This is preferred over silent failure because:
- An admin who uploads a logo expects both the logo and its derived favicon to work
- Silent failure would silently serve the generic `favicon.png` with no visible feedback
- The logo and favicon are conceptually atomic (one derives from the other)

One exception: if the logo's storage file does not exist (`FileNotFoundError`), the method logs a warning and returns — this handles edge cases where the `logo.name` path points to a file that was moved or deleted outside Django's field lifecycle.

Another exception: `delete()` favicon cleanup (e.g., S3 delete timeout) logs a warning but does not block the Brand deletion.

## Risks / Trade-offs

| Risk | Impact | Mitigation |
|---|---|---|
| **Logo save fails but favicon was partially written** | Orphaned favicon file on storage | Favicon generation happens *after* `super().save()` succeeds. If favicon generation fails (e.g., corrupt image), the exception propagates and the save is rolled back. |
| **S3 latency on favicon URL construction** | `storage.url()` adds ~10-50ms per page load | `storage.url()` does NOT check existence — it's purely URL construction (string concatenation + host prefix). No S3 API call is made. |
| **Brand.pk is 0 (unsaved) during save** | Favicon path becomes `brands/brand_0/favicon.png` | `super().save()` is called first, which assigns the pk. Favicon generation runs after the pk exists. |
| **Data migration for existing brands** | Existing brands with logos have no favicon | Add a `post_migrate` or standalone management command to backfill. Documented in tasks. |
| **Bulk operations bypass save()** | `Brand.objects.bulk_create()` / `bulk_update()` / `QuerySet.update()` skip the save() override | This is acceptable — the admin UI always uses single-object save. Bulk logo changes are not a real usage pattern. If needed, a management command can backfill. |
| **`file_overwrite=False` on PublicMediaStorage — stale favicon if delete-before-save is missed** | Logo replacement creates `favicon_1.png`, URL still points to old `favicon.png` | Design D3 mandates explicit delete-before-save in `_generate_favicon()`. Reviewed in code review. |
| **Generation failure kills the save entirely** | User cannot save a Brand if favicon generation errors | Intentionally accepted (D8). Favicon and logo are atomic. The user sees the error and can retry with a valid image. |
