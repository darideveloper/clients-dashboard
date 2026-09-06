## Context

The repo has no portable fixture infrastructure yet. The reusable pattern (`django-fixtures.md`) — `core/base_loaddata` + `core/seed_loaddata` auto-discovering `<app>/fixtures/<app>/*.json` via `apps.get_app_configs()` — is documented but unported. `core/seed_brands.py` is a bespoke one-shot (Default Brand creation + Membership backfill + logo file moves) that mixes responsibilities now better split across the fixture tiers. `start.sh` and the `production-deploy` spec currently mandate only `makemigrations` + `migrate` + gunicorn, with no fixture loading. Phase 1 CRM lookups will be the first consumer; Brand is the pilot row to prove the pattern.

## Goals / Non-Goals

**Goals:**
- Port the doc's two-loader fixture system so any app adds base/seed data by dropping JSON — zero loader edits.
- Split `seed_brands` into a base fixture (Default Brand row) + a focused command (`backfill_brand_files`) for the runtime-dependent jobs.
- Wire `base_loaddata` into `start.sh` after `migrate` so reference data is present on every deploy and test.

**Non-Goals:**
- No `FIXTURE_DIRS` setting (doc says optional; Django discovers `<app>/fixtures/` already).
- No seed-tier fixtures in this change (infrastructure only; content comes later).
- No schema changes; no changes to `backfill_brand_favicons` or `Brand.get_or_create_default()` callers beyond the split.
- No Phase 1 CRM fixtures here (those belong to `add-crm-phase1-lookups`).

## Decisions

1. **Port both loaders verbatim from the doc, in `core`.** `base_loaddata` discovers `<app>/fixtures/<app>/*.json`; `seed_loaddata` discovers `<app>/fixtures/<app>/seed/*.json` and syncs `seed/images/` to `default_storage`. Both live in `core` (the doc's "main project app") so every domain app can add fixtures without owning loader code. Alternative (per-app loaders) rejected: O(n) loaders, list maintenance.
2. **Default Brand row becomes a base fixture** (`core/fixtures/core/Brand.json`, `pk=1`, explicit `slug="default-brand"`, `is_default=true`, `primary_color="#C92FFF"`, no logo). `loaddata` bypasses `save()`, so `slug` must be explicit — `save()` never runs. PK `1` is conventional for the singleton default; `get_or_create_default()` already keys on `name`, so existing code tolerates any PK.
3. **Slimmed command renamed to `backfill_brand_files`.** Keeps Membership backfill (users without `Membership` → Default Brand) + logo file moves (`avatars/user_<id>/` ↔ `brands/brand_<pk>/`) + `--reverse` best-effort. Default Brand creation removed (owned by the fixture). Name `backfill_brand_files` reflects the lasting job; matches the explored gap 1:1.
4. **Fail-loud on missing fixture.** If the Default Brand row is absent, the command errors instead of `get_or_create_default()`. Enforces `base_loaddata` first and preserves the fixture as the single source of truth. Alternative (silent fallback) rejected: hides the ordering bug.
5. **`start.sh` + `production-deploy` spec delta in this change.** Base fixtures must load on every container start. Updating the spec alongside `start.sh` keeps implementation tracked; deferring would ship untracked deploy behavior.
6. **No deletion of `Brand.get_or_create_default()`.** Still used by `UserAdmin.save_model`, middleware callbacks, and Excel helpers — the fixture row satisfies it idempotently; admin path still works when fixtures precede user creation.

## Risks / Trade-offs

- [Risk] `Brand.json` `slug` drifts from `slugify("Default Brand")` → Mitigation: use the canonical slugify output `"default-brand"` and add a test that asserts `loaddata` produces the expected slug.
- [Risk] Loader fail-soft (`try/except` + continue) silently hides bad fixtures → Mitigation: CI test runs `base_loaddata` and asserts expected rows exist; entrypoint stays fail-soft so one bad fixture doesn't block deploy.
- [Risk] Container start ordering — `base_loaddata` after `migrate` assumes DB is reachable → Mitigation: matches doc §7; `start.sh` already `set -e`, and `loaddata` re-runs update rows in place (idempotent).
- [Risk] Old `seed_brands` callers (scripts, docs) break on rename → Mitigation: breaking change is explicit in proposal; `seed_brands` is removed, not shimmed — YAGNI.
