## 1. Models

- [x] 1.1 Append `Country`, `Rep`, `ContactType`, `CodeType`, `OrderType` to `ourlives/models.py` per spec field types, Option B uniqueness, `__str__`, and `Meta` ordering/verbose names
- [x] 1.2 Run `python manage.py check` to verify model definitions load cleanly

## 2. Migration

- [x] 2.1 Run `python manage.py makemigrations ourlives` and confirm a single new migration (expected `0009_*`) with 5 `CreateModel` ops
- [x] 2.2 Run `python manage.py migrate` and verify tables exist with expected unique constraints

## 3. Fixtures

- [x] 3.1 Create `ourlives/fixtures/ourlives/Country.json` (~249 ISO-3166 rows, PK 1–249 alphabetical by `iso2`, `region=""`, `active=true`, explicit PKs, blank description)
- [x] 3.2 Create `ourlives/fixtures/ourlives/ContactType.json` (4 rows: billing/invoice/primary/technical, PK alphabetical by `code`, ERD description where available)
- [x] 3.3 Create `ourlives/fixtures/ourlives/CodeType.json` (2 rows: `up_to_20` max 20 blank description, `up_to_5` max 5 ERD text, PK alphabetical by `code`)
- [x] 3.4 Create `ourlives/fixtures/ourlives/OrderType.json` (4 rows: pilot/renewal/standard/trial, PK alphabetical by `code`, ERD description where available)
- [x] 3.5 Run `python manage.py migrate && python manage.py base_loaddata` on a fresh DB and verify row counts (Country ~249, ContactType 4, CodeType 2, OrderType 4) and explicit PKs; re-running `base_loaddata` leaves counts unchanged (idempotent)

## 4. Tests

- [x] 4.1 Add `CountryTests` to `ourlives/tests.py` (create + iso2/iso3/name duplicate rejection + `__str__`)
- [x] 4.2 Add `RepTests` (create + duplicate-email rejection + `__str__`, no derived properties, no fixture)
- [x] 4.3 Add `ContactTypeTests`, `CodeTypeTests`, `OrderTypeTests` (create + duplicate-code/name rejection + `__str__`)
- [x] 4.4 Update tests to call `call_command("base_loaddata")` in `setUp` per doc §7 so fixture rows exist and loader is covered; verify `Rep` still has no fixture rows
- [x] 4.5 Run `python manage.py test ourlives` and confirm full suite passes
