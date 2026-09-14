# admin-inline-children Specification

## Purpose
Inline-only editing of Contact, OrganizationAddress, and OrderItem via their parent Organization/Order change forms with no standalone changelists.
## Requirements
### Requirement: Contact inline on Organization

The system SHALL provide `ContactInline(unfold.admin.StackedInline)` in `ourlives/admin.py` with `model=Contact`, `extra=0`, `autocomplete_fields=("contact_type",)`, full add/change/delete through the parent, and NO standalone `ContactAdmin` registration. (No `tab` attribute: Unfold 0.77 auto-renders inlines as change-form tabs.) `OrganizationAdmin` SHALL include it in `inlines`.

#### Scenario: Contacts edited on Organization page

- **WHEN** a staff user with Organization change and Contact add/change permission opens an Organization change form
- **THEN** existing contacts render as stacked editable rows grouped under a Contacts tab with `contact_type` as autocomplete, plus zero empty extra rows

#### Scenario: Contact without model permission sees no inline rows

- **WHEN** a staff user with Organization view permission but no Contact permissions opens an Organization change form
- **THEN** no editable Contact rows are shown (Django inline permission gating)

#### Scenario: Standalone Contact changelist gone

- **WHEN** any user requests `/admin/ourlives/contact/` or `/admin/ourlives/contact/add/`
- **THEN** the response is 404 (model unregistered)

### Requirement: OrganizationAddress inline on Organization

The system SHALL provide `OrganizationAddressInline(unfold.admin.StackedInline)` in `ourlives/admin.py` with `model=OrganizationAddress`, `extra=0`, `autocomplete_fields=("country",)`, full add/change/delete through the parent, and NO standalone `OrganizationAddressAdmin` registration. (No `tab` attribute: Unfold 0.77 auto-renders inlines as change-form tabs.) `OrganizationAdmin` SHALL include it in `inlines` alongside `ContactInline`.

#### Scenario: Addresses edited on Organization page

- **WHEN** a staff user with Organization change and OrganizationAddress add/change permission opens an Organization change form
- **THEN** existing addresses render as stacked editable rows grouped under an Addresses tab with `country` as autocomplete, including the `is_primary` flag

#### Scenario: Standalone address changelist gone

- **WHEN** any user requests `/admin/ourlives/organizationaddress/`
- **THEN** the response is 404 (model unregistered)

### Requirement: OrderItem Unfold inline without standalone admin

The system SHALL provide `OrderItemInline(unfold.admin.TabularInline)` (migrated from `django.contrib.admin.TabularInline`) with `model=OrderItem`, `extra=0`, `autocomplete_fields=("product",)`, readonly `line_total_display` (`@admin.display` over model `line_total`), full add/change/delete through the parent, and NO standalone `OrderItemAdmin` registration. `OrderAdmin.inlines` SHALL equal `(OrderItemInline,)`.

#### Scenario: Line items edited on Order page with Unfold styling

- **WHEN** a staff user opens an Order change form
- **THEN** items render as Unfold-styled tabular rows with product autocomplete and readonly `quantity × unit_price` line totals, plus zero empty extra rows

#### Scenario: Standalone OrderItem changelist gone

- **WHEN** any user requests `/admin/ourlives/orderitem/`
- **THEN** the response is 404 (model unregistered)
