## Context

The `ourlives` app has `Project`, `InvitationCode`, and `AppSettings` models. There is no existing mechanism to bulk-import invitation codes from external sources. The `ourlives` app has no existing management commands. The project follows a pattern in `core/management/commands/` (`seed_brands`, `backfill_brand_favicons`): `BaseCommand` with `add_arguments`, a `handle` method, and idempotent logic. The new command will follow this same pattern but live in the `ourlives` app since it operates exclusively on `ourlives` models.

The `InvitationCode.save()` method enforces a token pool ceiling (`sum of all max_use ≤ AppSettings.total_tokens`) using `select_for_update` under a transaction. This constraint complicates bulk inserts because `bulk_create` skips `save()` entirely.

## Goals / Non-Goals

**Goals:**
- Import invitation codes from a CSV into a target project via a single CLI command
- Handle the token pool constraint automatically (bump `total_tokens` when needed)
- Validate all rows before touching the database
- Overwrite existing codes by code value
- Follow existing command patterns (`seed_brands.py`) for consistency

**Non-Goals:**
- CSV export
- Updating `current_use` on existing codes during import
- Multi-project import in one run
- GUI or admin integration

## Decisions

### Decision 1: `bulk_create` + fallback to `update_or_create` per-row

**Choice**: Pre-validate, attempt `bulk_create`. If `IntegrityError` on unique constraint (pre-existing codes), fall back to per-row `update_or_create`.

**Alternatives considered**:
- *Pure `bulk_create`*: Fails if any code already exists—cannot handle overwrites.
- *Pure per-row `create`/`update_or_create`*: Each row calls `save()`, which runs `full_clean()` and the token pool check inside a transaction per row. This is slow (42 transactions vs 1) and the per-row token check would fail once the pool is exhausted—we'd need to bump `total_tokens` between rows, fighting the `select_for_update` lock.
- *Pure `bulk_create` + delete-and-recreate*: Race condition risk. Overkill for 42 rows.

**Rationale**: `bulk_create` is the fast path for the common case (all-new codes). The fallback handles the edge case cleanly without deleting data.

### Decision 2: Upfront validation layer

**Choice**: Validate everything before any database write:
1. CSV file readable, has required columns (`code`, `max_use_rate`, `current_use_rate`, `is_active`)
2. Project exists by name
3. Every row: `current_use_rate ≤ max_use_rate` (avoids DB `CheckConstraint` violation)
4. Every row: `max_use_rate` is a positive integer, `is_active` is truthy/falsy, `code` is non-empty
5. Total `max_use_rate` sum across CSV rows

**Rationale**: Fail fast with clear messages. Don't leave the database in a partially-imported state.

### Decision 3: Auto-bump `total_tokens`

**Choice**: Calculate `required_tokens = sum(max_use_rate)` from CSV. If `AppSettings.total_tokens < required_tokens`, set it to `required_tokens` before importing.

**Alternatives considered**:
- *Report deficit and exit*: Simpler, but forces a manual step. User explicitly chose auto-bump.
- *Bump per-row*: Would need to fight the `select_for_update` lock in `save()`—complex and fragile.

**Rationale**: Bumping before `bulk_create` is a single atomic operation. The constraint in `AppSettings.clean()` already ensures `total_tokens` can't go *below* assigned tokens, but there's no ceiling—bumping up is always safe.

### Decision 4: CSV column mapping

CSV uses `max_use_rate` and `current_use_rate`, but the model uses `max_use` and `current_use`. The command explicitly maps these rather than relying on header-to-field matching.

### Decision 5: Placement in `ourlives/management/commands/`

**Choice**: `ourlives/management/commands/import_invitation_codes.py`

**Rationale**: The command operates exclusively on `ourlives` models (`Project`, `InvitationCode`, `AppSettings`). Co-locating it with the models it manages follows Django conventions and keeps the `ourlives` app self-contained. The `core` app has no dependency on `ourlives` and adding one would create unwanted coupling.

## Risks / Trade-offs

| Risk | Mitigation |
|---|---|
| `bulk_create` has no model `signals` | No signals are attached to `InvitationCode`, so this is safe |
| `bulk_create` doesn't call `full_clean()` | Frontend validation replicates the relevant checks (token sum, current ≤ max). DB constraints (`CheckConstraint`, unique) still enforced |
| `total_tokens` auto-bump is a side effect | Command prints what it changed so the operator is aware |
| Large CSV could exceed `total_tokens` significantly | Warn the operator if bump > 2x current value, but proceed |
