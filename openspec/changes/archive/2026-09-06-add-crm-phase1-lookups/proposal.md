## Why

The CRM ERD (`ourlives/docs/crm-erd.md`) defines 14 tables but only 5 exist in `ourlives/models.py` (Project, Organization, InvitationCode, AppSettings, StripeEvent). Phase 2/3 models (Currency, Contact, Order, …) need stable lookup targets to FK into. Creating the 5 dependency-free lookups first unblocks that work with zero coupling.

## What Changes

- Add `Country` model: `iso2` (UK), `iso3` (UK), `name` (UK), `region` (blank), `active` (default True).
- Add `Rep` model: `first_name`, `last_name`, `email` (UK, EmailField). No `total_orders`/`total_revenue` properties in this phase (deferred until `Order` exists). No fixture for Rep — real people, admin-created.
- Add `ContactType` model: `code` (UK), `name` (UK per Option B), `active` (default True), `description` (blank).
- Add `CodeType` model: `code` (UK), `name` (UK per Option B), `max_codes` (PositiveIntegerField), `active` (default True), `description` (blank).
- Add `OrderType` model: `code` (UK), `name` (UK per Option B), `active` (default True), `description` (blank).
- One new migration (expected `0009_*`); model tests (create + unique-constraint + `__str__`) in `ourlives/tests.py` (tests call `base_loaddata` in `setUp` to load fixtures).
- Add base fixtures in `ourlives/fixtures/ourlives/` for Country (~249 ISO-3166 rows), ContactType (4 rows: billing/Billing Contact, invoice/Invoice Contact, primary/Primary Contact, technical/Technical Contact), CodeType (2 rows: `up_to_20`/Large team bundle and `up_to_5`/Small team bundle), OrderType (4 rows: pilot/renewal/standard/trial each with contextual description) — all base tier, auto-discovered by existing `core/base_loaddata` and loaded via `start.sh` after `migrate` with zero loader edits. Explicit PKs per file alphabetical from 1 (Country by `iso2` → 1–249, lookups by `code`) so future FK fixtures can reference them. `description` is contextual per fixture (Country `region=""`).
- DB structure only — no admin, no views, no serializers, no business logic, no changes to `project/admin_base.py`.

## Capabilities

### New Capabilities

- `crm-phase1-lookups`: standalone CRM lookup models (Country, Rep, ContactType, CodeType, OrderType) with natural-key uniqueness, `__str__`, and `Meta` conventions, plus base fixtures for Country/ContactType/CodeType/OrderType (Rep excluded).

### Modified Capabilities

- None. Existing specs (`organization-management`, `invitation-code-validation`, etc.) are untouched; no requirement changes to current behavior.

## Impact

- Affected code: `ourlives/models.py` (append only), `ourlives/migrations/<next>_*` (new, expected `0009_*`), `ourlives/tests.py` (5 new TestCases), `ourlives/fixtures/ourlives/Country.json` (~249 rows), `ContactType.json` (4 rows), `CodeType.json` (2 rows), `OrderType.json` (4 rows) — auto-loaded by existing `core/base_loaddata` / `start.sh`.
- No API/admin/serializer changes; no new dependencies; no data migration beyond `loaddata` (idempotent by PK; re-runs update in place).
- Future FKs (`Currency.country`, `Contact.contact_type`, `InvitationCode.code_type`, `Order↔OrderType M2M`, `Organization.assigned_rep`) will `PROTECT` into these tables — no rework expected.
