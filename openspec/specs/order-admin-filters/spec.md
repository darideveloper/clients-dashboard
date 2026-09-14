# order-admin-filters Specification

## Purpose
TBD - created by archiving change improve-order-admin-filters. Update Purpose after archive.
## Requirements
### Requirement: Order company and rep autocomplete filters

The system SHALL expose `organization` (Company) and `rep` filters on the `Order` changelist as autocomplete-backed select filters (from `unfold.contrib.filters`, no new dependencies), resolving options by querying on type against the related admins' existing `search_fields`.

#### Scenario: Filter orders by company

- **WHEN** a staff user selects an Organization in the Company filter on `/admin/ourlives/order/`
- **THEN** only orders with that `organization` are shown

#### Scenario: Filter orders by rep

- **WHEN** a staff user selects a Rep in the Rep filter on `/admin/ourlives/order/`
- **THEN** only orders with that `rep` are shown

### Requirement: Order primary and invoice contact filters

The system SHALL expose two separate autocomplete-backed filters on the `Order` changelist, one for `primary_contact` and one for `invoice_contact`, each narrowing on its own FK independently so the two compose via AND.

#### Scenario: Filter by primary contact

- **WHEN** a staff user selects a Contact in the primary-contact filter
- **THEN** only orders with that `primary_contact` are shown, regardless of `invoice_contact`

#### Scenario: Filter by invoice contact

- **WHEN** a staff user selects a Contact in the invoice-contact filter
- **THEN** only orders with that `invoice_contact` are shown, regardless of `primary_contact`

#### Scenario: Both contact filters compose

- **WHEN** a staff user sets both the primary-contact and invoice-contact filters
- **THEN** only orders matching both are shown

### Requirement: Order product single-select filter via order items

The system SHALL expose a single-select Product filter on the `Order` changelist backed by a custom filter class that lists all `Product` rows (active and inactive, ordered by name) and narrows the queryset via `items__product`. The filter SHALL apply `.distinct()` only when its parameter is active, so unfiltered loads pay no dedup cost and filtered counts contain no JOIN duplicates.

#### Scenario: Filter orders by product

- **WHEN** a staff user selects a Product in the product filter
- **THEN** only orders having at least one `OrderItem` for that product are shown

#### Scenario: Inactive products remain selectable

- **WHEN** a staff user opens the product filter options
- **THEN** inactive products are listed alongside active ones

#### Scenario: No duplicate rows under product filter

- **WHEN** a staff user filters by a product on an order that has multiple items of that product
- **THEN** the order appears exactly once and the changelist total equals the distinct order count

### Requirement: Order submitted-at datetime range filter

The system SHALL expose a `RangeDateTimeFilter` on `submitted_at` on the `Order` changelist with `list_filter_submit = True` set on `OrderAdmin`, while keeping the existing `date_hierarchy = "submitted_at"` drill-down.

#### Scenario: Filter orders by submitted window

- **WHEN** a staff user enters a from/to datetime range and applies the filter
- **THEN** only orders with `submitted_at` inside the window are shown

#### Scenario: Date hierarchy still drills down

- **WHEN** a staff user clicks a year/month/day in the date hierarchy
- **THEN** the changelist narrows by that date as before

### Requirement: Order referral-organisation free-text filter

The system SHALL expose a free-text contains-search filter on `referral_organisation` on the `Order` changelist (match on `icontains`), leaving the existing `is_referral_order` boolean filter in place so the two compose.

#### Scenario: Find orders by referral name fragment

- **WHEN** a staff user types a referral-name fragment into the referral filter and applies it
- **THEN** only orders whose `referral_organisation` contains the fragment (case-insensitive) are shown

### Requirement: Currency filters sit at the bottom in fixed sidebar order

The system SHALL order `OrderAdmin.list_filter` exactly as: Company (`organization`), Rep, Primary contact, Invoice contact, Product, Submitted range, Referral text, then the existing flags (`order_types`, `hcaptcha_verified`, `is_upgrade_from_pilot`, `is_referral_order`), then `currency` and `pilot_currency` dead last as plain dropdowns. Currency dropdowns SHALL list only active `Currency` rows (`active=True`, ordered by code).

#### Scenario: Sidebar order matches the agreed sequence

- **WHEN** the test suite inspects `OrderAdmin.list_filter` order
- **THEN** the filter entries appear in the agreed sequence with both currency filters in the final two positions

#### Scenario: Filter by main currency

- **WHEN** a staff user selects a Currency in the bottom currency filter
- **THEN** only orders with that `currency` are shown

#### Scenario: Inactive currencies are not listed

- **WHEN** a staff user opens either bottom currency filter
- **THEN** inactive currencies are absent from the options

### Requirement: Order-ID search coverage (verify-only)

No search change is introduced by this capability. The existing `^order_number` search SHALL keep resolving order-ID lookups.

#### Scenario: Order-ID search still works

- **WHEN** a staff user types an order number into the changelist search box
- **THEN** the existing `^order_number` search returns the matching order

