# product-fixture Specification

## Purpose
TBD - created by archiving change crm-fixture-form-parity. Update Purpose after archive.
## Requirements
### Requirement: Product base fixture

The system SHALL provide a base fixture at `ourlives/fixtures/ourlives/Product.json` with 12 rows covering every product select on the live buy form (`Ourlens US Order Form V2`: Micro/Regional/Enterprise Pilot × pilot regions US/CA/UK/SA), loaded via the existing `base_loaddata` with zero loader edits. Explicit PKs 1–12 grouped by currency then tier; `currency` FKs point at the existing `Currency` PKs (USD=1, GBP=4, CAD=8, ZAR=12); `tier` is lowercase (`micro`/`regional`/`enterprise`); `name` is `<Region> <Tier-capitalized> Pilot` (e.g. `US Micro Pilot`); `unit_price` is a decimal string (canonical sales prices when supplied, `0.00` placeholder otherwise); all rows `active` true with blank `description`:

| pk | currency | tier | name |
|----|----------|------|------|
| 1 | USD (1) | micro | US Micro Pilot |
| 2 | USD (1) | regional | US Regional Pilot |
| 3 | USD (1) | enterprise | US Enterprise Pilot |
| 4 | GBP (4) | micro | UK Micro Pilot |
| 5 | GBP (4) | regional | UK Regional Pilot |
| 6 | GBP (4) | enterprise | UK Enterprise Pilot |
| 7 | CAD (8) | micro | Canada Micro Pilot |
| 8 | CAD (8) | regional | Canada Regional Pilot |
| 9 | CAD (8) | enterprise | Canada Enterprise Pilot |
| 10 | ZAR (12) | micro | South Africa Micro Pilot |
| 11 | ZAR (12) | regional | South Africa Regional Pilot |
| 12 | ZAR (12) | enterprise | South Africa Enterprise Pilot |

No EUR rows (the form's `680` EUR option reveals no product block — verified). No fixture rows for per-sale data (`Order`, `OrderItem`, `Contact`, `OrganizationAddress`, `InvitationCode` rows, `Rep`, `AppSettings`, `StripeEvent`) SHALL be added by this capability.

#### Scenario: base_loaddata seeds twelve products

- **WHEN** `python manage.py base_loaddata` is run on a fresh database (after `migrate`, with existing Country/Currency fixtures loading first in sorted order)
- **THEN** 12 `Product` rows exist with tiers micro/regional/enterprise × currencies USD, GBP, CAD, ZAR, each `active` true, each pointing at its currency from the table above

#### Scenario: Re-running base_loaddata is idempotent for products

- **WHEN** `python manage.py base_loaddata` is run a second time
- **THEN** still exactly 12 `Product` rows exist (updated in place by PK, no duplicates)

#### Scenario: Seeded product unblocks pilot order items

- **WHEN** `base_loaddata` has run
- **THEN** an `OrderItem` can be created pointing at a seeded product (e.g. US Micro Pilot), and deleting that product while linked raises `ProtectedError`

#### Scenario: No per-sale fixtures leak into base

- **WHEN** `base_loaddata` has run
- **THEN** `Order`, `OrderItem`, `Contact`, `OrganizationAddress`, `Rep`, `InvitationCode`, `StripeEvent` contain zero fixture-created rows and `AppSettings` is untouched by product loading

