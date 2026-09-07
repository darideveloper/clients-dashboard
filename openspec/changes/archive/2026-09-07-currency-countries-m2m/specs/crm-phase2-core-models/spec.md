## MODIFIED Requirements

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
