## Context

`ourlives` has 14 models; base fixtures seed only the 5 closed vocabularies (`Country` 249, `ContactType` 4, `CodeType` 2, `OrderType` 4) while `Rep` is deliberately unseeded. `base_loaddata` (in `core`) auto-discovers `<app>/fixtures/<app>/*.json` in sorted order with no loader edits needed. The `Currency` model (`code` UK, `exchange_rate`, `countries` M2M `blank=True`, `active`) currently has no fixture, so fresh databases have no currency for `Product.currency` (required, PROTECT) to point at. Country PKs needed (all resolved against the `Country` fixture, zero missing): USD [233, 63, 210, 249, 173, 221, 143, 73, 185], EUR [12, 20, 98, 55, 64, 70, 75, 57, 89, 102, 110, 135, 133, 134, 153, 166, 184, 202, 200, 68], JPY [114], GBP [77], CNY [48], CHF [43, 129], AUD [13, 118, 169, 227], CAD [38], HKD [95], SGD [198], NZD [171, 45, 170, 181, 220], ZAR [247, 132, 160, 213]. Alphabetically `Currency.json` loads after `Country.json`, so country links resolve.

## Goals / Non-Goals

**Goals:**
- Seed 12 starter currencies (BIS-2025 top 10 by FX turnover + NZD + ZAR) via `base_loaddata` with explicit PKs, symbols, USD-relative rates, and links to every using country.
- Test coverage for row content, country links, and idempotent re-runs.

**Non-Goals:**
- Loader changes; `Product`/`Contact`/`OrganizationAddress` fixtures (commercial/per-org data, admin-created); live FX rates.

## Decisions

- **12 currencies: BIS-2025 FX top 10 (USD, EUR, JPY, GBP, CNY, CHF, AUD, CAD, HKD, SGD) + NZD + ZAR** over the original 4. Rationale: top-10 are the most-traded currencies by far (BIS Triennial Survey Apr-2025; USD alone on one side of 89% of trades) and match the SWIFT top-10 payments set; NZD added as the remaining freely-traded Oceanic currency; ZAR added per explicit requirement (also SSA-relevant). INR/KRW/MXN and below cut off at ≤1.9% turnover — extend later if needed.
- **Explicit PKs 1–12 in BIS-turnover order** (USD=1, EUR=2, JPY=3, GBP=4, CNY=5, CHF=6, AUD=7, CAD=8, HKD=9, SGD=10, NZD=11, ZAR=12). Rationale: ranking order is self-documenting; PKs carry no ordering semantics anyway (model orders by `code`). Matches the explicit-PK pattern of all Phase 1 fixtures.
- **Country links cover every using country, verified against the Country fixture (zero missing PKs)**: USD→US+8 dollarized states (EC, SV, ZW, PA, TL, MH, FM, PW); EUR→all 20 Eurozone members; ZAR→ZA+LS+NA+SZ (Common Monetary Area); CHF→CH+LI; AUD→AU+KI+NR+TV; NZD→NZ+CK+NU+PN+TK; JPY/CNY/GBP/CAD/HKD/SGD single-link. Rationale: the M2M finally tells the truth for shared currencies.
- **Rates as starting defaults (Fed G.5 Aug-2026 where available; SGD/NZD/ZAR approximate)** over live-rate fetching. Rationale: fixtures are static; live rates need a job/command, which is future scope if ever.
- **Django serialization format (`model: ourlives.Currency`, M2M as PK lists)** over natural keys. Rationale: matches all existing fixtures; `loaddata` bypasses `Model.save()`, so values must be DB-ready (decimals as strings).
- **No loader edit.** Rationale: `base_loaddata` auto-discovers; sorted order already puts `Currency.json` after `Country.json` (verified against fixture dir listing).

## Risks / Trade-offs

- [Risk] Static rates drift from reality → Mitigation: documented as starting defaults; editable in admin; live-rate sync is future scope.
- [Risk] Explicit PKs could collide with user-created rows on existing DBs → Mitigation: same pattern as all Phase 1 fixtures (`loaddata` updates in place on PK match); fresh builds unaffected, existing DBs gain/refresh the 12 rows.

## Migration Plan

No migration (data-only change). Deploy: fixture loads on next `base_loaddata` run (every build/deploy). Rollback: delete the 12 rows or revert the JSON file.

## Open Questions

None. Currency set (12, researcher-backed) and no-Product-fixture were user-confirmed.
