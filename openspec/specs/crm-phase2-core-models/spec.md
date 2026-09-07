# crm-phase2-core-models Specification

## Purpose
TBD - created by archiving change add-crm-phase2-models. Update Purpose after archive.
## Requirements
### Requirement: Currency model

The system SHALL provide a `Currency` model with `code` (CharField max_length=3, unique), `name` (CharField max_length=100), `symbol_left` (CharField max_length=10, blank=True), `symbol_right` (CharField max_length=10, blank=True), `exchange_rate` (DecimalField max_digits=10, decimal_places=2), `countries` (ManyToManyField to `Country`, blank=True, related_name="currencies"), `active` (BooleanField default True), `__str__` returning `code`, and `Meta` ordering by `code` with `verbose_name`/`verbose_name_plural` matching existing model style.

#### Scenario: Create currency with countries

- **WHEN** a Currency is created with code="EUR", name="Euro", symbol_left="€", exchange_rate="0.92" and countries=[<Germany>, <France>]
- **THEN** it persists with `active` True and `str()` returns "EUR"

#### Scenario: Countries are optional

- **WHEN** a Currency is created with code="USD", name="US Dollar" and no countries
- **THEN** it persists with zero linked countries

#### Scenario: Shared currency across countries

- **WHEN** EUR is linked to Germany and France
- **THEN** filtering `Country` Germany's `currencies` and France's `currencies` both return EUR

#### Scenario: Country delete removes only the link

- **WHEN** a Country linked to a Currency is deleted
- **THEN** the Currency survives with that link removed (junction row deleted, no ProtectedError)

#### Scenario: Code uniqueness enforced

- **WHEN** a second Currency duplicates `code`
- **THEN** the database rejects it with an integrity error

### Requirement: Product model

The system SHALL provide a `Product` model with `currency` (ForeignKey to `Currency`, on_delete=PROTECT, related_name="products"), `name` (CharField max_length=200), `tier` (CharField max_length=50, free text, blank=True), `unit_price` (DecimalField max_digits=10, decimal_places=2), `active` (BooleanField default True), `description` (TextField blank=True), `__str__` returning `name`, and `Meta` ordering by `name` with `verbose_name`/`verbose_name_plural` matching existing model style.

#### Scenario: Create product

- **WHEN** a Product is created with name="Micro Pilot", tier="micro", unit_price="995.00", currency=<USD>
- **THEN** it persists with `active` True and `str()` returns "Micro Pilot"

#### Scenario: Currency is protected

- **WHEN** a Currency with linked Products is deleted
- **THEN** the database raises ProtectedError and the Currency survives

### Requirement: Contact model

The system SHALL provide a `Contact` model with `organization` (ForeignKey to `Organization`, on_delete=CASCADE, related_name="contacts"), `contact_type` (ForeignKey to `ContactType`, on_delete=PROTECT, related_name="contacts"), `first_name` (CharField max_length=100), `last_name` (CharField max_length=100), `email` (EmailField max_length=254), `phone` (CharField max_length=50, blank=True), `__str__` returning `"First Last"`, and `Meta` ordering by `last_name, first_name` with `verbose_name`/`verbose_name_plural` matching existing model style. Email SHALL NOT be globally unique.

#### Scenario: Create contact

- **WHEN** a Contact is created with organization=<Acme>, contact_type=<Primary>, first_name="Alice", last_name="Smith", email="alice@acme.com", phone="+44 7700 900123"
- **THEN** it persists and `str()` returns "Alice Smith"

#### Scenario: Organization delete cascades

- **WHEN** the linked Organization is deleted (with no PROTECT-blocking InvitationCodes)
- **THEN** its Contacts are deleted too (CASCADE)

#### Scenario: Contact type is protected

- **WHEN** a ContactType with linked Contacts is deleted
- **THEN** the database raises ProtectedError and the ContactType survives

### Requirement: OrganizationAddress model

The system SHALL provide an `OrganizationAddress` model with `organization` (ForeignKey to `Organization`, on_delete=CASCADE, related_name="addresses"), `country` (ForeignKey to `Country`, on_delete=PROTECT, related_name="organization_addresses"), `line1` (CharField max_length=255), `line2` (CharField max_length=255, blank=True), `city` (CharField max_length=100), `state` (CharField max_length=100, blank=True), `zip` (CharField max_length=20), `is_primary` (BooleanField default False), `__str__` returning `"line1, city"`, and `Meta` ordering by `-is_primary, city` with `verbose_name`/`verbose_name_plural` matching existing model style. No database constraint SHALL enforce a single primary per organization in this phase.

#### Scenario: Create address

- **WHEN** an OrganizationAddress is created with organization=<Acme>, line1="10 Downing St", city="London", zip="SW1A 2AA", country=<UK>, is_primary=True
- **THEN** it persists and `str()` returns "10 Downing St, London"

#### Scenario: Filter primary address

- **WHEN** an organization has one primary and one secondary address
- **THEN** filtering by `organization` and `is_primary=True` returns exactly the primary address

#### Scenario: Country is protected

- **WHEN** a Country with linked addresses is deleted
- **THEN** the database raises ProtectedError and the Country survives

#### Scenario: Organization delete cascades

- **WHEN** the linked Organization is deleted (with no PROTECT-blocking InvitationCodes)
- **THEN** its addresses are deleted too (CASCADE)

