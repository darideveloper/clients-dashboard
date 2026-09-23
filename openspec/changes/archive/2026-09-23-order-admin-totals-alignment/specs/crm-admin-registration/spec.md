## MODIFIED Requirements

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