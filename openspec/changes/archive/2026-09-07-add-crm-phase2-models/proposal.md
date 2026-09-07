## Why

Phase 1 delivered the lookup tables (`Country`, `Rep`, `ContactType`, `CodeType`, `OrderType`). Orders cannot be modeled without the four transactional dependents defined in `ourlives/docs/crm-erd.md`: money (`Currency`), sellables (`Product`), people (`Contact`), and locations (`OrganizationAddress`). Adding them now unblocks the future Order/OrderItem phase.

## What Changes

- Add `Currency` model: `code` (UK), `name`, `symbol_left`, `symbol_right`, `exchange_rate`, `country` FK nullable `SET_NULL`, `active`.
- Add `Product` model: `currency` FK `PROTECT`, `name`, `tier` (free-text), `unit_price`, `active`, `description`.
- Add `Contact` model: `organization` FK `CASCADE`, `contact_type` FK `PROTECT`, `first_name`, `last_name`, `email`, `phone`.
- Add `OrganizationAddress` model: `organization` FK `CASCADE`, `country` FK `PROTECT`, `line1`, `line2`, `city`, `state`, `zip`, `is_primary`.
- Add migration `0010_*` depending on `0009_codetype_contacttype_country_ordertype_rep`.
- Add model tests for FK creation, nullable `Currency.country` + `SET_NULL` behaviour, `is_primary` filtering, and `PROTECT`/`CASCADE` delete semantics.
- No `Order`/`OrderItem`, no admin, no views, no serializers, no business logic, no changes to `project/admin_base.py`.

## Capabilities

### New Capabilities

- `crm-phase2-core-models`: Currency, Product, Contact, and OrganizationAddress models with FK delete semantics, natural-key uniqueness, related_names, migration, and model tests.

### Modified Capabilities

- None. Existing Phase 1 models and specs are untouched.

## Impact

- `ourlives/models.py`: 4 new model classes appended after `OrderType`.
- `ourlives/migrations/0010_*`: new migration, depends on `0009`.
- `ourlives/tests.py`: new `TestCase` classes appended; no existing tests modified.
- Source of truth `ourlives/docs/crm-erd.md` unchanged (models implement the already-documented `currencies`, `products`, `contacts`, `organization_addresses` tables).
- No admin registration, no fixture changes (`base_loaddata` untouched — these are transactional tables, not lookup seeds).
