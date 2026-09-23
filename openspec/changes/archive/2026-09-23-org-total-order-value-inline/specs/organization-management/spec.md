## MODIFIED Requirements

### Requirement: Organization CRUD

The system SHALL provide an Organization model with fields for `name` (unique, max 100 chars) and `description` (text, blankable). The system SHALL register Organization in the Django admin with search by name and filtered list display. The admin list SHALL show exactly six columns via `list_display=("name","order_count_display","rep_link","last_order_date_display","usage_pct_display","combined_total_display")`, where `order_count_display` and `last_order_date_display` are sortable via `ordering="_order_count"` / `ordering="_last_order_date"` on the annotated queryset fields, `rep_link` renders "First Last" linked to the Rep change page (or `—` when unassigned, non-sortable), `usage_pct_display` renders the dummy literal `0%` (display-only, non-sortable), and `combined_total_display` renders the per-currency combined breakdown last under the "Total Order Value" label (display-only, bulk-attached, no per-row queries). The admin change form SHALL include a readonly "Order summary" section exposing the five summaries with their labels and help texts (see `org-rep-order-summaries`).

#### Scenario: Create organization via admin
- **WHEN** a staff user creates an Organization with name "Acme Corp" and description "Primary billing entity"
- **THEN** the Organization SHALL be persisted with those values and appear in the admin list

#### Scenario: Organization name uniqueness
- **WHEN** a user attempts to create a second Organization with the same name as an existing one
- **THEN** the system SHALL reject the duplicate and show a validation error

#### Scenario: Organization list display
- **WHEN** a staff user views the Organization admin list
- **THEN** the list SHALL display "name", "Orders", "Rep", "Last Order", "Usage %" and "Total Order Value" last, be searchable by name, and sortable by name

#### Scenario: Organization summary columns
- **WHEN** a staff user views the Organization admin list for an org with 2 orders
- **THEN** the row shows `order_count` 2, `combined_total_display` with the per-currency breakdown, and `usage_pct_display` `0%`, with the changelist still served without per-row queries

#### Scenario: Organization summary section
- **WHEN** a staff user opens an Organization change form
- **THEN** a readonly "Order summary" section shows the five summaries with labels and help texts, and all existing fields and inlines keep working unchanged
