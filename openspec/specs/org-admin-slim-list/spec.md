# org-admin-slim-list Specification

## Purpose
Slim Organization admin changelist: six columns (Name, Orders, Rep, Last Order, Usage %, Combined total last) with a linked Rep column and a dummy Usage % column. Partial money breakdowns live on the detail page only.
## Requirements
### Requirement: Slim organization changelist

The system SHALL render the Organization admin changelist with exactly six columns in order: Name, Orders, Rep, Last Order, Usage %, Combined total.

#### Scenario: Changelist columns
- **WHEN** a staff user views the Organization admin list
- **THEN** the row shows `name` (linked), `order_count_display`, linked Rep (or `—`), `last_order_date_display`, `usage_pct_display`, and `combined_total_display` last — and SHALL NOT show `description`, `agreed_scans_total_display`, or `catalog_items_total_display`.

### Requirement: Linked rep column

The system SHALL render the Rep column as "First Last" linked to the Rep change page when `assigned_rep` is set, and `—` otherwise. The column is non-sortable.

#### Scenario: Rep assigned
- **WHEN** an organization has an assigned rep
- **THEN** the Rep cell links to that rep's admin change page with text "First Last".

#### Scenario: Rep unassigned
- **WHEN** an organization has no assigned rep
- **THEN** the Rep cell shows `—` with no link.

### Requirement: Dummy usage percent column

The system SHALL render the Usage % column as the literal text `0%` for every row, with no sorting and no extra queries.

#### Scenario: Dummy value
- **WHEN** a staff user views any Organization row
- **THEN** the Usage % cell shows `0%`.
