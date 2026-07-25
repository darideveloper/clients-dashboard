## Context

The `api_key` field was added to `AppSettings` in a previous change but is not needed — the intended external service doesn't require a per-instance API key. The field is unused in any code path. It should be removed cleanly while preserving the `storage_base_url` field.

Current state of affected files:
- `ourlives/models.py:169-173` — `api_key` field definition
- `ourlives/admin.py:68` — `"api_key"` in "API Configuration" fieldset
- `ourlives/admin.py:90` — `"api_key"` in `get_readonly_fields`
- `ourlives/tests.py:898,905` — `api_key` assertions in `AppSettingsAdminTests`
- `openspec/specs/admin-managed-settings/spec.md` — references `api_key` in 2 requirements

## Goals / Non-Goals

**Goals:**
- Remove `api_key` field from the model, admin, and tests
- Generate a new Django migration to drop the column
- Update the `admin-managed-settings` spec to remove `api_key` references

**Non-Goals:**
- No changes to `storage_base_url` or its behavior
- No migration squash or cleanup of old migration files

## Decisions

| Decision | Choice | Rationale |
|---|---|---|
| Migration approach | New migration via `makemigrations` (not manual SQL or squash) | Follows existing project pattern; `api_key` was never deployed to prod; clean auto-generated removal |
| Migration file handling | Keep `0007` as-is (committed), generate `0008` as removal | User explicitly said "don't touch the migration files" |

## Risks / Trade-offs

- **Migration 0007 adds api_key, 0008 removes it** — Leaves a brief migration artifact where the column exists then is dropped. Minor cosmetic issue, no runtime impact.
