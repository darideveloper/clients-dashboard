## Context

`ourlives/models.py` currently holds 10 models: the original 5 (`Project`, `Organization`, `InvitationCode`, `AppSettings`, `StripeEvent`) plus Phase 1 lookups (`Country`, `Rep`, `ContactType`, `CodeType`, `OrderType`) behind migration `0009_codetype_contacttype_country_ordertype_rep.py`. The source of truth `ourlives/docs/crm-erd.md` defines 14 tables; the four transactional dependents (`currencies`, `products`, `contacts`, `organization_addresses`) have no Django models yet and block the future Order/OrderItem phase. Scope is DB-only: `models.py` + migration + model tests. No admin, views, serializers, business logic; `project/admin_base.py` untouched. Global rules apply: derived values are `@property` (none needed here), `related_name` on all FKs, `PROTECT` on business FKs, `unique=True` on natural keys.

## Goals / Non-Goals

**Goals:**
- Add `Currency`, `Product`, `Contact`, `OrganizationAddress` models implementing the ERD tables, with delete semantics that protect money/reference data and cascade owned child rows.
- One migration depending on `0009`, plus model tests covering FK creation, nullable `Currency.country`, `SET_NULL` behaviour, and `is_primary` filtering.

**Non-Goals:**
- `Order` / `OrderItem` / `order_order_types` M2M (future phase; ERD `order_type_id` FK is dropped there per global decision — M2M only).
- Admin registration, fixtures/`base_loaddata` changes, single-primary enforcement, price/rate validation, derived `@property` totals (those belong to the Order phase).

## Decisions

- **`Currency.country`: nullable FK with `SET_NULL`** over `CASCADE`. Rationale: deleting a country must not destroy currency definitions (money outlives geography rows). Alternative `CASCADE` rejected as destructive. `null=True, blank=True`, `related_name="currencies"`. (User-confirmed; spec wrote `CASCADE/SET_NULL` ambiguously.)
- **`Product.currency`, `Contact.contact_type`, `OrganizationAddress.country`: `PROTECT`** over `CASCADE`/`SET_NULL`. Rationale: matches `InvitationCode.project` pattern; deleting a currency/type/country with dependents must fail loudly instead of orphaning or wiping financial rows.
- **`Contact.organization`, `OrganizationAddress.organization`: `CASCADE`** over `PROTECT`. Rationale: contacts/addresses are owned by the org; they have no meaning without it and should die with it.
- **`Product.tier`: free-text `CharField(max_length=50)`** over choices enum. Rationale: ERD contradicts itself (`micro` example vs `regional/enterprise` enum note); locking choices now is speculative. Constrain later when the list stabilizes.
- **Decimals `max_digits=10, decimal_places=2`** for `exchange_rate` and `unit_price`, over higher FX precision. Rationale: matches `AppSettings.price_per_token` pattern already in codebase; raise precision when a real rate needs it.
- **`is_primary`: filter-only, no DB constraint.** Rationale: "one primary per org" is business logic with update edge cases; task scope is DB structure + filtering tests. Enforce later in `clean()`/admin if needed.
- **Conventions follow Phase 1**: `ordering` (`Currency` by `code` like the other code-bearing lookups, `Product` by `name`, `Contact` by `last_name, first_name`, `Address` by `-is_primary, city`), `__str__` (`Currency.code`, `Product.name`, `Contact "First Last"`, `Address "line1, city"`), `active`/`description` fields where the ERD has them, `EmailField` for `Contact.email` (required, not globally unique — same person may serve two orgs).
- **Deliberately permissive vs ERD on 4 string fields.** `Product.tier`, `Contact.phone`, `OrganizationAddress.state`, and `Currency.symbol_left` are `blank=True` although the ERD marks them required. Rationale (user-confirmed): form-collected data is dirtier than the ERD assumes and `tier` has no stable value list yet; tightening to required later is a trivial migration.
- **No fixtures.** Rationale: currencies/products/contacts/addresses are transactional data, not lookup seeds; `base_loaddata` stays untouched.

## Risks / Trade-offs

- [Risk] `SET_NULL` leaves currencies with `country=None` after country delete → Mitigation: `null=True` is explicit and tested; admin (future) can surface unlinked currencies.
- [Risk] Free-text `tier` allows typos/inconsistent values → Mitigation: accepted short-term; choices enum is a one-migration change later.
- [Risk] No single-primary enforcement allows multiple `is_primary=True` per org → Mitigation: documented non-goal; queries filter by `is_primary=True` and ordering puts primary first.
- [Risk] `Contact.email` non-unique allows duplicates → Mitigation: intentional (multi-org contacts); add `UniqueConstraint(organization, email)` later if needed.
- [Risk] Mixed `Country` delete semantics: currencies SET_NULL (survive) while addresses PROTECT (block) → Mitigation: deleting a country with addresses fails even though currencies would null out cleanly; tested behaviour, surfaced here so it surprises nobody.

## Migration Plan

1. Append 4 model classes to `ourlives/models.py` after `OrderType`.
2. `python manage.py makemigrations ourlives` → `0010_*` with `dependencies = [("ourlives", "0009_codetype_contacttype_country_ordertype_rep")]`.
3. `python manage.py migrate` + full test run. Rollback: `migrate ourlives 0009` (new tables empty by definition).

## Open Questions

None. All four gaps (country delete rule, tier shape, primary enforcement, decimal precision) were resolved with the user during exploration.
