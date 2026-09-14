## ADDED Requirements

### Requirement: Company change page lists its Orders

The system SHALL render a read-only paginated Orders section on the Organization change page listing `order_number`, `po_number`, and agreed total per Order, each linking to its Order change page, with in-page pagination (25 per page via `?org_orders_page=N`) and a "View all" link to the Order changelist pre-filtered by the organization.

#### Scenario: Orders render with links
- **WHEN** a staff user with `view_order` permission opens a Company with Orders
- **THEN** the Orders section lists each Order's number, PO number, and total, each linking to `admin:ourlives_order_change` for that Order

#### Scenario: Pagination and view-all fallback
- **WHEN** a Company has more than 25 Orders and the user opens page 2 (`?org_orders_page=2`)
- **THEN** the section shows page 2 of 25-row pages with prev/next controls, and a "View all N" link to the Order changelist filtered by `organization__id__exact`

#### Scenario: Empty, add view, and permission states
- **WHEN** a Company has no Orders
- **THEN** the section shows "No orders yet"
- **WHEN** a staff user opens the add view (unsaved Organization)
- **THEN** the section shows "—"
- **WHEN** a staff user lacks `view_order` permission
- **THEN** the section shows only the Order count with no links

### Requirement: Rep change page lists Companies and Orders

The system SHALL render read-only paginated Companies and Orders sections on the Rep change page (25 per page via `?rep_companies_page=N` / `?rep_orders_page=N`), each row linking to its change page, with "View all" links to the pre-filtered changelists.

#### Scenario: Companies and Orders render
- **WHEN** a staff user with `view_organization` and `view_order` permissions opens a Rep with linked records
- **THEN** the Companies section lists organization names linking to `admin:ourlives_organization_change` and the Orders section lists order numbers linking to `admin:ourlives_order_change`

#### Scenario: Pagination per list
- **WHEN** a Rep has more than 25 Companies or Orders
- **THEN** each section paginates independently via its own GET key with prev/next controls, and offers "View all" links filtered by `assigned_rep__id__exact` / `rep__id__exact`

#### Scenario: Empty, add view, and permission states
- **WHEN** a Rep has no Companies or no Orders
- **THEN** the corresponding section shows "No companies yet" / "No orders yet"
- **WHEN** a staff user opens the add view (unsaved Rep)
- **THEN** both sections show "—"
- **WHEN** a staff user lacks the related view permission
- **THEN** the corresponding section shows only the count with no links

### Requirement: Order change page shows Rep card, all org contacts, and Codes

The system SHALL render a Related section on the Order change page containing: a mini Rep card (name linked to the Rep change page, email `mailto:`, company/order counts, "Open rep" link); a paginated list of ALL of the Order's organization contacts (25 per page via `?order_contacts_page=N`, each with name link, type, email, phone, and `(primary)`/`(invoice)` badges); and a paginated Codes table (25 per page via `?order_codes_page=N`, columns `code`, `project`, `code_type`, `current/max` use, each code linking to its InvitationCode change page); each list with a "View all" link to its pre-filtered changelist. `submitted_at` SHALL render readonly in Order details.

#### Scenario: Rep card renders
- **WHEN** a staff user with `view_rep` permission opens an Order
- **THEN** the Rep card shows the rep's full name (link to `admin:ourlives_rep_change`), email as a `mailto:` link, assigned-company and order counts, and an "Open rep" link

#### Scenario: All org contacts render with badges
- **WHEN** a staff user with `view_contact` permission opens an Order whose organization has contacts
- **THEN** the contacts list shows every org contact with type, email, phone, links to `admin:ourlives_contact_change`, and `(primary)`/`(invoice)` badges on the selected contacts

#### Scenario: Codes table renders main fields
- **WHEN** a staff user with `view_invitationcode` permission opens an Order with codes
- **THEN** the Codes table shows each code (link to `admin:ourlives_invitationcode_change`), project, code type, and `current_use/max_use`

#### Scenario: Pagination, view-all, and permission states
- **WHEN** contacts or codes exceed 25 rows
- **THEN** the corresponding list paginates via its own GET key with prev/next controls, plus "View all" links filtered by `organization__id__exact` (contacts) / `order__id__exact` (codes)
- **WHEN** a staff user lacks the related view permission
- **THEN** the corresponding block shows only the count with no links or emails
- **WHEN** the Order is unsaved or a relation is empty
- **THEN** blocks show "—" (add view) or "No contacts yet" / "No codes yet"
