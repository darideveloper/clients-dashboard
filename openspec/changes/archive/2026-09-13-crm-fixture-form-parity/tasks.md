## 1. Prices + naming sign-off

- [x] 1.1 Confirm 12 canonical `unit_price` values (US/UK/Canada/South Africa × Micro/Regional/Enterprise Pilot) with sales; if unanswered, keep `0.00` placeholders and note it in the task output — DONE (2026-09-13): no sales input in session; shipping `0.00` placeholders, grep-able for later fill
- [x] 1.2 Confirm display naming (`US Micro Pilot` convention per spec table) or record the chosen alternative — DONE (2026-09-13): accepted spec-table convention, no alternative on record

## 2. Product base fixture

- [x] 2.1 Create `ourlives/fixtures/ourlives/Product.json` with 12 rows per `specs/product-fixture/spec.md` (explicit PKs 1–12, `currency` FKs USD=1/GBP=4/CAD=8/ZAR=12, lowercase `tier`, decimal-string `unit_price`, `active` true, blank `description`)
- [x] 2.2 Run `python manage.py migrate --noinput` on a fresh test DB, then `python manage.py base_loaddata`, and verify 12 `Product` rows with correct currency links plus unchanged counts (Country 249, ContactType 4, CodeType 2, OrderType 4, Currency 12, Rep 0) — DONE: scratch sqlite verified 249/4/2/4/12/12/0 with correct USD/GBP/CAD/ZAR links
- [x] 2.3 Re-run `base_loaddata` and verify still exactly 12 `Product` rows (idempotent, no duplicates) — DONE: re-ran, still 12/249/12

## 3. Test coverage

- [x] 3.1 Extend `ourlives/tests.py` (new `ProductFixtureTests` class following `CurrencyFixtureTests`): seeds-all-twelve, currency links per spec table, idempotency, seeded-product-unblocks-`OrderItem`, and zero fixture rows in `Order`/`OrderItem`/`Contact`/`OrganizationAddress`/`Rep`/`InvitationCode`/`StripeEvent`
- [x] 3.2 Run the full `ourlives` + `core` fixture-related tests (`Phase1FixturesTests`, `CurrencyFixtureTests`, `ProductFixtureTests`, `core/tests.py` loaddata tests) and confirm green — DONE: targeted 17 green; full `ourlives`+`core` 247 green
