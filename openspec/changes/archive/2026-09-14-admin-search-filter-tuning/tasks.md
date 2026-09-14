## 1. Lookup admins (`ourlives-lookup-admin` delta)

- [x] 1.1 Update `CountryAdmin.search_fields` to `("^iso2","^iso3","name")`
- [x] 1.2 Update `ContactType`/`CodeType`/`OrderType` `search_fields` to `("^code","name","description")`
- [x] 1.3 Update `InvitationCodeAdmin` search + `list_filter += code_type` + `search_help_text`

## 2. CRM admins (`crm-admin-registration` delta)

- [x] 2.1 Update `CurrencyAdmin.search_fields` to `("^code","name")`
- [x] 2.2 Update `ProductAdmin.search_fields` to `("name","tier","description")` (drop currency text, filter covers)
- [x] 2.3 Update `ContactAdmin.search_fields` to add `phone` (no `contact_type__` entries)
- [x] 2.4 Update `OrganizationAddressAdmin.search_fields` to add `line2`, drop `country__name`
- [x] 2.5 Update `OrderAdmin` search + `list_filter += pilot_currency` + `search_help_text`
- [x] 2.6 Update `OrderItemAdmin.search_fields` to `("^order__order_number","product__name")`

## 3. Project / Organization / StripeEvent (`admin-search-filter-tuning`)

- [x] 3.1 Update `ProjectAdmin.search_fields` to `("name","description")`
- [x] 3.2 Update `OrganizationAdmin` search + `list_filter = ("assigned_rep",)`
- [x] 3.3 Add `StripeEventAdmin.search_fields = ("=stripe_event_id","source","presentment_currency")` + `search_help_text`, keep read-only perms

## 4. Verify

- [x] 4.1 Update `ourlives/tests.py` admin assertions for new search/filter/help-text values
- [x] 4.2 Run `python manage.py check`, focused admin tests, and manual changelist search spot-checks per admin
