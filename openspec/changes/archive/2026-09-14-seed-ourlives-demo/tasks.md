## 1. Command scaffold

- [x] 1.1 Create `ourlives/management/commands/seed_ourlives_demo.py` with `BaseCommand`, flags `--seed 42 --reps 6 --orgs 10 --orders 25 --tokens --clear`, stdlib-only imports (`random`, `decimal`; rng-derived email hex, no `secrets`)
- [x] 1.2 Implement `--clear` scoped wipe in reverse-FK order (codes → items → orders → contacts/addresses → orgs/projects/reps, `Demo `/`test-` scope only, never lookups)
- [x] 1.3 Wire `call_command("base_loaddata")` first + `transaction.atomic()` wrapper + `AppSettings.get_solo()` token pre-sizing

## 2. Seed transactional graph (FK DAG order, Django ORM create)

- [x] 2.1 Create Reps (`test-{hex}@gmail.com`, unique) + Projects (`Demo ...`, unique names) with `random.Random(seed)`
- [x] 2.2 Create Organizations (`Demo ...`, `assigned_rep` mix incl. unassigned) + Contacts (mixed `ContactType`, org-owned, `test-{hex}@gmail.com`) + OrganizationAddresses (1–2 per org, exactly one `is_primary=True`)
- [x] 2.3 Create Orders honoring PROTECT/nullable rules: org+rep links, `primary/invoice_contact` from own org, `currency`/`pilot_currency` mix (incl. both NULL), `order_types` M2M mix (pilot/standard/multi/typeless), null `number_of_scans`/`cost_per_scan` injection, `po_number`/`referral`/`upgrade-from-pilot` realism, then spread `submitted_at` across ~6 months via `queryset.update()` (bypasses `auto_now_add`)
- [x] 2.4 Create OrderItems (CASCADE order, PROTECT product, explicit non-zero frozen `unit_price`, 0–4 per order incl. one duplicate-product order)
- [x] 2.5 Create InvitationCodes (PROTECT links, nullable order/code_type + `sequence`, `current_use <= max_use`, usage spread 0%/partial/100% incl. one `is_active=False`), verify `sum(max_use) <= total_tokens`

## 3. Coverage showcases + verification

- [x] 3.1 Add fixed showcase rows: `Empty Org` + lone rep (zero orders), `Full Org` (most orders, >25 related rows), currency-wins-over-pilot / pilot-only / `Uncategorized` orders, order-vs-product currency fallback item
- [x] 3.2 Run canonical command `python manage.py seed_ourlives_demo --seed 42 --reps 6 --orgs 10 --orders 25` on a migrated dev DB and verify admin: order summaries per currency, `line_total`/`total_agreed_price`/`is_pilot_order`, token counters + `usage_percentage`, all three inline families render

## 4. Tests

- [x] 4.1 Add command tests: exit 0 with defaults, email regex `^test-[0-9a-f]+@gmail\.com$` + uniqueness, `Country==249` after re-run, `--clear` only deletes seeded scope, branch rows exist (null scans, Uncategorized, typeless order, inactive code)
- [x] 4.2 Run `python manage.py test ourlives` (or targeted new tests) and fix failures

## 5. Docs (accurate place for the run command)

- [x] 5.1 Create `ourlives/docs/demo-seed.md` (next to `crm-erd.md`) containing the exact run command `python manage.py seed_ourlives_demo --seed 42 --reps 6 --orgs 10 --orders 25`, flags table, coverage matrix, and `--clear` safety note
