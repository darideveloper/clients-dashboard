## Context

`ourlives/models.py` (16 models) + live form `Ourlens US Order Form V2` (Formidable `form_id=20`, verified 2026-09-10 via playwright: every radio/select toggled, visibility of all 78 `.frm_form_field` containers recorded). Static form vocabularies vs repo fixtures:

| Form vocabulary | Form values | Fixture today | Match |
|---|---|---|---|
| Country (`615[country]`) | 251 labels, duplicates (`Holy See`+`Vatican City`, `East Timor`+`Timor-Leste`), non-ISO `Kosovo`, colloquial (`Brunei`, `Swaziland`, `Macedonia`…) | `Country.json` 249 ISO-3166, pks 1–249 alpha by `iso2` | Fixture correct; form needs label→ISO normalization at import, not fixture edits |
| Pilot Currency (`680`, Pilot=Yes) / Currency (`681`, Pilot=No) | USD/CAD/GBP/EUR/ZAR (+Please Select) | `Currency.json` 12 (adds JPY/CNY/CHF/AUD/HKD/SGD/NZD), pks 1–12, M2M `countries` valid, max ref pk 249 | Superset; keep 12 |
| Product US/CA/UK/SA (`627/630/633/694`) | Micro/Regional/Enterprise Pilot each | — none — | **Gap: 12 combos** |
| Quantity+amount per region (`628/687`, `631/686`, `634/685`, `695/693`) | free numbers per order ($/CA$/£/R) | n/a (per-order `OrderItem`, not catalog) | No fixture |
| Additional codes (`636`→`637`→`639-658`) | Up to 5 / Up to 20 → Code 1..5 / 1..20 | `CodeType.json` `up_to_5`/`up_to_20` | Exact |
| Contacts (`616-618`, `619-621`) | primary + invoice only | `ContactType.json` 4 (+billing, +technical extensibility) | Superset; keep |
| Pilot Yes/No (`609`) | pilot only | `OrderType.json` 4 (+renewal/standard/trial lifecycle) | Superset; keep |
| `db.sqlite3` | predates CRM tables (only project/invitationcode/stripeevent/appsettings tables exist) | — | No prices to mine; page shows no catalog prices |

Constraints: single source `project/admin_base.py`; `base_loaddata` auto-discovers `<app>/fixtures/<app>/*.json` sorted, no loader edits; `start.sh` runs `migrate` then `base_loaddata`; `loaddata` bypasses `save()` so explicit PKs + string decimals required; existing tests pin counts (249/4/2/4/12) and `Rep==0`.

## Goals / Non-Goals

**Goals:**
- Preload every static form vocabulary as base fixtures so a fresh `migrate` + `base_loaddata` deploy can take a sale with zero admin data entry: add the 12-row `Product` catalog, keep the other 5 files.
- Keep base/seed tiering clean: catalog in base (needed every deploy/test), nothing transactional in fixtures.

**Non-Goals:**
- No model/admin/view/import-code changes; no `Country`/`Currency` row edits; no transactional seed data; no country-label normalizer (import concern, separate change); no EUR-pilot product invention (form shows no EUR block — no EUR rows).

## Decisions

- **12 Product rows = 3 tiers × 4 pilot currencies (no EUR).** Form reveals one product select per region only when Pilot=Yes and that region's `pilot_currency` is chosen (verified: USD→627/628/687, CAD→630/631/686, GBP→633/634/685, ZAR→694/695/693; EUR→none; Pilot=No→none, uses scans/cost/total instead). Alternative (16 with EUR, or 3 currency-agnostic rows) rejected: contradicts observed conditionals; `Product.currency` is non-nullable PROTECT FK so one row per currency is required.
- **FK to existing Currency PKs (USD=1, GBP=4, CAD=8, ZAR=12), explicit Product PKs 1–12 grouped by currency then tier.** Follows the `currency-fixture` table and `crm-phase1-lookups` alphabetical-PK precedent so future `OrderItem` seeds can reference stable PKs. Alternative (PK by tier) rejected: breaks per-currency grouping admins expect.
- **`tier` = `micro`/`regional`/`enterprise` lowercase; `name` = `<Region> <Tier> Pilot` (e.g. `US Micro Pilot`); `unit_price` = TBD placeholder `0.00` until sales supplies catalog prices.** `name` uniqueness is not DB-constrained (only `Currency.code`, lookup `code`s are), so descriptive names are safe. Placeholder over invention: prices appear nowhere (per-order amounts on form, no catalog on page, stale local DB). `0.00` is honest and grep-able; `ProductTests` already create `Micro Pilot` ad-hoc so no constraint breaks.
- **Keep `Currency` at 12, `Country` at 249, lookups as-is.** Verified supersets with valid refs; trimming to form-subsets would churn specs/tests (`Phase1FixturesTests`, `CurrencyFixtureTests`, `currency-fixture`, `crm-phase1-lookups`) for zero deploy benefit. Alternative (trim to 5 currencies) rejected.
- **No fixture for anything the form fills per sale** (Org/Contact/Address/Order/OrderItem/InvitationCode rows, Rep, AppSettings, StripeEvent) — same rationale as existing `Rep` exclusion; token-pool validation and per-order identity make fixtures actively harmful.

## Risks / Trade-offs

- [`0.00` placeholder prices ship if sales never replies] → Mitigation: `unit_price` is admin-editable, `OrderItem.unit_price` snapshots per order so placeholder never corrupts history; tasks gate the price fill as one explicit step.
- [Guessing tier/region naming (`US Micro Pilot` vs `Micro Pilot (USD)`)] → Mitigation: names are display-only, no uniqueness constraint; rename is a fixture-only edit, no migration.
- [EUR pilot orders have no product to attach] → Mitigation: documented non-goal; form itself offers no EUR block — CRM treats EUR pilots via scans/cost path until sales clarifies.
- [Country label mismatch bites future import] → Mitigation: out of scope here; design notes the 20-vs-18 diff so the import change normalizes (e.g. `Brunei`→`Brunei Darussalam`, drop `Kosovo` dup) instead of dirtying the ISO fixture.

## Migration Plan

- Deploy: merge fixture file only (no migration — fixtures aren't schema). `start.sh` loads it on next deploy; fresh DBs get 12 rows, existing DBs upsert by PK via `loaddata` idempotency. Rollback: delete file + `base_loaddata` rerun leaves rows (loaddata never deletes) — remove rows via shell if a name/price must be revoked; no data-loss path since no code reads products yet.

## Open Questions

1. Canonical `unit_price` per tier/currency (12 numbers) — sales team? (Ships `0.00` if unanswered.)
2. Confirm display naming convention for products (proposed `<Region> <Tier> Pilot`).
3. EUR pilot: truly no products, or missing form block to mirror later?
4. `Organization.name` source at import (form has address but no company-name input) — separate import change, noted here only.
