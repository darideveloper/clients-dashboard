## Why

In production the browser tab icon rendered as a red square for every brand, while the per-brand sidebar logo rendered correctly. The confirmed root cause was **test pollution, not a missing file**: a test-suite run with `STORAGE_AWS=True` and prod bucket credentials executed the favicon tests, whose helper builds solid-red `(255,0,0)` logos; test brands take pks 1, 2, … in the throwaway test DB, so `_generate_favicon` overwrote the real prod keys `brands/brand_<pk>/favicon.png` with red squares. Proven by triple md5 match (`b0557c08…`): both prod objects, the local test-generated file, and an in-memory replay of the pipeline. `settings.STORAGES` honors `STORAGE_AWS` even under `IS_TESTING`, so nothing stopped the suite from writing to the prod bucket. Repair (backfill + CDN edge-cache purge — the purge proved necessary) is confirmed working by the user.

## What Changes

- `site_favicon()` verifies the generated `favicon.png` actually exists in storage before returning its URL, and falls back to `static("favicon.png")` when it does not — defense in depth against dead URLs (shipped; not the active cause, since the prod files existed).
- Repair: `backfill_brand_favicons` against production regenerated the real per-brand icons, plus a CDN edge-cache purge (corrected bytes stayed hidden behind the cached red until purged).
- Deploy gap closed: `backfill_brand_favicons` runs as part of container startup (`start.sh`) after `base_loaddata`, so future deploys self-heal favicon content.
- Prod verification: tab icon confirmed working per brand after the purge.

## Capabilities

### New Capabilities

- None — no new user-facing capability; this restores the behavior already promised by `auto-favicon-generation`.

### Modified Capabilities

- `auto-favicon-generation`: the favicon callback requirement gains an existence guard (brand logo present but generated file missing → static fallback instead of a dead URL).
- `production-deploy`: the start-script requirement gains the favicon backfill step so missing favicons are regenerated on every deploy.

## Impact

- Code: `utils/callbacks.py` (`site_favicon`) and `start.sh`. `core/models.py` untouched — `favicon_url` stays a pure URL builder per design D1.
- Ops: one `backfill_brand_favicons` run in prod (done) plus one CDN edge-cache purge (done, proved necessary); one extra storage existence check per admin page load (S3 HEAD) unless cached — performance tradeoff documented in design.
- No API, schema, or fixture changes. No breaking changes. Sidebar logo path (`site_icon`) untouched.
- Explicit follow-up, NOT in this change: isolate test storage (force local `STORAGES` when `IS_TESTING`) so no future test run with leaked prod env can clobber prod media again — the root-cause fix for the pollution vector.
