# org-orders-inline Specification

## Purpose
Display-only tabular Orders inline on the Organization detail page showing only relevant columns (`order_number`, `number_of_scans`, `submitted_at`), plus a readonly total-scans line. Replaces the hand-rolled `orders_list` HTML section.
## Requirements
### Requirement: Orders inline table

The system SHALL render a display-only tabular Orders inline on the Organization change page with exactly the columns `order_number`, `number_of_scans`, `submitted_at`, and a trailing action column with a blank header, plus a per-row link to each Order change page. The inline SHALL allow no adding, editing, or deleting. The inline section SHALL render first among the Organization detail inline sections.

#### Scenario: Inline columns
- **WHEN** a staff user opens an Organization with orders
- **THEN** the Orders inline shows one row per order with `order_number`, `number_of_scans` (`—` when null), `submitted_at`, and a trailing action link — and SHALL NOT show money columns, the hand-rolled orders list, or a title-row change link.

#### Scenario: Permission-aware action label
- **WHEN** a staff user with Order change permission views a row
- **THEN** the action link reads `"Change"` with class `inlinechangelink`.
- **WHEN** a staff user without Order change permission views a row
- **THEN** the action link reads `"View"` with class `inlineviewlink`.

#### Scenario: No add or delete
- **WHEN** a staff user views the Orders inline
- **THEN** no empty extra forms and no delete checkboxes are rendered.

#### Scenario: Without order permission
- **WHEN** a staff user without Order view permission opens the Organization change page
- **THEN** the Orders inline is not rendered at all.

#### Scenario: Inline section order
- **WHEN** a staff user opens the Organization change page
- **THEN** the Orders inline section renders before Contacts and Addresses.

#### Scenario: Empty row
- **WHEN** the inline renders its empty template row (unsaved instance)
- **THEN** the action cell is blank with no link.

### Requirement: Total scans line

The system SHALL render a readonly total-scans line on the Organization change page as `Total: N scans across M orders`, where N is the sum of `number_of_scans` over all of the organization's orders (nulls count as 0) and M is the order count.

#### Scenario: Total shown
- **WHEN** a staff user opens an Organization with 2 orders holding 500 and null scans
- **THEN** the line reads `Total: 500 scans across 2 orders`.

#### Scenario: No orders
- **WHEN** a staff user opens an Organization with no orders
- **THEN** no total line is shown (empty state instead).

#### Scenario: Without order permission
- **WHEN** a staff user without Order view permission opens an Organization with orders
- **THEN** the line shows only the count (`"N orders"`), never the scan sum.
