## 1. Fixture

- [x] 1.1 Create `ourlives/fixtures/ourlives/Currency.json` with 12 rows (`ourlives.Currency`, explicit PKs 1–12 in BIS order, symbols, rates as strings, `countries` M2M as PK lists per spec table, active true)
- [x] 1.2 Run `base_loaddata` on a fresh test DB and confirm 12 `Currency` rows with correct country links

## 2. Tests

- [x] 2.1 Add `CurrencyFixtureTests` to `ourlives/tests.py` (row count/codes after `base_loaddata`, country links incl. multi-link USD/EUR/ZAR, idempotent re-run keeps 12 rows, Product creatable against seeded USD)
- [x] 2.2 Run full test suite and confirm no regressions (existing per-model count assertions unaffected)
