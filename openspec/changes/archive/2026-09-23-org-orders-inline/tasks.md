## 1. Orders inline

- [x] 1.1 Add display-only `OrgOrderInline` (Unfold tabular, `order_number`/`number_of_scans`/`submitted_at` readonly, `extra=0`, no add/delete, change links) and register it on `OrganizationAdmin`
- [x] 1.2 Delete `orders_list` and remove it from `fieldsets`/`readonly_fields`
- [x] 1.3 Add readonly `total_scans_display` (`Total: N scans across M orders`, nulls as 0, full-queryset aggregate, count-only without view permission) to `fieldsets`/`readonly_fields`

## 2. Verification

- [x] 2.1 Update detail-view tests asserting old `orders_list` strings; add tests for inline columns, null-scan `—`, and total line
- [x] 2.2 Run `python manage.py check` and the `ourlives` test suite; verify detail page renders
