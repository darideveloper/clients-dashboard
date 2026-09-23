## 1. Inline action column and order

- [x] 1.1 Add readonly `order_link` (blank header, permission-aware Change/View, blank for unsaved rows) as last column; set `show_change_link=False`
- [x] 1.2 Reorder `OrganizationAdmin.inlines` to `(OrgOrderInline, ContactInline, OrganizationAddressInline)`

## 2. Verification

- [x] 2.1 Extend inline assertions (4-tuple fields, `show_change_link is False`) and rendered-content tests (trailing action link, label per permission, Orders section first)
- [x] 2.2 Run `python manage.py check` and the `ourlives` test suite; verify detail page renders
