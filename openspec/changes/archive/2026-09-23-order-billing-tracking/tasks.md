## 1. Model + migration

- [x] 1.1 Add 6 fields to `Order` in `ourlives/models.py` (`invoice_sent/_on`, `invoice_paid/_on`, `commission_paid/_on`; bools default False, dates null+blank)
- [x] 1.2 Generate migration (`makemigrations ourlives`) and verify `migrate` applies cleanly

## 2. Admin detail page

- [x] 2.1 Add `Billing` fieldset to `OrderAdmin` between `Terms` and `Details` with the 6 fields; confirm no `list_display`/`list_filter`/`search_fields` changes

## 3. Tests + verification

- [x] 3.1 Add model tests: defaults falsy/empty, tick-without-date persists, date-without-tick persists (no auto-tick)
- [x] 3.2 Add admin test: Billing section renders on change page; changelist has no billing columns/filters
- [x] 3.3 Run relevant test suite and `migrate`; verify Excel export includes new columns via existing mixins
