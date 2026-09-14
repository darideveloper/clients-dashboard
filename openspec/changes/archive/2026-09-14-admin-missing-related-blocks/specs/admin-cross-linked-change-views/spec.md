## ADDED Requirements

### Requirement: Company change page lists Codes across all its orders

The system SHALL render a read-only paginated Codes section on the Organization change page listing every `InvitationCode` whose `order.organization` is that Organization, with the same row format as the Order codes table (`code` linking to `admin:ourlives_invitationcode_change`, `project` name, `code_type` name or "—", `current_use/max_use`), ordered by `code`, 25 per page via `?org_order_codes_page=N`, with a "View all" link to the InvitationCode changelist pre-filtered by the organization.

#### Scenario: Codes render with links

- **WHEN** a staff user with `view_invitationcode` permission opens a Company whose orders carry codes
- **THEN** the Codes section lists each code with its project, code type, and used/max counts, each code linking to its InvitationCode change page

#### Scenario: Pagination and view-all

- **WHEN** a Company has more than 25 codes across its orders
- **THEN** the section shows 25-row pages with prev/next controls via `?org_order_codes_page=N`, and a "View all N" link to the InvitationCode changelist filtered by `order__organization__id__exact`

#### Scenario: Empty, add view, and permission states

- **WHEN** a Company has no codes across its orders
- **THEN** the section shows "No codes yet"
- **WHEN** a staff user opens the add view (unsaved Organization)
- **THEN** the section shows "—"
- **WHEN** a staff user lacks `view_invitationcode` permission
- **THEN** the section shows only the code count with no links

### Requirement: Company change page lists directly-assigned Codes

The system SHALL render a second read-only paginated Codes section on the Organization change page listing every `InvitationCode` whose direct `organization` FK is that Organization (including ones with no order), with the same row format as the Order codes table, ordered by `code`, 25 per page via `?org_codes_page=N`, with a "View all" link to the InvitationCode changelist filtered by `organization__id__exact`.

#### Scenario: Direct codes render with links

- **WHEN** a staff user with `view_invitationcode` permission opens a Company with directly-assigned codes
- **THEN** the section lists each code with its project, code type, and used/max counts, each code linking to its InvitationCode change page

#### Scenario: Pagination and view-all

- **WHEN** a Company has more than 25 directly-assigned codes
- **THEN** the section shows 25-row pages with prev/next controls via `?org_codes_page=N`, and a "View all N" link to the InvitationCode changelist filtered by `organization__id__exact`

#### Scenario: Empty, add view, and permission states

- **WHEN** a Company has no directly-assigned codes
- **THEN** the section shows "No codes yet"
- **WHEN** a staff user opens the add view (unsaved Organization)
- **THEN** the section shows "—"
- **WHEN** a staff user lacks `view_invitationcode` permission
- **THEN** the section shows only the code count with no links

### Requirement: Order change page shows Company card

The system SHALL render a read-only Company card in the Related section of the Order change page mirroring `rep_card`: organization name linking to `admin:ourlives_organization_change`, address line resolving to the primary address else the first address (omitted only when the organization has no addresses), contact/order/code counts for that organization (`N codes` counts directly-assigned codes), and an "Open company" link.

#### Scenario: Company card renders

- **WHEN** a staff user with `view_organization` permission opens an Order
- **THEN** the Company card shows the organization name (link to its change page), its primary address line (or first address when no primary exists), `N contacts · N orders · N codes` counts, and an "Open company" link

#### Scenario: Add view and permission states

- **WHEN** the Order is unsaved or has no organization
- **THEN** the card shows "—"
- **WHEN** a staff user lacks `view_organization` permission
- **THEN** the card shows only the organization name with no link or counts
- **WHEN** the organization has no addresses at all
- **THEN** the card omits the address line but still shows name, counts, and link
