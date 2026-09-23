## 1. Admin list reshape

- [x] 1.1 Set `OrganizationAdmin.list_display` to `("name", "order_count_display", "rep_link", "last_order_date_display", "usage_pct_display", "combined_total_display")`
- [x] 1.2 Add `rep_link` display method (linked "First Last", `—` fallback), `usage_pct_display` dummy (`0%` + ponytail comment), and `list_select_related = ("assigned_rep",)`
- [x] 1.3 Confirm detail `fieldsets`/`readonly_fields` still expose the five order summaries unchanged

## 2. Verification

- [x] 2.1 Add/extend admin display tests for the 6-column list, rep link, combined total last, and `0%` dummy
- [x] 2.2 Run `python manage.py check` and the `ourlives` test subset; verify changelist renders
