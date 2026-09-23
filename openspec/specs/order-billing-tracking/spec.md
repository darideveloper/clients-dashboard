# order-billing-tracking Specification

## Purpose
TBD - created by archiving change order-billing-tracking. Update Purpose after archive.
## Requirements
### Requirement: Order billing milestone flags and dates

The system SHALL provide on `Order` six fields: `invoice_sent` (BooleanField, default False), `invoice_sent_on` (DateField, null=True, blank=True), `invoice_paid` (BooleanField, default False), `invoice_paid_on` (DateField, null=True, blank=True), `commission_paid` (BooleanField, default False), `commission_paid_on` (DateField, null=True, blank=True). Each flag and its date SHALL be fully independent: no validation SHALL require or forbid any combination.

#### Scenario: Defaults on new order

- **WHEN** an Order is created without billing fields
- **THEN** all three flags are False and all three dates are None

#### Scenario: Tick without date persists

- **WHEN** an Order is saved with `invoice_sent=True` and `invoice_sent_on=None`
- **THEN** it persists verbatim with no validation error

#### Scenario: Date without tick persists

- **WHEN** an Order is saved with `invoice_paid_on=2026-09-22` and `invoice_paid=False`
- **THEN** it persists verbatim, the flag stays False, and no auto-tick occurs

#### Scenario: Full pair persists

- **WHEN** an Order is saved with `commission_paid=True` and `commission_paid_on=2026-09-22`
- **THEN** both values persist verbatim

### Requirement: Billing fieldset on Order detail page

The system SHALL render a `Billing` fieldset on the `Order` admin change (detail) page containing `invoice_sent`, `invoice_sent_on`, `invoice_paid`, `invoice_paid_on`, `commission_paid`, `commission_paid_on`, positioned after `Terms` and before `Details`, using default checkbox and date-picker widgets, with each flag and its date grouped on the same row (three side-by-side pairs). None of the six fields SHALL appear in `list_display`, `list_filter`, or `search_fields`.

#### Scenario: Billing section visible in detail view

- **WHEN** staff open an Order change page
- **THEN** a Billing section shows the three checkbox+date pairs side by side on shared rows, editable and savable

#### Scenario: List view unchanged

- **WHEN** staff open the Order changelist
- **THEN** no billing column or filter is present
