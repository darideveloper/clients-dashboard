## Why

Seeded demo data (`seed_ourlives_demo`) currently has no safe removal path: deleting `Demo ` / `test-` rows by hand in shell or admin risks `ProtectedError` violations (wrong FK order), accidental deletion of real rows (wrong filter), or silently leaving orphans. This is most dangerous on prod, where a typo can destroy real sales data.

## What Changes

- New management command `clean_ourlives_demo` (stdlib-only, no new dependencies) that interactively audits and removes demo data:
  - Scans with the exact same `Demo ` / `test-` querysets the seed uses (single source of truth, cannot drift).
  - Prints a preview table (full breakdown per org: rep, #contacts/#addresses/#orders/#items/#codes, combined totals) plus untouched-lookup confirmation (`Country` 249).
  - Prompts **per Demo org** showing every related row with its natural identifier (contact email + name + type, address line1/city, order number + PO + totals + types + date, item product × qty @ price, code + project + usage %), then `(d)elete / (k)eep / (a)ll remaining / (q)uit / (?)help`.
  - After orgs, prompts separately for each remaining `Demo` project and each `test-` rep.
  - Deletes each group inside its own `transaction.atomic()` in strict FK-safe order (codes → items → orders → contacts/addresses → org → project/rep).
  - Flags: `--dry-run` (preview only, no prompts/deletes), `--yes` (delete all Demo groups without prompting).
  - Leaves `AppSettings.total_tokens` untouched (freeing happens automatically via `tokens_available = total − assigned`); no prod ENV guard (same flow local and prod, per scope decision).
- Tests mirroring `tests_seed_demo.py` (dry-run counts, `--yes` deletes, handmade rows survive, lookups intact).
- Docs alongside `ourlives/docs/demo-seed.md`.

## Capabilities

### New Capabilities
- `demo-clean`: interactive per-org audit and FK-safe removal of seeded `ourlives` demo data with dry-run and non-interactive modes.

### Modified Capabilities
- None. No existing spec behavior changes; `demo-seed` keeps its requirements (the cleaner reuses its scope definitions).

## Impact

- New file `ourlives/management/commands/clean_ourlives_demo.py` (+ tests in `ourlives/tests_clean_demo.py` or alongside seed tests); reuses seed scope constants and model validation.
- Docs: one added doc under `ourlives/docs/` (next to `demo-seed.md`) with the run commands and prompt reference.
- No model/migration changes, no new dependencies, no admin changes. Safe on prod by construction (scoped querysets, per-group atomic, dry-run default preview).
