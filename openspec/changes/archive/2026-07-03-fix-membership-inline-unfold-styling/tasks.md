## 1. Admin Fix

- [x] 1.1 Add `from unfold.admin import StackedInline as UnfoldStackedInline` to imports in `core/admin.py`
- [x] 1.2 Change `MembershipInline` base class from `admin.StackedInline` to `UnfoldStackedInline` at `core/admin.py:57`

## 2. Verification

- [x] 2.1 Run `python manage.py test` — confirm zero regressions
- [x] 2.2 Manual smoke: superuser edits a user → confirm brand inline renders with Unfold styling (consistent borders, Tailwind spacing, matches rest of form)
- [x] 2.3 Manual smoke: staff user edits a user → confirm no brand inline visible (unchanged behavior)
