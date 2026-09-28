## ADDED Requirements

### Requirement: Rep auto-assigned to organization when unassigned
The system SHALL set `Organization.assigned_rep` to the submitting rep during webhook ingestion whenever the resolved organization has no assigned rep. An organization that already has an assigned rep SHALL keep it — later submissions never overwrite a manual (or earlier automatic) assignment.

#### Scenario: New organization gets the submitting rep
- **WHEN** a submission creates a new organization with `reps-email="john@example.com"`
- **THEN** the organization persists with `assigned_rep` equal to the resolved rep

#### Scenario: Existing unassigned organization gets assigned on next submission
- **WHEN** a submission resolves to an organization whose `assigned_rep` is empty
- **THEN** `assigned_rep` is set to the submitting rep

#### Scenario: Pre-assigned rep is never overwritten
- **WHEN** a submission resolves to an organization already assigned to rep A but is submitted by rep B
- **THEN** `assigned_rep` remains rep A and the order still links rep B as its `rep`
