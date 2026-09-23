## 1. Model + migration

- [x] 1.1 Add `rep_commission_note = CharField(max_length=255, blank=True, default="")` to `Order` in `ourlives/models.py` after `commission_paid_on`
- [x] 1.2 Generate migration (`makemigrations ourlives`) and verify `migrate` applies cleanly

## 2. Admin detail page

- [x] 2.1 Add `rep_commission_note` on its own row at the end of the `Billing` fieldset in `OrderAdmin`; confirm no `list_display`/`list_filter`/`search_fields` changes

## 3. Tests + verification

- [x] 3.1 Add model tests: defaults to "", free text persists verbatim
- [x] 3.2 Add/extend admin test: note input renders on change page; changelist has no note column/filter
- [x] 3.3 Run relevant test suite and `migrate`; verify Excel export includes the new column via existing mixins
