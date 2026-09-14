# demo-seed Specification

## Purpose

Deterministic realistic ourlives sales-like seeding for exercising calculated fields and admin inlines in development and test environments.

## Requirements

### Requirement: Deterministic demo seed command with documented run command
The system SHALL provide `ourlives/management/commands/seed_ourlives_demo.py` runnable as `python manage.py seed_ourlives_demo --seed 42 --reps 6 --orgs 10 --orders 25` with flags `--seed/--reps/--orgs/--orders/--tokens/--clear`, and SHALL document that exact command in `ourlives/docs/demo-seed.md`.

#### Scenario: Canonical run command works
- **WHEN** `python manage.py seed_ourlives_demo --seed 42 --reps 6 --orgs 10 --orders 25` is run on a migrated DB
- **THEN** the command exits 0 and creates ~6 reps, ~10 organizations, ~25 orders plus contacts, addresses, items, and codes

#### Scenario: Run command is documented in the accurate place
- **WHEN** a developer opens `ourlives/docs/demo-seed.md`
- **THEN** the file contains the exact command `python manage.py seed_ourlives_demo --seed 42 --reps 6 --orgs 10 --orders 25` plus a coverage summary

### Requirement: Lookup-first realistic graph respecting DB structure
The system SHALL call `base_loaddata` first and then create Rep → Project → Organization (`assigned_rep` SET_NULL, some unassigned) → Contact (mixed `ContactType`, CASCADE) + OrganizationAddress (exactly one `is_primary=True` per org with addresses, CASCADE) → Order (PROTECT links, nullable contacts/currencies, `submitted_at` spread across ~6 months via `queryset.update()`) → OrderItem (CASCADE order, PROTECT product, explicit non-zero `unit_price`) → InvitationCode (PROTECT links, nullable order/code_type), all inside one `transaction.atomic()`, using stdlib RNG (`random.Random(seed)`, rng-derived email hex) and no new dependencies. `StripeEvent` is intentionally NOT seeded (webhook-only audit rows with a read-only admin; keeps webhook idempotency tests clean).

#### Scenario: Fresh DB seeds end to end
- **WHEN** the command runs on a fresh migrated DB
- **THEN** all FKs resolve (contacts/addresses/items/codes attach to their parents) and no new dependency was added to `requirements.txt`

#### Scenario: One primary address per addressed org
- **WHEN** seeding completes
- **THEN** every organization that has addresses has exactly one with `is_primary=True`

#### Scenario: Order items carry frozen realistic prices
- **WHEN** seeding completes
- **THEN** every `OrderItem.unit_price` is greater than `0` even though fixture `Product.unit_price` is `0.00`

### Requirement: Test-email domain rule
Every generated `Rep.email` and `Contact.email` SHALL match `test-{random-hex}@gmail.com` and remain unique.

#### Scenario: All emails use the test domain
- **WHEN** seeding completes with defaults
- **THEN** all `Rep` + `Contact` emails match `^test-[0-9a-f]+@gmail\.com$` and no duplicates exist

### Requirement: Token-pool-safe invitation codes
The system SHALL size `AppSettings.total_tokens` upfront (default generous, `--tokens` override) before creating codes, and every `InvitationCode` SHALL satisfy `current_use <= max_use` with usage spread across `0%`, partial, and `100%`, including at least one `is_active=False` code (which still counts as assigned).

#### Scenario: Pool never blocks seeding
- **WHEN** the command runs with defaults
- **THEN** `sum(InvitationCode.max_use) <= AppSettings.total_tokens` and the command exits 0

#### Scenario: Usage spread visible in admin
- **WHEN** seeding completes
- **THEN** at least one code shows `0%`, one partial, one `100%` `usage_percentage`, and one inactive code exists

### Requirement: Calculated-field branch coverage
The seeded data SHALL exercise: `total_agreed_price` (normal + null scans + null cost), `is_pilot_order` (pilot-only, standard-only, multi-type, typeless), agreed-totals attribution (`currency` wins over `pilot_currency`, pilot-only, neither → `Uncategorized`), catalog-items attribution (order currency → pilot currency → product currency fallback), `combined_total` merge, an empty org/rep with zero orders, and a full org holding the most orders.

#### Scenario: All summary branches present
- **WHEN** seeding completes
- **THEN** there exists an order with `number_of_scans=None`, one with `cost_per_scan=None`, one pilot / one standard / one multi-type / one typeless order, one `currency+pilot` order, one pilot-only order, one currency-less order with scans (→ `Uncategorized`), an item whose order currency differs from its product currency, an org with zero orders (its `last_order_date` is None and all its totals render `—`), a rep with zero orders, an order with zero items, and an order with zero invitation codes (empty items-inline / `codes_list` states)

#### Scenario: Order dates spread across months
- **WHEN** seeding completes
- **THEN** seeded `Order.submitted_at` values span roughly 6 months (set via `queryset.update()` to bypass `auto_now_add`), so holders have differing `last_order_date` values and the admin `date_hierarchy` shows multiple months

### Requirement: Inline-family coverage
The seeded data SHALL render every inline state: organizations with 0/1/multiple contacts and addresses, and orders with 0/1/multiple items (including one order with a duplicate product line), with `primary_contact`/`invoice_contact` drawn from the order's own organization.

#### Scenario: Inlines populated
- **WHEN** seeding completes and an admin opens a seeded organization and order change page
- **THEN** the organization shows its contacts + addresses inlines, the order shows its items inline with `line_total_display`, and the order's contacts belong to its organization

### Requirement: Scoped idempotent re-runs
Re-running with the same seed SHALL NOT duplicate lookup rows and SHALL NOT touch non-seeded data; `--clear` SHALL delete only seeded transactional rows in reverse-FK order (codes → items → orders → contacts/addresses → orgs/projects/reps).

#### Scenario: Re-run is safe
- **WHEN** the command runs twice with the same flags (second time with `--clear`)
- **THEN** `Country` count stays 249, no duplicate `Demo` organizations exist, and no non-`Demo`/non-`test-` rows were deleted
