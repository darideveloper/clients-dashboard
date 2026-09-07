## Why

The `Currency.country` FK (nullable, SET_NULL) forces a falsehood for every shared currency: EUR had to point at a single arbitrary country (DE) when ~20 Eurozone states use it, and the same lie awaits USD (EC, SV, ZW, …). A many-to-many relationship models shared currencies truthfully and powers correct "which currencies for this country?" queries for the future order form.

## What Changes

- Replace `Currency.country` FK with `Currency.countries` M2M (`blank=True`, `related_name="currencies"`); Django auto-creates junction table `ourlives_currency_countries`.
- Add forward migration `0011_*` (remove FK, add M2M). No rewrite of pushed `0010` — the table is still empty.
- Rewrite the two FK-shaped `CurrencyTests` (SET_NULL survival → junction-row cleanup on country delete; add shared-currency and reverse-accessor tests).
- Update the still-open `add-currency-fixture` artifacts to M2M (multi-link EUR) so it applies cleanly on top.

## Capabilities

### New Capabilities

- None. No new behavior surface; this is a relationship-shape correction.

### Modified Capabilities

- `crm-phase2-core-models`: Currency requirement changes from single nullable `country` FK (SET_NULL) to `countries` M2M; scenarios updated (shared currency, country-delete junction cleanup, per-country currency query).

## Impact

- `ourlives/models.py`: one field replaced on `Currency`.
- `ourlives/migrations/0011_*`: new forward migration.
- `ourlives/tests.py`: `CurrencyTests` rewritten (no other test class touches `Currency.country`).
- Open change `add-currency-fixture` (unapplied): its spec/design/tasks must be reworded to M2M before `/opsx-apply` runs on it.
- Junction table appears in a future `build_full_app_workbook()` export automatically (model discovery); no admin changes in scope.
