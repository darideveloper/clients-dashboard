# crm-admin-registration Specification

## Purpose
Admin registration and changelist behavior for the six Phase-2/3 CRM models (`Currency`, `Product`, `Contact`, `OrganizationAddress`, `Order`, `OrderItem`) plus Unfold inlines for child editing on the parent change forms (see `admin-inline-children`). Created by archiving change register-missing-crm-admins; inline coexistence by change admin-inline-models-sidebar; structured Order filters by change improve-order-admin-filters.
## Requirements
### Requirement: Currency admin registration

The system SHALL register `Currency` in `ourlives/admin.py` as `CurrencyAdmin(OurlivesModelAdminBase)` with `sidebar_icon="payments"`, `list_display=("code","name","exchange_rate","active")`, `list_display_links=("code",)`, `list_filter=("active","countries")`, `search_fields=("^code","name")`, `list_editable=("active",)`, `filter_horizontal=("countries",)` and full add/change/delete permissions.

#### Scenario: Currency changelist renders

- **WHEN** a staff user with `ourlives` view permission opens `/admin/ourlives/currency/`
- **THEN** rows show code, name, exchange rate and active flag with prefix search over code plus name search, filters for active and countries, and inline active toggles

### Requirement: Product admin registration

The system SHALL register `Product` in `ourlives/admin.py` as `ProductAdmin(OurlivesModelAdminBase)` with `sidebar_icon="inventory_2"`, `list_display=("name","tier","currency","unit_price","active")`, `list_display_links=("name",)`, `list_filter=("active","tier","currency")`, `search_fields=("name","tier","description")`, `autocomplete_fields=("currency",)`, `list_editable=("active",)` and full add/change/delete permissions.

#### Scenario: Product filtered by currency

- **WHEN** a staff user filters the Product changelist by a currency
- **THEN** only products priced in that currency are shown and currency renders as an autocomplete widget in the change form

#### Scenario: Product found by description not currency text

- **WHEN** a staff user searches a description word in `/admin/ourlives/product/`
- **THEN** matching products are returned
- **WHEN** a staff user wants products of one currency
- **THEN** the currency `list_filter` (not search) narrows the changelist

### Requirement: Contact admin registration

The system SHALL register `Contact` in `ourlives/admin.py` as `ContactAdmin(OurlivesModelAdminBase)` with `sidebar_icon="contact_mail"`, `list_display=("first_name","last_name","email","organization","contact_type")`, `list_display_links=("first_name",)`, `list_filter=("contact_type","organization")`, `search_fields=("first_name","last_name","email","phone","organization__name")`, `autocomplete_fields=("organization","contact_type")` and full add/change/delete permissions. Contacts are additionally editable via `ContactInline` on the Organization change form (see `admin-inline-children`).

#### Scenario: Contact search across org

- **WHEN** a staff user searches "acme" in the Contact changelist
- **THEN** contacts whose own name/email/phone or organization name matches are returned

#### Scenario: Contact type via filter not search

- **WHEN** a staff user wants contacts of one type
- **THEN** the `contact_type` `list_filter` narrows the changelist (no `contact_type__` entry exists in search)

### Requirement: OrganizationAddress admin registration

The system SHALL register `OrganizationAddress` in `ourlives/admin.py` as `OrganizationAddressAdmin(OurlivesModelAdminBase)` with `sidebar_icon="location_on"`, `list_display=("organization","line1","city","country","is_primary")`, `list_display_links=("line1",)`, `list_filter=("is_primary","country","organization")`, `search_fields=("line1","line2","city","state","zip","organization__name")`, `autocomplete_fields=("organization","country")`, `list_editable=("is_primary",)` and full add/change/delete permissions. Addresses are additionally editable via `OrganizationAddressInline` on the Organization change form (see `admin-inline-children`).

#### Scenario: Primary address toggle

- **WHEN** a staff user flips `is_primary` on an address row and saves the changelist
- **THEN** the change persists without opening the detail form

#### Scenario: Address found by second line

- **WHEN** a staff user searches a `line2` fragment (e.g. suite/apartment) in `/admin/ourlives/organizationaddress/`
- **THEN** matching addresses are returned alongside line1/city/state/zip/org matches

### Requirement: Order admin registration with inline items

