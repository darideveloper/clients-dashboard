## REMOVED Requirements

### Requirement: Contact admin registration

**Reason**: `Contact` is now a child-only model edited exclusively via `ContactInline` on the Organization page; a standalone changelist duplicates the workflow and clutters the sidebar.
**Migration**: Manage contacts on the parent Organization change form; contact data remains in full-app Excel exports (discovered via `apps.get_models()`).

### Requirement: OrganizationAddress admin registration

**Reason**: `OrganizationAddress` is now a child-only model edited exclusively via `OrganizationAddressInline` on the Organization page.
**Migration**: Manage addresses on the parent Organization change form; address data remains in full-app Excel exports.

### Requirement: OrderItem admin registration and inline

**Reason**: `OrderItem` is now a child-only model edited exclusively via the Unfold `OrderItemInline` on the Order page; the standalone changelist and the Django-native inline class are superseded (see `admin-inline-children` capability).
**Migration**: Manage line items on the parent Order change form; item data remains in full-app Excel exports.

## MODIFIED Requirements

### Requirement: Order admin registration with inline items

The system SHALL register `Order` in `ourlives/admin.py` as `OrderAdmin(OurlivesModelAdminBase)` with `sidebar_icon="receipt"`, `list_display=("order_number","organization","rep","po_number","total_agreed_price_display","is_pilot_order_display","hcaptcha_verified","submitted_at")`, `list_display_links=("order_number",)`, `list_filter=("order_types","rep","currency","pilot_currency","hcaptcha_verified","is_upgrade_from_pilot","is_referral_order")`, `search_fields=("^order_number","^po_number","organization__name","rep__first_name","rep__last_name","rep__email","primary_contact__last_name","primary_contact__email","invoice_contact__last_name","invoice_contact__email","referral_organisation")`, `search_help_text` naming order/PO/org/rep/contact/referral coverage, `autocomplete_fields=("organization","rep","currency","pilot_currency")` (contact autocompletes removed — `Contact` is unregistered so Django autocomplete cannot target it; `primary_contact`/`invoice_contact` render as plain selects), `filter_horizontal=("order_types",)`, `date_hierarchy="submitted_at"`, `list_select_related` over the FKs plus a `get_queryset` override prefetching `order_types`, `inlines=(OrderItemInline,)` and readonly `total_agreed_price_display`, `is_pilot_order_display` (all concrete fields editable). The admin SHALL expose `total_agreed_price_display` (model `total_agreed_price`) and `is_pilot_order_display` (model `is_pilot_order`) as `@admin.display` readonly columns.

#### Scenario: Order hub renders computed columns

- **WHEN** a staff user opens `/admin/ourlives/order/`
- **THEN** each row shows the agreed-price total and pilot flag computed from the model with prefix search over order/PO numbers plus org/rep/contact/referral search and type/rep/currency/pilot-currency/flag filters

#### Scenario: Order change form edits types and items inline

- **WHEN** a staff user opens an Order change form
- **THEN** `order_types` renders as a horizontal filter widget, organization/rep/currency FKs render as autocomplete, primary/invoice contacts render as plain selects, computed price/pilot columns are readonly, and related OrderItems are editable inline

#### Scenario: Order found by contact or referral

- **WHEN** a staff user searches a billing-contact email or referral name in `/admin/ourlives/order/`
- **THEN** matching orders are returned
- **WHEN** a staff user clicks a `pilot_currency` filter choice
- **THEN** only orders with that pilot currency are shown
