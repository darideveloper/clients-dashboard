# crm-auto-match Specification

## Purpose
Match-or-create auto-selection for CRM records (Organization by normalized address line1, Rep by email, Contact by email within org, Country via alias map + nullable fallback, Currency/Product/CodeType label resolution), so repeat form submissions reuse existing records instead of duplicating.
## Requirements

### Requirement: Organization auto-selected by normalized line1
The system SHALL derive the Organization name from the address `line1` and auto-select an existing Organization by a normalized comparison (lowercase, whitespace stripped) instead of creating a duplicate. When no match exists, the system SHALL create the Organization with `name = line1`.

#### Scenario: Existing organization is reused
- **WHEN** a submission's address line1 normalizes to the same value as an existing Organization (`"Saxon Healthcare Ltd Four"` vs `"saxonhealthcareltdfour"`)
- **THEN** the existing Organization is linked to the order and no new Organization is created

#### Scenario: Unknown organization is created
- **WHEN** no existing Organization matches the normalized line1
- **THEN** a new Organization is created with `name` equal to the raw line1

#### Scenario: Case and whitespace differences still match
- **WHEN** line1 differs from an existing Organization only by case, spacing, or punctuation spacing
- **THEN** they are treated as the same organization

### Requirement: Rep auto-selected by email
The system SHALL auto-select a Rep by the unique `reps-email`; when absent, the system SHALL create a Rep, splitting the single `reps-name` field into `first_name` and `last_name` at the first space.

#### Scenario: Existing rep reused
- **WHEN** `reps-email` matches an existing Rep
- **THEN** the existing Rep is linked to the order and no new Rep is created

#### Scenario: New rep created with split name
- **WHEN** `reps-email` is unknown and `reps-name="Demo Harry Judd"`
- **THEN** a Rep is created with first_name `"Demo"`, last_name `"Harry Judd"`, and the submitted email

### Requirement: Contacts auto-selected by email within the organization
The system SHALL auto-select a Contact by email within the resolved organization for the primary and invoice roles; when absent, the system SHALL create a Contact with the role's `ContactType` (`primary` / `invoice`), splitting the name at the first space.

#### Scenario: Existing contact reused
- **WHEN** a `primary-contact-email` matches a Contact in the order's organization
- **THEN** that Contact is linked as the order's `primary_contact` and no new Contact is created

#### Scenario: New primary contact created
- **WHEN** no matching Contact exists in the organization
- **THEN** a Contact is created with type `primary`, the split name, email, and phone, and linked as `primary_contact`

#### Scenario: Invoice contact created with invoice type
- **WHEN** the invoice block has no matching Contact
- **THEN** a Contact with type `invoice` is created and linked as `invoice_contact`

### Requirement: Address reconstructed and split
The system SHALL split the flattened address string (comma-joined) back into `line1`, `line2`, `city`, `state`, `zip`, `country`, parsing from the right (last segment = country, then zip, state, city; remaining left segments = line1 and line2).

#### Scenario: Six-part address split
- **WHEN** the address is `"Saxon Healthcare Ltd Four, 54 High Street, Essex, Suffolk, SU34 T56, United Kingdom"`
- **THEN** line1=`"Saxon Healthcare Ltd Four"`, line2=`"54 High Street"`, city=`"Essex"`, state=`"Suffolk"`, zip=`"SU34 T56"`, country=`"United Kingdom"`

#### Scenario: Five-part address (empty line2)
- **WHEN** the address has five comma-separated parts (no line2)
- **THEN** line1 is the first part, line2 is empty, and city/state/zip/country are the trailing four parts

### Requirement: Country resolved via alias map with nullable fallback
The system SHALL resolve the country label to a `Country` fixture row by normalized exact match, then by an alias map for known form/fixture label gaps. When no match exists, the address SHALL be saved with `country = None` and the event flagged.

#### Scenario: Exact normalized country match
- **WHEN** the country label is `"United Kingdom"`
- **THEN** the matching `Country` row is linked

#### Scenario: Alias map resolves known gaps
- **WHEN** the label is `"Vatican City"` (form) while the fixture stores `"Holy See"`
- **THEN** the `Holy See` Country row is linked via the alias map

#### Scenario: Unknown country leaves country null
- **WHEN** the label matches neither a fixture name nor an alias (e.g. `"Kosovo"`, which is not in the fixture)
- **THEN** the address is saved with `country=None` and the audit event records the unresolved label

### Requirement: Product, currency, and code type resolved by label
The system SHALL resolve `Currency` by code, `Product` by derived name `<Region> <Tier> Pilot`, and `CodeType` by bundle name (`Up to 5 Additional Codes` → `up_to_5`, `Up to 20 Additional Codes` → `up_to_20`).

#### Scenario: Currency resolved by code
- **WHEN** `currency` (or `pilot-currency`) is `"GBP"`
- **THEN** the `GBP` Currency row is linked

#### Scenario: Product resolved by region and tier
- **WHEN** a UK pilot block has `product-uk="Micro Pilot"`
- **THEN** the `UK Micro Pilot` Product is used for the OrderItem

#### Scenario: Code type resolved by bundle name
- **WHEN** `how-many-additional-codes-do-you-require="Up to 5 Additional Codes"`
- **THEN** the `up_to_5` CodeType is used for the order's invitation codes

#### Scenario: Up-to-20 code type resolved by bundle name
- **WHEN** `how-many-additional-codes-do-you-require="Up to 20 Additional Codes"`
- **THEN** the `up_to_20` CodeType is used for the order's invitation codes
