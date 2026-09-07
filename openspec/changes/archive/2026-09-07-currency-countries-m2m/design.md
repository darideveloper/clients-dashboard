## Context

`Currency.country` is a nullable FK with SET_NULL (`ourlives/models.py:389-395`, migration `0010`, archived spec `crm-phase2-core-models`). It forces one country per currency — false for EUR (~20 Eurozone states), USD, and others. The table is still empty (fixture change `add-currency-fixture` is open but unapplied), and `0010` is pushed, so the correction must be a forward migration. Nothing in code reads `Currency.country` (verified: only `models.py` defines it, `tests.py` exercises it).

## Goals / Non-Goals

**Goals:**
- Truthful shared-currency mapping via auto-created junction table.
- Correct per-country currency queries (`country.currencies.all()`) for the future order form.
- Spec source of truth corrected via MODIFIED delta.

**Non-Goals:**
- Loader/fixture implementation (belongs to `add-currency-fixture`, updated separately); admin registration; live rates.

## Decisions

- **`ManyToManyField(Country, related_name="currencies", blank=True)`** over FK-with-junction-duplication or a hand-rolled through model. Rationale: global decision prefers M2M; no extra junction fields are needed (no `notes`-style payload — unlike `order_order_types`), so Django's auto through table is the laziest correct option. Add an explicit through model only if per-link metadata ever appears.
- **Keep `related_name="currencies"`** over renaming. Rationale: reverse accessor `country.currencies` stays stable; only the cardinality changes.
- **`blank=True`, no `null`** (M2M has no column). Rationale: preserves "currency with no country" validity from the nullable FK.
- **Forward migration `0011_*`, never rewrite `0010`.** Rationale: `0010` is pushed to `main`; empty-table `RemoveField`+`AddField` is lossless here.
- **Country delete semantics fall out naturally**: deleting a country removes junction rows only; currencies survive without any `on_delete` configuration. The old "mixed delete semantics" design risk disappears by construction.

## Risks / Trade-offs

- [Risk] M2M queries are marginally heavier than FK joins → Mitigation: 4-row table; irrelevant at this scale.
- [Risk] Fixture format changes (FK pk → PK list) → Mitigation: `add-currency-fixture` is still unapplied, so its artifacts are edited, not migrated.
- [Risk] Junction table name `ourlives_currency_countries` is Django-default → Mitigation: acceptable; rename only if export naming demands it later.

## Migration Plan

1. Edit `Currency` model field; `makemigrations` → `0011_*`; `migrate` + rollback round-trip check.
2. Rewrite `CurrencyTests`; full suite green; `makemigrations --check` clean.
3. Archive; then reword `add-currency-fixture` artifacts to M2M before it applies.

## Open Questions

None.
