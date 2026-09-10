## 1. Lookup admins (Currency, Product)

- [x] 1.1 Add `CurrencyAdmin` + `ProductAdmin` to `ourlives/admin.py` per spec (icons, list_display/filter/search, `list_editable`, `filter_horizontal`, autocomplete on `Product.currency`)
- [x] 1.2 Verify `/admin/ourlives/currency/` and `/product/` render with filters, search, and Excel export actions

## 2. Relational admins (Contact, OrganizationAddress)

- [x] 2.1 Add `ContactAdmin` + `OrganizationAddressAdmin` per spec (filters, autocomplete over org/type/country, `list_editable(is_primary)`)
- [x] 2.2 Verify autocomplete widgets resolve (relies on `search_fields` from 1.1) and changelist search works

## 3. Core admins (Order, OrderItem + inline)

- [x] 3.1 Add `OrderItemInline(TabularInline)` + `OrderItemAdmin` per spec (readonly `line_total_display`, autocomplete order/product)
- [x] 3.2 Add `OrderAdmin` per spec (M2M `filter_horizontal`, `date_hierarchy`, `list_select_related` + `get_queryset` prefetch of `order_types`, readonly computed `total_agreed_price_display` / `is_pilot_order_display`, all concrete fields editable, inline)
- [x] 3.3 Verify order changelist/form: computed columns, type filter, inline item editing, no N+1 (select/prefetch related)

## 4. Tests and checks

- [x] 4.1 Extend `ourlives/tests.py` admin tests: per-model `list_display`/`list_filter`/`search_fields`/`autocomplete_fields`, inline + `filter_horizontal` presence, readonly computed fields, inherited `export_all` action
- [x] 4.2 Run `python manage.py check`, `runtests ourlives`, and `makemigrations --check --dry-run` (expect no model changes)
