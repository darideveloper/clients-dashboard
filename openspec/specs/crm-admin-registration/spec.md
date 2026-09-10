# crm-admin-registration Specification

## Purpose
Admin registration and changelist behavior for the six Phase-2/3 CRM models (`Currency`, `Product`, `Contact`, `OrganizationAddress`, `Order`, `OrderItem`) plus the `OrderItem` tabular inline. Created by archiving change register-missing-crm-admins.
## Requirements
### Requirement: Currency admin registration

The system SHALL register `Currency` in `ourlives/admin.py` as `CurrencyAdmin(OurlivesModelAdminBase)` with `sidebar_icon="payments"`, `list_display=("code","name","exchange_rate","active")`, `list_display_links=("code",)`, `list_filter=("active","countries")`, `search_fields=("code","name")`, `list_editable=("active",)`, `filter_horizontal=("countries",)` and full add/change/delete permissions.

#### Scenario: Currency changelist renders

- **WHEN** a staff user with `ourlives` view permission opens `/admin/ourlives/currency/`
- **THEN** rows show code, name, exchange rate and active flag with search over code/name, filters for active and countries, and inline active toggles

### Requirement: Product admin registration

The system SHALL register `Product` in `ourlives/admin.py` as `ProductAdmin(OurlivesModelAdminBase)` with `sidebar_icon="inventory_2"`, `list_display=("name","tier","currency","unit_price","active")`, `list_display_links=("name",)`, `list_filter=("active","tier","currency")`, `search_fields=("name","tier","currency__code","currency__name")`, `autocomplete_fields=("currency",)`, `list_editable=("active",)` and full add/change/delete permissions.

#### Scenario: Product filtered by currency

- **WHEN** a staff user filters the Product changelist by a currency
- **THEN** only products priced in that currency are shown and currency renders as an autocomplete widget in the change form

### Requirement: Contact admin registration

The system SHALL register `Contact` in `ourlives/admin.py` as `ContactAdmin(OurlivesModelAdminBase)` with `sidebar_icon="contact_mail"`, `list_display=("first_name","last_name","email","organization","contact_type")`, `list_display_links=("first_name",)`, `list_filter=("contact_type","organization")`, `search_fields=("first_name","last_name","email","organization__name")`, `autocomplete_fields=("organization","contact_type")` and full add/change/delete permissions.

#### Scenario: Contact search across org

- **WHEN** a staff user searches "acme" in the Contact changelist
- **THEN** contacts whose own name/email or organization name matches are returned

### Requirement: OrganizationAddress admin registration

The system SHALL register `OrganizationAddress` in `ourlives/admin.py` as `OrganizationAddressAdmin(OurlivesModelAdminBase)` with `sidebar_icon="location_on"`, `list_display=("organization","line1","city","country","is_primary")`, `list_display_links=("line1",)`, `list_filter=("is_primary","country","organization")`, `search_fields=("line1","city","state","zip","organization__name","country__name")`, `autocomplete_fields=("organization","country")`, `list_editable=("is_primary",)` and full add/change/delete permissions.

#### Scenario: Primary address toggle

- **WHEN** a staff user flips `is_primary` on an address row and saves the changelist
- **THEN** the change persists without opening the detail form

### Requirement: Order admin registration with inline items

The system SHALL register `Order` in `ourlives/admin.py` as `OrderAdmin(OurlivesModelAdminBase)` with `sidebar_icon="receipt"`, `list_display=("order_number","organization","rep","po_number","total_agreed_price_display","is_pilot_order_display","hcaptcha_verified","submitted_at")`, `list_display_links=("order_number",)`, `list_filter=("order_types","rep","currency","hcaptcha_verified","is_upgrade_from_pilot","is_referral_order")`, `search_fields=("order_number","po_number","organization__name","rep__first_name","rep__last_name","rep__email")`, `autocomplete_fields=("organization","rep","primary_contact","invoice_contact","currency","pilot_currency")`, `filter_horizontal=("order_types",)`, `date_hierarchy="submitted_at"`, `list_select_related` over the FKs plus a `get_queryset` override prefetching `order_types`, `inlines=(OrderItemInline,)` and readonly `total_agreed_price_display`, `is_pilot_order_display` (all concrete fields editable). The admin SHALL expose `total_agreed_price_display` (model `total_agreed_price`) and `is_pilot_order_display` (model `is_pilot_order`) as `@admin.display` readonly columns.

#### Scenario: Order hub renders computed columns

- **WHEN** a staff user opens `/admin/ourlives/order/`
- **THEN** each row shows the agreed-price total and pilot flag computed from the model with search over order number/PO/org/rep and type/rep/currency/flag filters

#### Scenario: Order change form edits types and items inline

- **WHEN** a staff user opens an Order change form
- **THEN** `order_types` renders as a horizontal filter widget, FKs render as autocomplete, computed price/pilot columns are readonly, and related OrderItems are editable inline

### Requirement: OrderItem admin registration and inline

The system SHALL register `OrderItem` in `ourlives/admin.py` as `OrderItemAdmin(OurlivesModelAdminBase)` with `sidebar_icon="list_alt"`, `list_display=("order","product","quantity","unit_price","line_total_display")`, `list_display_links=("order",)`, `list_filter=("product",)`, `search_fields=("order__order_number","product__name")`, `autocomplete_fields=("order","product")` and a readonly `line_total_display` (`@admin.display` over model `line_total`). The system SHALL also provide `OrderItemInline(admin.TabularInline)` with `extra=0`, `autocomplete_fields=("product",)` and readonly `line_total_display`, registered inside `OrderAdmin.inlines`.

#### Scenario: Item line total shown

- **WHEN** a staff user opens the OrderItem changelist or an Order change form
- **THEN** each item shows `quantity × unit_price` as a readonly line total with order/product autocomplete in the form
