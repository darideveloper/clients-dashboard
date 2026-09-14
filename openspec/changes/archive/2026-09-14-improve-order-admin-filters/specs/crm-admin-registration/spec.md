## MODIFIED Requirements

### Requirement: Order admin registration with inline items

The system SHALL register `Order` in `ourlives/admin.py` as `OrderAdmin(OurlivesModelAdminBase)` with `sidebar_icon="receipt"`, `list_display=("order_number","organization","rep","po_number","total_agreed_price_display","is_pilot_order_display","hcaptcha_verified","submitted_at")`, `list_display_links=("order_number",)`, `list_filter` ordered exactly as Company (`organization` autocomplete filter), Rep (autocomplete filter), Primary contact (autocomplete filter), Invoice contact (autocomplete filter), Product (custom single-select filter over `items__product`, all products), Submitted range (`RangeDateTimeFilter` on `submitted_at`), Referral text (free-text contains filter on `referral_organisation`), then the existing flags (`order_types`, `hcaptcha_verified`, `is_upgrade_from_pilot`, `is_referral_order`), then `currency` and `pilot_currency` active-only plain dropdowns dead last, `search_fields=("^order_number","^po_number","organization__name","rep__first_name","rep__last_name","rep__email","primary_contact__last_name","primary_contact__email","invoice_contact__last_name","invoice_contact__email","referral_organisation")`, `search_help_text` naming order/PO/org/rep/contact/referral coverage, `autocomplete_fields=("organization","rep","primary_contact","invoice_contact","currency","pilot_currency")`, `filter_horizontal=("order_types",)`, `date_hierarchy="submitted_at"`, `list_filter_submit=True`, `list_select_related` over the FKs plus a `get_queryset` override prefetching `order_types` (and applying `distinct()` only when the product filter is active), `inlines=(OrderItemInline,)` and readonly `total_agreed_price_display`, `is_pilot_order_display` (all concrete fields editable). The admin SHALL expose `total_agreed_price_display` (model `total_agreed_price`) and `is_pilot_order_display` (model `is_pilot_order`) as `@admin.display` readonly columns.

#### Scenario: Order hub renders computed columns

- **WHEN** a staff user opens `/admin/ourlives/order/`
- **THEN** each row shows the agreed-price total and pilot flag computed from the model with prefix search over order/PO numbers plus org/rep/contact/referral search and the full ordered filter set (company/rep/contacts/product/date-range/referral-text/flags/currencies)

#### Scenario: Order change form edits types and items inline

- **WHEN** a staff user opens an Order change form
- **THEN** `order_types` renders as a horizontal filter widget, FKs render as autocomplete, computed price/pilot columns are readonly, and related OrderItems are editable inline

#### Scenario: Order found by contact or referral

- **WHEN** a staff user searches a billing-contact email or referral name in `/admin/ourlives/order/`
- **THEN** matching orders are returned
- **WHEN** a staff user clicks a `pilot_currency` filter choice
- **THEN** only orders with that pilot currency are shown
