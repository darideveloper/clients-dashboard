## Context

Per-brand admin branding resolves through `utils.callbacks`: `site_icon()` serves `logo.url` for the sidebar (working in prod), while `site_favicon()` serves `brand.favicon_url` for the browser tab (broken in prod — red/broken square on every brand). Both URLs come from the same `PublicMediaStorage`, so bucket config, ACLs, and URL signing are exonerated: the sidebar proves the storage path works.

The favicon object lifecycle has two writers and one blind reader:

- Writers: `Brand.save()` (logo-change detection → `_generate_favicon()`) and the `backfill_brand_favicons` management command.
- Reader: `Brand.favicon_url` builds `storage.url("brands/brand_<pk>/favicon.png")` guarded only by `has_logo`/`pk` — it never checks the object exists.
- Deploy: `start.sh` runs `migrate` + `base_loaddata` only. It never runs `backfill_brand_favicons`. `loaddata` bypasses `save()`, so any logo arriving outside an admin upload never gets a favicon.

So any brand whose logo predates the auto-favicon feature (or arrived via fixtures/imports) has `has_logo == True` with no `favicon.png` in S3, and every admin page serves `<link rel="icon" href="<dead S3 key>">`. Initial hypothesis was a 404/403 on a missing key — **disproven during implementation**: both prod keys returned 200 with solid-red bytes (test pollution, see Resolved Questions). The existence guard shipped anyway as defense in depth; the backfill + CDN purge was the actual repair.

## Goals / Non-Goals

**Goals:**
- The tab icon never points at a nonexistent storage object (graceful static fallback instead).
- Every prod brand with a logo actually has a `favicon.png` (one-time repair + self-healing deploys).
- Verify the fix in prod, accounting for the documented cache windows.

**Non-Goals:**
- No change to favicon generation quality, size, format, or the sidebar logo path.
- No new caching layer, CDN invalidation, or querystring versioning (only document the existing cache behavior).
- No fix for the `brand_None` first-upload path (real but unrelated to this symptom; separate change if wanted).
- No broadening of `_generate_favicon` exception handling (out of scope; failures there surface as admin errors, not silent red squares).

## Decisions

### D1: Guard the serving path (`site_favicon`), not the model property (`favicon_url`)
`site_favicon()` will check `storage.exists("brands/brand_<pk>/favicon.png")` via the brand's logo storage before returning `favicon_url`, falling back to `static("favicon.png")` when absent. `favicon_url` stays a pure URL builder.
- Why here: one caller exists today (`SITE_FAVICONS` href); guarding at the single serving path is the smallest diff with the smallest blast radius. Turning `favicon_url` into an I/O call changes the semantics of a property other code (and tests) treats as a cheap builder.
- Alternative considered: guard inside `favicon_url` (returns `None` when missing) — fixes all future callers at once. Rejected for now per YAGNI: no other callers exist; revisit if a second consumer appears.

### D2: Accept one storage existence check per admin page render
`site_favicon` runs once per Unfold `each_context` (one admin page load = one check; an S3 `HEAD`). This is negligible next to the page's own queries.
- Alternative considered: memoize the resolved URL on `request` next to `_brand_cache`. Rejected initially — one HEAD per page load needs no invalidation logic; add memoization only if request latency measurements justify it.

### D3: Wire the existing backfill command into `start.sh`, unchanged
Append `python manage.py backfill_brand_favicons` after `base_loaddata` in `start.sh`. The command is already idempotent (regenerates all favicons for brands with logos, skips the rest) and — critically for `set -e` — never exits nonzero: per-brand failures are caught, reported to stderr, and the command exits 0, so a single bad logo can never block gunicorn startup.
- Alternative considered: `--missing-only` flag to skip existing favicons. Rejected: with a handful of brands the full regen costs seconds at startup; the flag is added only if brand count or startup time makes it necessary (`# ponytail:` ceiling note at the call site).

### D4: Repair prod with the same command, then verify at HTTP level
One-time `backfill_brand_favicons` run in prod (happens automatically on next deploy via D3; or run manually first for immediate relief). Verification is HTTP-level, not code-level: `curl -I` the tab href per brand → expect `200` + `image/png`; download and confirm 32×32 PNG pixels matching the logo (rules out the alternate "file exists but red" hypothesis retroactively).
- Cache caveat (not a code change): S3 objects carry `CacheControl: max-age=86400` and browsers pin favicons aggressively — the fixed icon may take up to ~24h (or a hard refresh) to appear everywhere. Document, don't engineer around it.

## Risks / Trade-offs

- [Pre-implementation assumption wrong] → Mitigation: the `curl -I` probe in tasks phase 0 decides everything. Dead key (403/404) confirms this design. `200` with red pixels pivots the change toward the generation path instead — do not implement blindly.
- [Regen rewrites every favicon on each deploy] → Mitigation: harmless (same bytes, refreshed cache age); cost scales with brand count (currently trivial). Ceiling noted for future `--missing-only`.
- [Tiny delete-then-save window during regen serves fallback] → Mitigation: with D1 in place, a concurrent request during regeneration falls back to the static icon for one load — strictly better than today's dead URL.
- [Guard live before backfill completes shows fallback, not brand icon] → Mitigation: both ship in the same deploy (`start.sh` ordering). Do not verify per-brand icons until phase 4 — an indigo fallback tab before the backfill runs is expected, not a failure.
- [`storage.exists` on S3 adds a HEAD per page load] → Mitigation: accepted per D2; measurable and reversible.

## Migration Plan

1. Deploy: `start.sh` runs `migrate` → `base_loaddata` → `backfill_brand_favicons` → gunicorn. No schema migration involved (code + script only).
2. Verify per D4 (href status, PNG pixels, per brand).
3. Rollback: revert the commit; generated `favicon.png` objects remain in S3 and are harmless (the old code serves them as before). No data-loss path in either direction.

## Resolved Questions

1. ~~Does the prod favicon href return 403/404 or 200-with-red-bytes?~~ **Answered: 200 + `image/png`, solid `(255,0,0)`, identical etags on both brands.** Triple md5 match (`b0557c08…` on both prod objects, the local test-generated file, and an in-memory pipeline replay) proved test pollution: a suite run with `STORAGE_AWS=True` + prod creds let favicon tests overwrite the real keys. Repair was backfill + CDN edge-cache purge — the purge proved necessary (fresh bytes stayed hidden behind cached red). Remaining root-cause fix (force local `STORAGES` under `IS_TESTING`) is tracked as a separate follow-up, not this change.
2. Guard placement is decided as `site_favicon` (D1) — flag during review if a second `favicon_url` consumer is planned, which would flip the decision.
