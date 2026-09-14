## Why

There is no realistic sales-like dataset for the `ourlives` app: `base_loaddata` only seeds lookup tables (countries, currencies, products with `0.00` prices) and leaves reps, orgs, orders, contacts, addresses, and invitation codes empty. Manually creating the 16-model graph with correct multi-currency, pilot/standard, and token-pool edge cases is slow and error-prone, so calculated fields (`OrderSummaryMixin` totals, `line_total`, token counters) and admin inlines are never visually exercised.

## What Changes

- New management command `seed_ourlives_demo` (stdlib-only, no new dependencies) that builds a deterministic, realistic demo dataset:
  - Calls `base_loaddata` first so all lookup FK targets exist.
  - Creates Reps, Projects, Organizations (with `assigned_rep`), Contacts + OrganizationAddresses (inline children), Orders + OrderItems (inline children), InvitationCodes linked to orders/code types.
  - All generated emails use `test-{random}@gmail.com`.
  - Default volume `--seed 42 --reps 6 --orgs 10 --orders 25`; tunable via flags (`--reps`, `--orgs`, `--orders`, `--seed`, `--tokens`, `--clear` scope).
  - Deterministic via `random.Random(seed)`; single `transaction.atomic()`; sets `AppSettings.total_tokens` upfront so `InvitationCode` pool validation never blocks seeding; idempotent scoped re-runs (`--clear` wipes only `Demo ` prefixed transactional rows, never lookup tables).
  - Deliberately covers every calculated-field branch: null scans/cost, `currency` vs `pilot_currency` vs `Uncategorized` attribution, order-vs-product currency fallback for items, pilot vs standard vs multi-type vs typeless orders, empty org/rep (zero orders), inactive codes, `100%`/`0%` usage.
- Docs update recording the exact run command and what it covers, stored next to the existing fixture docs.
- `StripeEvent` intentionally excluded: webhook-only audit rows with a read-only admin; seeding fake `evt_*` rows would pollute webhook idempotency tests. Confirmed in scope review.

## Capabilities

### New Capabilities
- `demo-seed`: deterministic realistic `ourlives` sales-like seeding command covering all transactional models, calculated fields, and inline children, with documented run command.

### Modified Capabilities
- None. No existing spec behavior changes; lookup fixtures, token-pool validation, admin summaries, and inlines keep their current requirements.

## Impact

- New file `ourlives/management/commands/seed_ourlives_demo.py` (+ tests in `ourlives/tests.py` or a dedicated test module); reuses `base_loaddata`, `AppSettings`, and existing model validation.
- Docs: one updated/added doc under `ourlives/docs/` (alongside existing fixture docs) with the canonical run command.
- No model/migration changes, no new dependencies, no admin changes. Dev/test-only tooling; safe to run in local environments, not for production deploys.
