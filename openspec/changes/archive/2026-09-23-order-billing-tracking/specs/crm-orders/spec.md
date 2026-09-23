## ADDED Requirements

### Requirement: Order billing milestone fields recorded

The `crm-orders` capability SHALL additionally record billing milestones on `Order` as documented in `order-billing-tracking` (three independent Boolean + nullable Date pairs: invoice sent, invoice paid, rep commission paid; fully manual with no cross-validation), with a dedicated `Billing` section on the Order admin detail page only.

#### Scenario: Billing milestones additive

- **WHEN** an existing Order predating this change is loaded
- **THEN** it shows flags False and dates empty, and all prior `crm-orders` behaviors (identity, typing, pricing) are unchanged
