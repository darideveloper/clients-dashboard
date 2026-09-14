## MODIFIED Requirements

### Requirement: Organization CRUD

The system SHALL provide an Organization model with fields for `name` (unique, max 100 chars) and `description` (text, blankable). The system SHALL register Organization in the Django admin with search by name and filtered list display. The admin list SHALL additionally show the order-summary columns via `list_display=("name","description","order_count_display","agreed_scans_total_display","catalog_items_total_display","combined_total_display","last_order_date_display")`, where `order_count_display` and `last_order_date_display` are sortable via `admin_order_field` on annotated queryset fields and the three money columns render per-currency breakdowns (display-only). The admin change form SHALL include a readonly "Order summary" section exposing the five summaries with their labels and help texts (see `org-rep-order-summaries`).

#### Scenario: Create organization via admin
- **WHEN** a staff user creates an Organization with name "Acme Corp" and description "Primary billing entity"
- **THEN** the Organization SHALL be persisted with those values and appear in the admin list

#### Scenario: Organization name uniqueness
- **WHEN** a user attempts to create a second Organization with the same name as an existing one
- **THEN** the system SHALL reject the duplicate and show a validation error

#### Scenario: Organization list display
- **WHEN** a staff user views the Organization admin list
- **THEN** the list SHALL display "name" and "description" columns, be searchable by name, and sortable by name

#### Scenario: Organization summary columns
- **WHEN** a staff user views the Organization admin list for an org with 2 orders
- **THEN** the row shows `order_count` 2 and the money breakdown columns, with the changelist still served without per-row queries

#### Scenario: Organization summary section
- **WHEN** a staff user opens an Organization change form
- **THEN** a readonly "Order summary" section shows the five summaries with labels and help texts, and all existing fields and inlines keep working unchanged
