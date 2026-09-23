## ADDED Requirements

### Requirement: Rep commission note on Order

The system SHALL provide on `Order` a `rep_commission_note` field (`CharField`, max_length=255, blank=True, default "") holding free text such as "15%" or "$500 flat". The field SHALL be optional with no validation on its content.

#### Scenario: Defaults to empty

- **WHEN** an Order is created without a commission note
- **THEN** `rep_commission_note` is ""

#### Scenario: Free text persists verbatim

- **WHEN** an Order is saved with `rep_commission_note="15% Q3 promo"`
- **THEN** the exact string persists and round-trips

### Requirement: Commission note in Billing fieldset

The system SHALL render `rep_commission_note` as a text input on its own row at the end of the `Billing` fieldset on the `Order` admin change (detail) page. The field SHALL NOT appear in `list_display`, `list_filter`, or `search_fields`.

#### Scenario: Note visible and editable in detail view

- **WHEN** staff open an Order change page
- **THEN** the Billing section shows the commission note input after the commission paid pair, editable and savable

#### Scenario: List view unchanged

- **WHEN** staff open the Order changelist
- **THEN** no commission-note column or filter is present
