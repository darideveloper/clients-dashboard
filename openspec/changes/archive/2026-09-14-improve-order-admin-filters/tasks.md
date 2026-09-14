## 1. Verify toolkit

- [x] 1.1 Confirm `RangeDateTimeFilter`, `AutocompleteSelectFilter`, `RelatedDropdownFilter`, `FieldTextFilter` import from `unfold.contrib.filters.admin` under `venv` (Django 5.2 / Unfold 0.77.1) and that `OrganizationAdmin`, `RepAdmin`, `ContactAdmin` keep qualifying `search_fields`.

## 2. FK + currency filters on OrderAdmin

- [x] 2.1 Switch `organization`, `rep`, `primary_contact`, `invoice_contact` entries to autocomplete-backed filters and `currency`, `pilot_currency` to active-only plain dropdown filters, in the agreed tuple positions (currencies last).
- [x] 2.2 Set `list_filter_submit = True` on `OrderAdmin` only.

## 3. Custom product + referral filters

- [x] 3.1 Add custom single-select product filter class (lookups over all products ordered by name; queryset filters `items__product__id` with conditional `distinct()`).
- [x] 3.2 Add free-text referral filter on `referral_organisation` (`icontains`), keeping `is_referral_order` flag.
- [x] 3.3 Add submitted-at `RangeDateTimeFilter`, keeping `date_hierarchy = "submitted_at"`.

## 4. Verify

- [x] 4.1 Assert `OrderAdmin.list_filter` sidebar order matches the spec sequence (currencies in final two positions).
- [x] 4.2 Exercise each filter axis on a fixture set (company/rep/both contacts/product incl. multi-item order dedup/date window/date-hierarchy drill-down/referral fragment/both currencies incl. inactive-currency exclusion) plus `^order_number` search sanity.
- [x] 4.3 Run the affected test subset and confirm no other admin's filters/search regressed.
