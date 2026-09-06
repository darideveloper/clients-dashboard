## Why

No portable pattern exists for loading fixed reference data, yet every new lookup table (CRM Phase 1: Country, ContactType, CodeType, OrderType) and the existing `Brand` system need deterministic base rows in every environment. The reusable `base_loaddata`/`seed_loaddata` fixture pattern (`/home/daridev/Desktop/obsidian/daridev/20-areas/work/django/django-fixtures.md`) solves this centrally; porting it now makes Phase 1 fixtures and all future apps trivial to add and decouples the legacy `seed_brands` one-shot into a proper base fixture + a focused backfill command.

## What Changes

- Port `core/management/commands/base_loaddata.py` and `core/management/commands/seed_loaddata.py` verbatim from the fixtures doc (auto-discovery via `apps.get_app_configs()`, `call_command("loaddata", f"{label}/{fixture}")`, per-fixture `try/except`, sorted load, seed media sync). Both loaders are added even though only base-tier data exists in this change.
- Add `core/fixtures/core/Brand.json` base fixture for the Default Brand (`pk=1`, `name="Default Brand"`, `slug="default-brand"` explicit because `loaddata` skips `save()`, `is_default=true`, `primary_color="#C92FFF"`, no logo).
- **BREAKING (rename):** Replace `core/management/commands/seed_brands.py` with `core/management/commands/backfill_brand_files.py` — slimmed to Membership backfill (users without a brand) + logo file relocation (`avatars/user_<id>/` ↔ `brands/brand_<pk>/`) with `--reverse`; Default Brand creation removed (now owned by the fixture). Command fails loudly if the fixture row is missing, enforcing `base_loaddata` first.
- Update `start.sh` to run `python manage.py base_loaddata` after `migrate` on every container start (per doc §7).
- No `FIXTURE_DIRS` setting (Django discovers `<app>/fixtures/` by default; doc marks it optional). No `Rep`/seed-tier fixtures in this change.

## Capabilities

### New Capabilities

- `fixture-system`: portable fixture infrastructure — two auto-discovering loader commands in `core`, base vs seed tier lifecycle, and the Default Brand base fixture.

### Modified Capabilities

- `brand-management`: `seed_brands` mechanism replaced by base fixture + `backfill_brand_files` (file relocation + Membership backfill); fail-loud ordering.
- `production-deploy`: `start.sh` contract extended to run `base_loaddata` after `migrate`.

## Impact

- Affected code: `core/management/commands/` (+2 new, 1 renamed/deleted), `core/fixtures/core/Brand.json` (new), `core/tests.py` (command-name references), `start.sh` (one line), `openspec/specs/brand-management` + `openspec/specs/production-deploy` (deltas).
- No new dependencies; no schema migration (fixture load is idempotent via `loaddata` PK matching, re-runs update in place).
- Future Phase 1 fixtures (`ourlives/fixtures/ourlives/*.json`) and any new app's fixtures require zero loader edits — drop the JSON and `base_loaddata` picks it up.
