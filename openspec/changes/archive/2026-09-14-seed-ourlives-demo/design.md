## Context

`ourlives/models.py` (16 models) is the source of truth. Lookup tables are seeded by `base_loaddata` (`core/management/commands/base_loaddata.py`, auto-discovers `*/fixtures/*/*.json` in sorted order): Country (249), ContactType (4), CodeType (2), OrderType (4 incl. `pilot`), Currency (12 + M2M countries), Product (12, all `unit_price=0.00`). Nothing seeds the transactional graph: Rep, Project, Organization, Contact, OrganizationAddress, Order, OrderItem, InvitationCode. `AppSettings` (django-solo singleton) stays at `total_tokens=0`, so any `InvitationCode.save()` fails pool validation. `import_invitation_codes.py` is the reference for pool handling (auto-bump + bulk_create with update_or_create fallback). `StripeEvent` is webhook-only with a read-only admin — out of scope. Docs for the domain live in `ourlives/docs/` (`crm-erd.md` is the ERD source); the run command belongs next to it.

FK/delete graph that dictates creation (and reverse, deletion) order:

```
base lookups → Rep, Project → Organization(assigned_rep SET_NULL)
  → Contact(org CASCADE, type PROTECT) + OrganizationAddress(org CASCADE, country PROTECT)
  → Order(org PROTECT, rep PROTECT, contacts PROTECT nullable,
          currency/pilot_currency SET_NULL nullable, order_types M2M)
    → OrderItem(order CASCADE, product PROTECT)
  → InvitationCode(project PROTECT, org PROTECT, order/code_type PROTECT nullable)
```

Key model constraints the design must respect: `Rep.email`, `Organization.name`, `Project.name`, `InvitationCode.code`, `Order.order_number` unique; `InvitationCode` has `CheckConstraint current_use<=max_use` plus `save()` validation (`max_use>=current_use`, `sum(max_use)<=AppSettings.total_tokens`); `Contact.organization`/`OrganizationAddress.organization`/`OrderItem.order` CASCADE (children die with parent); `Currency` delete SETs NULL on orders (seed must not delete currencies).

## Goals / Non-Goals

**Goals:**
- One command `seed_ourlives_demo` producing a believable, deterministic sales dataset that visually exercises every `OrderSummaryMixin` branch, `line_total`/`total_agreed_price`/`is_pilot_order`, token counters + `usage_percentage`, and all three inline families.
- Django-idiomatic: ORM `create()` (so real validation runs), `transaction.atomic()`, `get_solo()`, no raw SQL, no new dependencies.
- Safe re-runs: scoped idempotency that never touches lookup tables.

**Non-Goals:**
- No model/migration/admin changes; no StripeEvent seeding; no perf-scale (10k rows) tooling; no Faker/factory_boy introduction; not for production deploys.

## Decisions

- **New command at `ourlives/management/commands/seed_ourlives_demo.py`, stdlib-only (`random`, `secrets`, `decimal`).** Alternative: JSON fixtures for orders — rejected, hardcoded PKs rot and `loaddata` bypasses `save()` pool validation. Alternative: Faker — rejected, new dependency for dev-only tooling; small hardcoded name pools + `random.Random(seed)` are enough and reproducible.
- **Call `base_loaddata` first inside the command.** Rationale: guarantees FK targets (countries, contact/code/order types, currencies, products) regardless of DB state; matches how tests set up (`call_command("base_loaddata")`). Alternative: assume fixtures exist — rejected, fresh DBs would fail with confusing FK errors.
- **Set `AppSettings.total_tokens` upfront (default e.g. 1_000_000, `--tokens` override) via `get_solo()` + `save()` before creating codes.** Rationale: `InvitationCode.save()` validates pool on every row; pre-sizing avoids per-row failures. Mirrors `import_invitation_codes` auto-bump behavior. Precompute planned `sum(max_use)` when `--tokens` not given is a follow-up, not required.
- **Creation order follows the FK DAG** (Rep/Project → Organization → Contact/Address → Order → OrderItem → InvitationCode), all inside one `transaction.atomic()`. Rationale: respects PROTECT/CASCADE semantics; atomicity avoids half-seeded graphs on error.
- **Deterministic RNG (`random.Random(args.seed)`) for all generated values including the `test-{hex}@gmail.com` local-part (rng-derived hex + per-row counter for uniqueness).** Rationale: fully reproducible demos (`--seed 42` always yields the same dataset) while satisfying unique `Rep.email`. `secrets` is rejected here precisely because it would break repeatability.
- **Explicit `OrderItem.unit_price` (realistic frozen prices, e.g. 295–4995), never the fixture `0.00`.** Rationale: fixture products are price-less pilots; catalog totals would all read `0` otherwise. Do NOT rewrite `Product.json` — item price is frozen at order time by design.
- **Deliberate edge-case injection (~10% nulls + fixed showcase rows) instead of pure random.** One `Empty Org`/`lone Rep` (zero orders), one `Full Org` (most orders, >25 related rows to prove pagination), one `currency+pilot` order (currency wins), one pilot-only, one currency-less (`Uncategorized`), one typeless order, one inactive code, usage spread (`0%`, partial, `100%`). Rationale: pure random rarely hits all five `OrderSummaryMixin` branches; fixed rows guarantee coverage.
- **Scoped idempotency: `--clear` deletes only seeded transactional rows (`name__startswith="Demo "` / `email__startswith="test-"`) in reverse-FK order (codes → items → orders → contacts/addresses → orgs/projects/reps), never lookups; without `--clear`, stable models (Rep/Project/Organization, keyed by unique email/name) upsert via `get_or_create`/`update_or_create`, while auto-unique rows (Order/InvitationCode with generated `order_number`/`code`) are created anew — `--clear` is the exact-repeat path.** Rationale: re-runnable demos without destroying hand-made data or the 249 countries.
- **Spread `Order.submitted_at` across ~6 months via `queryset.update()` after creation.** Rationale: `submitted_at` is `auto_now_add` so plain `create()` clusters all orders in the same minute, which looks fake and flattens the admin `date_hierarchy`; `update()` bypasses `auto_now_add`. `last_order_date` values then genuinely differ per holder.
- **Docs at `ourlives/docs/demo-seed.md`** (next to `crm-erd.md`) holding the canonical run command plus coverage table. Rationale: discoverable where the domain ERD lives; single source for the exact command string.

## Risks / Trade-offs

- [Risk] `submitted_at` backdating bypasses `auto_now_add` via `update()` → Mitigation: only seeded `Demo` orders are touched, in the same atomic run; no signal/model change.
- [Risk] Seeded `Demo` rows collide with real rows named similarly → Mitigation: distinctive `Demo ` prefix + `test-` email scope; `--clear` only touches that scope.
- [Risk] `total_tokens` pre-size too small if user raises `--orders` a lot → Mitigation: generous default (1M) + `--tokens` flag; command fails loudly with pool message (same wording as import command) instead of silently bumping.
- [Risk] Random data looks samey across runs → Mitigation: fixed showcase rows + name pools sized for default volumes; seed flag documents reproducibility.
- [Trade-off] ORM row-by-row `create()` is slower than `bulk_create`, but runs real `save()` validation (pool, `CheckConstraint`-adjacent logic) — correct for ≤ hundreds of rows; bulk path deferred until perf seeding is requested.
