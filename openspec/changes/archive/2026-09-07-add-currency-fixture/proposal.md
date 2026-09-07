## Why

`Product.currency` is required and `PROTECT`ed, so no product can exist until at least one `Currency` row exists — yet `base_loaddata` seeds none, leaving every fresh build/deploy with an unusable product catalog. Currencies are ISO-standard reference data (like the already-seeded `Country` table), so a starter set belongs in base fixtures.

## What Changes

- Add `ourlives/fixtures/ourlives/Currency.json` with 12 rows (explicit PKs 1–12, in BIS-2025 turnover order): USD, EUR, JPY, GBP, CNY, CHF, AUD, CAD, HKD, SGD, NZD, ZAR — each with symbols, a USD-relative starting rate (Fed G.5 Aug-2026 where available, otherwise approximate), and `countries` M2M links to every country that uses it (verified against the `Country` fixture: USD→US+8 dollarized states, EUR→20 Eurozone members, JPY→JP, GBP→GB, CNY→CN, CHF→CH+LI, AUD→AU+3 Pacific states, CAD→CA, HKD→HK, SGD→SG, NZD→NZ+4 Pacific states, ZAR→ZA+3 CMA states).
- No loader changes (`base_loaddata` auto-discovers; `Currency.json` sorts after `Country.json` so country links resolve).
- Add `CurrencyFixtureTests` to `ourlives/tests.py`: row count/fields, country links (incl. multi-link EUR/USD/ZAR), idempotent re-run.
- No fixtures for `Product` (commercial data, admin-created like `Rep`), `Contact` / `OrganizationAddress` (per-org transactional data).

## Capabilities

### New Capabilities

- `currency-fixture`: seeded 12-currency rows (BIS-2025 top 10 + NZD + ZAR) loaded via `base_loaddata`, with M2M country links and idempotency.

### Modified Capabilities

- None. `fixture-system` behavior (auto-discovery, sorted load) and `crm-phase2-core-models` model requirements are unchanged.

## Impact

- New file `ourlives/fixtures/ourlives/Currency.json` (picked up by `base_loaddata` on every build/deploy/test with no code changes).
- `ourlives/tests.py`: one new `TestCase` appended; existing tests untouched (per-model count assertions are unaffected).
- `Product` creation is unblocked on fresh databases (currencies to point at).
- `exchange_rate` values are starting defaults vs USD (Fed G.5 Aug-2026 where available), not live rates. Source: BIS Triennial Survey 2025 (FX turnover) + SWIFT Oct-2025 (payments) for the currency ranking.
