## Context

`ourlives/models.py` has 5 models (Project, Organization, InvitationCode, AppSettings, StripeEvent). The ERD source of truth (`ourlives/docs/crm-erd.md`) defines 14 tables. This change adds the 5 dependency-free lookups: Country, Rep, ContactType, CodeType, OrderType. None of them has FKs, so they can land in any order in a single migration. Consumers (Currency→Country, Contact→ContactType, InvitationCode→CodeType, Order M2M→OrderType, Organization→Rep) come in Phase 2/3. Existing test pattern lives in single-file `ourlives/tests.py` (e.g. `ProjectTests`, `StripeEventModelTests`); migrations are linear (`0008_…` is head).

## Goals / Non-Goals

**Goals:**
- 5 new tables with natural-key uniqueness, `__str__`, `Meta` ordering/verbose names, matching existing model style.
- One new migration + model tests (create + unique-violation + `__str__`).
- Base fixtures for Country (~249 rows), ContactType (4), CodeType (2), OrderType (4) — Rep has no fixture — auto-loaded by existing `core/base_loaddata` via `start.sh` after `migrate`, zero loader changes.
- Zero coupling to Phase 2/3; future `PROTECT` FKs land cleanly.

**Non-Goals:**
- No admin (`ourlives/admin.py` untouched, no `project/admin_base.py` changes).
- No views, serializers, business logic, or derived `@property` fields (Rep totals deferred until `Order` exists).
- No timestamps, no `clean()` normalization, no case-insensitive constraints — YAGNI until proven need.
- No fixtures for Rep (real people, admin-created) and no seed-tier fixtures in this change.

## Decisions

1. **One capability, one migration.** All 5 models are FK-free → single `makemigrations` run, single next-migration file (expected `0009_*`). Alternative (one migration per model) rejected: 5× churn for no dependency benefit.
2. **Option B uniqueness (user-confirmed).** `code UK + name UK` on ContactType/CodeType/OrderType; `iso2/iso3/name` each UK on Country; `email UK` on Rep. Alternative A (code-only) rejected: user prefers guaranteed-distinct admin labels; rename-transition cost (`Billing (old)` temp name) accepted.
3. **Field types from ERD examples + codebase defaults.** `iso2=CharField(2)`, `iso3=CharField(3)`, lookup `code=CharField(50)`, display `name=CharField(100)`, `first/last_name=CharField(100)`, `email=EmailField(254)`, `region=CharField(10, blank=True)`, `description=TextField(blank=True)`, `active=BooleanField(default=True)`, `CodeType.max_codes=PositiveIntegerField()`. No `null=True` on strings (Django convention; matches existing models). Alternative (exact Formidable lengths) rejected: ERD gives examples, not DDL; user confirmed defaults.
4. **No `related_name` / FK opts in this phase.** Nothing to point at yet; Phase 2/3 adds `PROTECT` + `related_name` on their side. Matches GLOBAL DECISION (PROTECT on business FKs) without premature scaffolding.
5. **`__str__`: `Country→name`, `Rep→"First Last"`, lookups→`name`.** Matches `Project`/`Organization` (`return self.name`) pattern. Alternative (`f"{code}: {name}"`) rejected: noisier dropdowns; code stays queryable.
6. **`Meta.ordering`: lookups by `["code"]`, Country by `["name"]`, Rep by `["last_name", "first_name"]`.** Deterministic admin/test ordering at zero cost.
7. **Rep derived properties deferred.** `total_orders`/`total_revenue` SHALL be `@property` per GLOBAL DECISIONS, but with no `Order` table any implementation would be a stub `return 0` — dead code. Skipped until Phase 2/3 (user-confirmed).
8. **Base fixtures auto-loaded, explicit PKs, contextual descriptions, `base_loaddata` in tests.** Fixtures live in `ourlives/fixtures/ourlives/` as base tier (always loaded via existing `core/base_loaddata` after `migrate` in `start.sh`; no `FIXTURE_DIRS` per doc). Explicit PKs per file alphabetical from 1 (Country by `iso2` → 1–249, lookups by `code`) so future FK/seed fixtures can reference them. `description` is contextual: ContactType all 4 share "Extensible contact role, from 616/619"; CodeType `up_to_5` is "Small team bundle, separate frontend field", `up_to_20` is "Large team bundle, up to 20 additional codes, separate frontend field"; OrderType `pilot`/`renewal`/`standard`/`trial` each have distinct pilot/renewal/standard/trial descriptions (e.g., pilot "Pilot order for initial evaluation period, replaces hard boolean is_pilot_order"); Country `region` is blank. Tests call `call_command("base_loaddata")` in `setUp` per doc §7 (also covers the loader) rather than `fixtures = [...]`.
9. **Country full ISO-3166, `region=""`.** ERD says 250 options; full ISO (~249 rows) with `region=""` and `active=true` covers it. `region` has no ISO source, so blank and filled via admin later. Alternative (minimal 3-row set) rejected; hardcoded list in JSON with no new dependency (`pycountry`).

## Risks / Trade-offs

- [Risk] Duplicate display `name` transitions blocked by Option B unique → Mitigation: temp-name convention (`Billing (old)`); reversible by dropping one constraint.
- [Risk] `max_length` guesses (esp. `region=10`, `code=50`) prove too small for real data → Mitigation: trivial `AlterField` migration; no FKs depend on length.
- [Risk] Single-file `tests.py` (already 923 lines) grows → Mitigation: accepted; matches repo pattern, avoids test-runner reconfiguration. Split only if file becomes unmanageable.
- [Risk] Future case-variant codes (`Pilot` vs `pilot`) bypass unique → Mitigation: out of scope; add `Lower()` functional constraint only on evidence.
- [Risk] Country fixture size / hardcoded ISO list drift vs upstream ISO → Mitigation: ~249 rows with explicit PKs, `region=""` blank; `loaddata` idempotent by PK; fail-soft loader could hide bad JSON so CI asserts row counts.
- [Risk] Fixture JSON typo breaks `base_loaddata` silently (fail-soft) → Mitigation: model tests call `base_loaddata` and assert expected rows exist; entrypoint stays fail-soft so one bad fixture doesn't block deploy.
