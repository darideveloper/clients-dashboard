## 1. Command scaffold

- [x] 1.1 Create `ourlives/management/commands/clean_ourlives_demo.py` with `BaseCommand`, flags `--dry-run/--yes`, stdlib-only (`input()`, no new dependencies)
- [x] 1.2 Implement seed-scope querysets (`Demo ` orgs/projects, `test-` reps, descendants via Demo orgs) reusing the seed's scope; refuse to run non-interactively without `--yes`/`--dry-run` (non-tty guard)
- [x] 1.3 Implement preview table (per-org: rep, #contacts/#addresses/#orders/#items/#codes, combined totals + grand totals + `Country` count) printed before any prompt or delete

## 2. Interactive prompts

- [x] 2.1 Implement per-org drill-down block (contact email+name+type, address line1/city, order number+PO+totals+types+date, item product×qty@price, code+project+usage%+order) with `d/k/a/q/?` loop (`?` legend, `a` deletes rest, `q` quits cleanly)
- [x] 2.2 Implement post-org prompts: one per remaining `Demo` project (linked code count) and one per remaining `test-` rep (order/org counts, handmade-org warning), same controls

## 3. FK-safe deletion

- [x] 3.1 Delete each confirmed group in its own `transaction.atomic()` in reverse-FK order (codes → items → orders → contacts/addresses → org → project/rep); never touch lookups, handmade rows, or `AppSettings.total_tokens`
- [x] 3.2 Wire `--dry-run` (preview only, exit 0, no stdin) and `--yes` (delete all Demo groups, final summary, no stdin)
- [x] 3.3 Run `python manage.py seed_ourlives_demo --seed 42` then `python manage.py clean_ourlives_demo --dry-run` and `--yes` on a dev DB; verify counts, `Country==249`, pool freed via `tokens_available`

## 4. Tests

- [x] 4.1 Add `ourlives/tests_clean_demo.py`: dry-run deletes nothing, `--yes` deletes all Demo scope, handmade `Real Org`/`real@company.com` survive, lookups intact, simulated `d/k` answers keep/delete correctly (mock `input`/`builtins.input`)
- [x] 4.2 Run `python manage.py test ourlives.tests_clean_demo` plus full `ourlives` suite and fix failures

## 5. Docs (accurate place for the run commands)

- [x] 5.1 Create `ourlives/docs/demo-clean.md` (next to `demo-seed.md`) with `python manage.py clean_ourlives_demo` plus `--dry-run`/`--yes` variants, `d/k/a/q/?` reference, scope + safety note
