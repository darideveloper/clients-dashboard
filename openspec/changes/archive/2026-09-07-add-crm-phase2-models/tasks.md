## 1. Models

- [x] 1.1 Append `Currency` to `ourlives/models.py` after `OrderType` (code UK, name, symbol_left/right blank=True, exchange_rate 10,2, country FK nullable SET_NULL related_name="currencies", active, ordering by code, `__str__` → code)
- [x] 1.2 Append `Product` (currency FK PROTECT related_name="products", name, tier free-text blank=True, unit_price 10,2, active, description, ordering by name, `__str__` → name)
- [x] 1.3 Append `Contact` (organization FK CASCADE related_name="contacts", contact_type FK PROTECT related_name="contacts", first/last name, email EmailField non-unique, phone blank=True, ordering by last_name/first_name, `__str__` → "First Last")
- [x] 1.4 Append `OrganizationAddress` (organization FK CASCADE related_name="addresses", country FK PROTECT related_name="organization_addresses", line1, line2 blank=True, city, state blank=True, zip, is_primary default False, ordering by -is_primary/city, `__str__` → "line1, city")

## 2. Migration

- [x] 2.1 Run `makemigrations ourlives` and verify single `0010_*` depending on `0009_codetype_contacttype_country_ordertype_rep`
- [x] 2.2 Run `migrate` and confirm clean apply (rollback check: `migrate ourlives 0009` then forward, optional)

## 3. Tests

- [x] 3.1 Add `CurrencyTests` to `ourlives/tests.py` (create with country, create without country, country delete → SET_NULL survives, duplicate code → IntegrityError)
- [x] 3.2 Add `ProductTests` (create with currency, delete currency with products → ProtectedError)
- [x] 3.3 Add `ContactTests` (create with org + type, org delete → CASCADE removes contacts, delete type with contacts → ProtectedError)
- [x] 3.4 Add `OrganizationAddressTests` (create, is_primary=True filter returns primary only, delete country with addresses → ProtectedError, org delete → CASCADE removes addresses)
- [x] 3.5 Run full test suite and confirm no regressions
