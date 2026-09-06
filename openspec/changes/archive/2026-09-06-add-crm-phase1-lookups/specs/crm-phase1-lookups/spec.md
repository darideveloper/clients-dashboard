## ADDED Requirements

### Requirement: Country lookup model

The system SHALL provide a `Country` model with `iso2` (CharField max_length=2, unique), `iso3` (CharField max_length=3, unique), `name` (CharField max_length=100, unique), `region` (CharField max_length=10, blank=True), `active` (BooleanField default True), `__str__` returning `name`, and `Meta` ordering by `name` with `verbose_name`/`verbose_name_plural` matching existing model style.

#### Scenario: Create country

- **WHEN** a Country is created with iso2="GB", iso3="GBR", name="United Kingdom", region="EU"
- **THEN** it persists with `active` True by default and `str()` returns "United Kingdom"

#### Scenario: Natural-key uniqueness enforced

- **WHEN** a second Country duplicates `iso2`, `iso3`, or `name`
- **THEN** the database rejects it with an integrity error

### Requirement: Rep model

The system SHALL provide a `Rep` model with `first_name` (CharField max_length=100), `last_name` (CharField max_length=100), `email` (EmailField max_length=254, unique), `__str__` returning `"First Last"`, and `Meta` ordering by `last_name, first_name` with `verbose_name`/`verbose_name_plural` matching existing model style. No derived properties SHALL exist in this phase. No fixture SHALL be provided for Rep.

#### Scenario: No fixture for Rep

- **WHEN** `base_loaddata` is run
- **THEN** no `Rep` rows are created by fixtures (Reps are admin-created)

#### Scenario: Create rep

- **WHEN** a Rep is created with first_name="John", last_name="Doe", email="john@ourlivesapp.com"
- **THEN** it persists and `str()` returns "John Doe"

#### Scenario: Email uniqueness enforced

- **WHEN** a second Rep duplicates `email`
- **THEN** the database rejects it with an integrity error

### Requirement: ContactType lookup model

The system SHALL provide a `ContactType` model with `code` (CharField max_length=50, unique), `name` (CharField max_length=100, unique), `active` (BooleanField default True), `description` (TextField blank=True), `__str__` returning `name`, and `Meta` ordering by `code` with `verbose_name`/`verbose_name_plural` matching existing model style.

#### Scenario: Create contact type

- **WHEN** a ContactType is created with code="primary", name="Primary Contact"
- **THEN** it persists with `active` True and `str()` returns "Primary Contact"

#### Scenario: Code and name uniqueness enforced

- **WHEN** a second ContactType duplicates `code` or `name`
- **THEN** the database rejects it with an integrity error

### Requirement: CodeType lookup model

The system SHALL provide a `CodeType` model with `code` (CharField max_length=50, unique), `name` (CharField max_length=100, unique), `max_codes` (PositiveIntegerField), `active` (BooleanField default True), `description` (TextField blank=True), `__str__` returning `name`, and `Meta` ordering by `code` with `verbose_name`/`verbose_name_plural` matching existing model style.

#### Scenario: Create code type

- **WHEN** a CodeType is created with code="up_to_5", name="Up to 5 Additional Codes", max_codes=5
- **THEN** it persists with `active` True and `str()` returns "Up to 5 Additional Codes"

#### Scenario: Code and name uniqueness enforced

- **WHEN** a second CodeType duplicates `code` or `name`
- **THEN** the database rejects it with an integrity error

### Requirement: OrderType lookup model

The system SHALL provide an `OrderType` model with `code` (CharField max_length=50, unique), `name` (CharField max_length=100, unique), `active` (BooleanField default True), `description` (TextField blank=True), `__str__` returning `name`, and `Meta` ordering by `code` with `verbose_name`/`verbose_name_plural` matching existing model style.

#### Scenario: Create order type

- **WHEN** an OrderType is created with code="pilot", name="Pilot Order"
- **THEN** it persists with `active` True and `str()` returns "Pilot Order"

#### Scenario: Code and name uniqueness enforced

- **WHEN** a second OrderType duplicates `code` or `name`
- **THEN** the database rejects it with an integrity error

### Requirement: Phase 1 base fixtures

The system SHALL provide base fixtures in `ourlives/fixtures/ourlives/` for Country (~249 ISO-3166 rows), ContactType (4 rows), CodeType (2 rows), OrderType (4 rows) — all base tier, auto-discovered by existing `core/base_loaddata` and loaded via `start.sh` after `migrate` with zero loader edits. Explicit PKs per file alphabetical from 1 (Country by `iso2` → 1–249, lookups by `code`: ContactType billing pk1/invoice pk2/primary pk3/technical pk4; CodeType up_to_20 pk1/up_to_5 pk2; OrderType pilot pk1/renewal pk2/standard pk3/trial pk4) so future FK fixtures can reference them. No fixture SHALL be provided for Rep. `description` SHALL be contextual: ContactType all 4 are "Extensible contact role, from 616/619"; CodeType `up_to_5` is "Small team bundle, separate frontend field" and `up_to_20` is "Large team bundle, up to 20 additional codes, separate frontend field"; OrderType pilot is "Pilot order for initial evaluation period, replaces hard boolean is_pilot_order", renewal is "Renewal order for extending existing service after pilot", standard is "Standard order for regular full-scope service", trial is "Trial order for short-term evaluation with limited scope"; Country `region` SHALL be blank and `active` true for all rows. ContactType `billing` SHALL have name "Billing Contact" (not "Billing").

#### Scenario: base_loaddata loads all Phase 1 fixtures

- **WHEN** `python manage.py base_loaddata` is run on a fresh database (after `migrate`)
- **THEN** `Country` contains ~249 rows with explicit PKs, `ContactType` contains 4 rows (billing, invoice, primary, technical), `CodeType` contains 2 rows (`up_to_20` max 20 and `up_to_5` max 5), and `OrderType` contains 4 rows (pilot, renewal, standard, trial)

#### Scenario: Fixture re-run is idempotent

- **WHEN** `python manage.py base_loaddata` is run a second time
- **THEN** no duplicate rows are created (rows updated in place by PK)

#### Scenario: Fixture PKs support future FK references

- **WHEN** a future FK fixture references a Phase 1 PK (e.g., `Currency.country=1` or `Contact.contact_type=3`)
- **THEN** the referenced row exists at the documented PK from the alphabetical scheme

#### Scenario: Rep has no fixture rows

- **WHEN** `base_loaddata` is run
- **THEN** no `Rep` rows exist by fixtures
