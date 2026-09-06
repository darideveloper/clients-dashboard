## 1. Fixture loaders

- [x] 1.1 Create `core/management/commands/base_loaddata.py` verbatim from `django-fixtures.md` §5 (auto-discovery via `apps.get_app_configs()`, sorted `*.json`, `call_command("loaddata", f"{label}/{name}")`, per-fixture `try/except`)
- [x] 1.2 Create `core/management/commands/seed_loaddata.py` verbatim from `django-fixtures.md` §5 (includes `_sync_seed_media` for `seed/images/` to `default_storage`)
- [x] 1.3 Verify both commands `--help` and a dry run on an empty `core/fixtures/` scans without error

## 2. Default Brand base fixture

- [x] 2.1 Create `core/fixtures/core/Brand.json` with `pk=1`, `name="Default Brand"`, `slug="default-brand"`, `is_default=true`, `primary_color="#C92FFF"` (explicit slug because `loaddata` skips `save()`)
- [x] 2.2 Run `python manage.py migrate && python manage.py base_loaddata` on a fresh DB and verify the row exists via `Brand.objects.get(pk=1)`; re-running `base_loaddata` leaves a single row (idempotent)
- [x] 2.3 Add/adjust a test that `base_loaddata` creates the expected Brand (or assert `loaddata` output) and that `--help` succeeds

## 3. Adapt seed_brands → backfill_brand_files

- [x] 3.1 Create `core/management/commands/backfill_brand_files.py` slimmed from `seed_brands.py` (Membership backfill + logo file moves `avatars/user_<id>/` ↔ `brands/brand_<pk>/`, `--reverse`, fail-loud if Default Brand row missing instead of `get_or_create_default()`)
- [x] 3.2 Delete `core/management/commands/seed_brands.py`
- [x] 3.3 Update `core/tests.py`: Default Brand provisioning tests → `call_command("base_loaddata")`; Membership backfill and file-move tests → `call_command("backfill_brand_files")` (replacing `call_command("seed_brands")`); adjust assertions for fail-loud behavior when the Default Brand fixture is missing
- [x] 3.4 Run `python manage.py test core` and verify all Brand/Membership/file-move tests pass; verify `--reverse` best-effort still works

## 4. Wire base_loaddata into deploy

- [x] 4.1 Edit `start.sh` to run `python manage.py base_loaddata` after `migrate` (before `exec gunicorn`), preserving `set -e`
- [x] 4.2 Verify `start.sh` content matches `production-deploy` spec (makemigrations + migrate + base_loaddata + gunicorn) and that `shellcheck`/dry-run shows no breakage
