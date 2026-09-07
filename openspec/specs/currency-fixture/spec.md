# currency-fixture Specification

## Purpose
TBD - created by archiving change add-currency-fixture. Update Purpose after archive.
## Requirements
### Requirement: Currency base fixture

The system SHALL provide a base fixture at `ourlives/fixtures/ourlives/Currency.json` with 12 rows loaded via `base_loaddata` (explicit PKs 1–12, rates vs USD, M2M `countries` as PK lists, all `active` true):

| pk | code | name | symbol_left | rate | countries |
|----|------|------|-------------|------|-----------|
| 1 | USD | US Dollar | $ | 1.00 | US + EC, SV, ZW, PA, TL, MH, FM, PW |
| 2 | EUR | Euro | € | 0.86 | 20 Eurozone: AT, BE, HR, CY, EE, FI, FR, DE, GR, IE, IT, LV, LT, LU, MT, NL, PT, SK, SI, ES |
| 3 | JPY | Japanese Yen | ¥ | 161.00 | JP |
| 4 | GBP | British Pound | £ | 0.75 | GB |
| 5 | CNY | Chinese Yuan | CN¥ | 6.74 | CN |
| 6 | CHF | Swiss Franc | Fr | 0.81 | CH, LI |
| 7 | AUD | Australian Dollar | A$ | 1.41 | AU, KI, NR, TV |
| 8 | CAD | Canadian Dollar | CA$ | 1.39 | CA |
| 9 | HKD | Hong Kong Dollar | HK$ | 7.84 | HK |
| 10 | SGD | Singapore Dollar | S$ | 1.29 | SG |
| 11 | NZD | New Zealand Dollar | NZ$ | 1.69 | NZ, CK, NU, PN, TK |
| 12 | ZAR | South African Rand | R | 17.80 | ZA, LS, NA, SZ |

Rates are starting defaults vs USD (Fed G.5 Aug-2026 where available; SGD/NZD/ZAR approximate), not live rates.

#### Scenario: base_loaddata seeds twelve currencies

- **WHEN** `python manage.py base_loaddata` is run on a fresh database (after `migrate`)
- **THEN** 12 `Currency` rows exist with codes USD, EUR, JPY, GBP, CNY, CHF, AUD, CAD, HKD, SGD, NZD, ZAR, each `active` true

#### Scenario: Fixture currencies link to all using countries

- **WHEN** `base_loaddata` has run
- **THEN** USD links to United States + 8 dollarized states, EUR to all 20 Eurozone members, ZAR to South Africa + Lesotho, Namibia, Eswatini, and each remaining currency links to its using countries per the table above

#### Scenario: Re-running base_loaddata is idempotent for currencies

- **WHEN** `python manage.py base_loaddata` is run a second time
- **THEN** still exactly 12 `Currency` rows exist (updated in place, no duplicates)

#### Scenario: Seeded currency unblocks product creation

- **WHEN** `base_loaddata` has run
- **THEN** a `Product` can be created pointing at the seeded USD currency

