## ADDED Requirements

### Requirement: Interactive demo clean command with per-org prompts
The system SHALL provide `ourlives/management/commands/clean_ourlives_demo.py` runnable as `python manage.py clean_ourlives_demo` with flags `--dry-run` and `--yes`, and SHALL document both commands in `ourlives/docs/demo-clean.md`.

#### Scenario: Preview table before any prompt
- **WHEN** `python manage.py clean_ourlives_demo` runs (any mode)
- **THEN** it prints a preview table with one row per `Demo` organization (rep, #contacts/#addresses/#orders/#items/#codes, combined totals) plus totals and a `Country` count of 249 before prompting or deleting anything

#### Scenario: Run commands are documented in the accurate place
- **WHEN** a developer opens `ourlives/docs/demo-clean.md`
- **THEN** the file contains `python manage.py clean_ourlives_demo`, the `--dry-run` / `--yes` variants, the `d/k/a/q/?` prompt reference, and the safety note

### Requirement: Per-org drill-down with natural identifiers
Each `Demo` organization prompt SHALL list every related row with its identifier: contacts as `email — name (contact_type code)`, addresses as `line1, city`, orders as `order_number — po_number — scans × cost — order type codes — submitted_at`, items as `product name × quantity @ unit_price = line_total`, codes as `code — project — current/max usage % — order`. The prompt SHALL accept `d` (delete), `k` (keep), `a` (delete all remaining), `q` (quit), `?` (help).

#### Scenario: Detailed org prompt
- **WHEN** the cleaner reaches `Demo Full Org`
- **THEN** it shows all its contacts, addresses, orders with items, and codes with the identifiers above before reading one of `d/k/a/q/?`

#### Scenario: Help and quit controls
- **WHEN** the user answers `?` then `q`
- **THEN** a legend is printed, and quitting keeps all not-yet-confirmed groups untouched

### Requirement: Projects and reps prompted after orgs
After all org prompts, the system SHALL prompt once per remaining `Demo` project (showing still-linked code count) and once per remaining `test-` rep (showing order/org counts), with the same `d/k/a/q/?` controls.

#### Scenario: Leftover project and lone rep
- **WHEN** orgs are done and `Demo OurLens Launch` still has codes plus the orderless `test-` rep remains
- **THEN** both are prompted individually and can be kept or deleted independently

### Requirement: FK-safe per-group deletion in scope only
Deletion SHALL happen per group inside its own `transaction.atomic()` in reverse-FK order (codes → items → orders → contacts/addresses → org → project/rep), touching ONLY `Demo `-prefixed orgs/projects, `test-` emails, and their descendants. Lookup tables and handmade rows SHALL never be deleted. `AppSettings.total_tokens` SHALL NOT be modified.

#### Scenario: Scoped deletion preserves real data
- **WHEN** a `Real Org` / `real@company.com` rep exists alongside demo data and the user deletes all Demo groups
- **THEN** the handmade rows still exist, `Country` count stays 249, and no `ProtectedError` is raised

#### Scenario: Dry-run deletes nothing
- **WHEN** `python manage.py clean_ourlives_demo --dry-run` runs
- **THEN** it prints the preview table and exits 0 without prompting and without deleting any row

#### Scenario: Yes-mode deletes all without prompting
- **WHEN** `python manage.py clean_ourlives_demo --yes` runs
- **THEN** all Demo orgs, projects, and `test-` reps are deleted in FK-safe order with a final summary, reading no stdin
