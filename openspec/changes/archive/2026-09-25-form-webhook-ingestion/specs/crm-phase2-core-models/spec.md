## MODIFIED Requirements

### Requirement: OrganizationAddress model
The system SHALL provide an `OrganizationAddress` model with `organization` (ForeignKey to `Organization`, on_delete=CASCADE, related_name="addresses"), `country` (ForeignKey to `Country`, on_delete=PROTECT, related_name="organization_addresses", null=True, blank=True, allowing addresses without a resolved country), `line1` (CharField max_length=255), `line2` (CharField max_length=255, blank=True), `city` (CharField max_length=100), `state` (CharField max_length=100, blank=True), `zip` (CharField max_length=20), `is_primary` (BooleanField default False), `__str__` returning `"line1, city"`, and `Meta` ordering by `-is_primary, city` with `verbose_name`/`verbose_name_plural` matching existing model style. No database constraint SHALL enforce a single primary per organization in this phase.

#### Scenario: Create address

- **WHEN** an OrganizationAddress is created with organization=<Acme>, line1="10 Downing St", city="London", zip="SW1A 2AA", country=<UK>, is_primary=True
- **THEN** it persists and `str()` returns "10 Downing St, London"

#### Scenario: Filter primary address

- **WHEN** an organization has one primary and one secondary address
- **THEN** filtering by `organization` and `is_primary=True` returns exactly the primary address

#### Scenario: Country is protected

- **WHEN** a Country with linked addresses is deleted
- **THEN** the database raises ProtectedError and the Country survives

#### Scenario: Address without a resolved country is allowed

- **WHEN** an OrganizationAddress is created with `country=None` (an unmatched country label during webhook ingestion)
- **THEN** the address persists with a null country

#### Scenario: Organization delete cascades

- **WHEN** the linked Organization is deleted (with no PROTECT-blocking InvitationCodes)
- **THEN** its addresses are deleted too (CASCADE)