The system SHALL register `Order` in `ourlives/admin.py` as `OrderAdmin(OurlivesModelAdminBase)` with `sidebar_icon="receipt"`, `list_display=("order_number","organization","rep","po_number","total_order_value_display","submitted_at","usage_pct_display")`, `list_display_links=("order_number",)`, `list_filter` ordered exactly as Company (`organization` autocomplete filter), Rep (autocomplete filter), Primary contact (autocomplete filter), Invoice contact (autocomplete filter), Product (custom single-select filter over `items__product`, all products), Submitted range (`RangeDateTimeFilter` on `submitted_at`), Referral text (free-text contains filter on `referral_organisation`), then the existing flags (`order_types`, `hcaptcha_verified`, `is_upgrade_from_pilot`, `is_referral_order`), then `currency` and `pilot_currency` active-only plain dropdowns, then the usage filters (`UsageBucketFilter`, `UsageMinFilter`, `UsageMaxFilter`) dead last, `list_filter_submit=True`, `search_fields=("^order_number","^po_number","organization__name","rep__first_name","rep__last_name","rep__email","primary_contact__last_name","primary_contact__email","invoice_contact__last_name","invoice_contact__email","referral_organisation")`, `search_help_text` naming order/PO/org/rep/contact/referral coverage, `autocomplete_fields=("organization","rep","primary_contact","invoice_contact","currency","pilot_currency")`, `filter_horizontal=("order_types",)`, `date_hierarchy="submitted_at"`, `list_select_related` over the FKs plus a `get_queryset` override prefetching `order_types` and `items__product__currency`, `inlines=(OrderItemInline,)`, and readonly `total_agreed_price_display`, `catalog_items_total_display`, `total_order_value_display`, `is_pilot_order_display`, `submitted_at` (all concrete fields editable). The admin SHALL expose the three money figures as `@admin.display` readonlys — `total_agreed_price_display` (model `total_agreed_price`, label "Agreed scans total"), `catalog_items_total_display` (`Σ quantity × unit_price` over items, label "Catalog items total"), and `total_order_value_display` (model `total_order_value`, label "Total Order Value") — plus `is_pilot_order_display` (model `is_pilot_order`). The "Terms" fieldset SHALL list the three money figures in org-summary order (`total_agreed_price_display`, `catalog_items_total_display`, `total_order_value_display`), while the changelist SHALL show only `total_order_value_display` (the final total, non-sortable).

#### Scenario: Order hub renders computed columns

- **WHEN** a staff user opens `/admin/ourlives/order/`
- **THEN** each row shows the final `Total Order Value` (not the agreed-only figure) and the pilot flag computed from the model with prefix search over order/PO numbers plus org/rep/contact/referral search and the full ordered filter set (company/rep/contacts/product/date-range/referral-text/flags/currencies/usage)

#### Scenario: Order change form edits types and items inline

- **WHEN** a staff user opens an Order change form
- **THEN** `order_types` renders as a horizontal filter widget, FKs render as autocomplete, the three money totals and pilot flag render readonly in the "Terms" fieldset, and related OrderItems are editable inline

#### Scenario: Money figure labels align with org admin

- **WHEN** a staff user views the Order list or change form
- **THEN** the money columns render "Agreed scans total", "Catalog items total", and "Total Order Value" with the same `CODE amount` formatting and currency fallback (order → pilot → product → `No Currency`) as the org admin, with `—` when the amount is zero

### Requirement: OrderItem admin registration and inline

The system SHALL register `OrderItem` in `ourlives/admin.py` as `OrderItemAdmin(OurlivesModelAdminBase)` with `sidebar_icon="list_alt"`, `list_display=("order","product","quantity","unit_price","line_total_display")`, `list_display_links=("order",)`, `list_filter=("product",)`, `search_fields=("^order__order_number","product__name")`, `autocomplete_fields=("order","product")` and a readonly `line_total_display` (`@admin.display` over model `line_total`). The system SHALL also provide `OrderItemInline(unfold.admin.TabularInline)` with `extra=0`, `autocomplete_fields=("product",)` and readonly `line_total_display`, registered inside `OrderAdmin.inlines`.

#### Scenario: Item line total shown

- **WHEN** a staff user opens the OrderItem changelist or an Order change form
- **THEN** each item shows `quantity × unit_price` as a readonly line total with order/product autocomplete in the form

