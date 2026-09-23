## ADDED Requirements

### Requirement: Commission note recorded alongside billing milestones

The `order-billing-tracking` capability SHALL additionally record a free-text `rep_commission_note` (`CharField`, max_length=255, blank=True, default "") on `Order`, rendered on its own row at the end of the `Billing` section of the Order admin detail page only.

#### Scenario: Note additive to existing milestones

- **WHEN** an existing Order predating this change is loaded
- **THEN** its note is "" and all prior `order-billing-tracking` behaviors (milestone flags, dates, side-by-side pairs) are unchanged
