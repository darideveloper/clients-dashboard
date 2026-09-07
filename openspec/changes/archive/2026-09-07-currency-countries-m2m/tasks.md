## 1. Model + migration

- [x] 1.1 Replace `Currency.country` FK with `countries = models.ManyToManyField(Country, related_name="currencies", blank=True)` in `ourlives/models.py`
- [x] 1.2 Run `makemigrations ourlives`, verify single `0011_*` (RemoveField `country`, AddField `countries`)
- [x] 1.3 Run `migrate` with rollback round-trip (`migrate ourlives 0010` then forward) and confirm clean apply

## 2. Tests

- [x] 2.1 Rewrite `CurrencyTests` in `ourlives/tests.py` (create with countries, no countries valid, shared EUR across DE+FR incl. reverse accessor, country delete removes link only, duplicate code → IntegrityError)
- [x] 2.2 Run full test suite and `makemigrations --check`; confirm green and in sync

## 3. Follow-up artifact update (same session, after archive)

- [x] 3.1 Reword open change `add-currency-fixture` artifacts (spec/design/tasks) from `country` FK to `countries` M2M with multi-link EUR before it applies
