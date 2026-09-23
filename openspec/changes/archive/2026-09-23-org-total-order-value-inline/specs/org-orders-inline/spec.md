## MODIFIED Requirements

### Requirement: Orders inline table

The system SHALL render a display-only tabular Orders inline on the Organization change page with exactly the columns `order_number_link`, `number_of_scans`, `submitted_at`, `total_order_value_display`, and a trailing action column with a blank header, plus a per-row link to each Order change page. The order-number cell SHALL itself link to the Order change page with Unfold link styling. The inline SHALL hide its per-row title row. The inline SHALL allow no adding, editing, or deleting. The inline section SHALL render first among the Organization detail inline sections.

#### Scenario: Inline columns
- **WHEN** a staff user opens an Organization with orders
- **THEN** the Orders inline shows one row per order with linked `order_number`, `number_of_scans` (`—` when null), `submitted_at`, per-order total (`—` when zero), and a trailing action link — with no doubled order-number title row and no hand-rolled orders list.

#### Scenario: Permission-aware link labels
- **WHEN** a staff user with Order change permission views a row
- **THEN** the order-number cell and the action link both navigate to the Order change page with class `inlinechangelink`.
- **WHEN** a staff user without Order change permission views a row
- **THEN** both links navigate to the Order change page with class `inlineviewlink`.

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
