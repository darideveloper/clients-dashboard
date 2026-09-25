# invitation-code-autocreate Specification

## Purpose
Auto-population of InvitationCode rows from form code-N slots (code_type by bundle, sequence, max_use=1, current_use=0, project always ourlens, order + org links), Order.tokens_used population, and add-missing-codes reconcile on re-submit.
## Requirements

### Requirement: Invitation codes auto-created from form codes
The system SHALL create one `InvitationCode` per non-empty `code-N` value in the mapping, linked to the resolved organization, the created/reconciled order, the `ourlens` Project, and the resolved `CodeType` (null when no bundle value is present — e.g. the additional-codes toggle is `No` or blank but code values exist). The `ourlens` project is the fixed, always-used project for this dedicated Ourlens webhook. Each code SHALL have `max_use=1`, `current_use=0`, `is_active=True`, and `sequence` equal to the form's slot number `N` (e.g. `code-16` → sequence 16), preserving any gaps in the submitted codes.

#### Scenario: Five codes created for an up-to-5 order
- **WHEN** a production submission has five non-empty `code-1..code-5` values and `how-many-additional-codes-do-you-require="Up to 5 Additional Codes"`
- **THEN** five InvitationCodes are created with `code_type=up_to_5`, `sequence` 1..5, `max_use=1`, `current_use=0`, `is_active=True`, linked to the order, organization, and the `ourlens` project

#### Scenario: Twenty codes created for an up-to-20 order
- **WHEN** a production submission has `how-many-additional-codes-do-you-require="Up to 20 Additional Codes"` with twenty non-empty `code-1..code-20` values
- **THEN** twenty InvitationCodes are created with `code_type=up_to_20`, `sequence` 1..20, `max_use=1`, `current_use=0`, `is_active=True`, linked to the order, organization, and the `ourlens` project

#### Scenario: Empty code fields are skipped
- **WHEN** only some `code-N` values are non-empty (e.g. `code-15` is blank but `code-14` and `code-16` are filled)
- **THEN** exactly the non-empty codes are created and each `sequence` is the form's slot number (code-14 → 14, code-16 → 16, no renumbering)

#### Scenario: Code creation is independent of the additional-codes toggle
- **WHEN** the toggle is "No" but code values are present
- **THEN** the codes are still created with `code_type=None` (the values are the source of truth)

#### Scenario: Project is always ourlens
- **WHEN** a submission creates invitation codes
- **THEN** every code's project is `ourlens`, regardless of the order, organization, or any payload value

### Requirement: The ourlens project is guaranteed by fixture
The system SHALL ship a `Project` fixture (`ourlives/fixtures/ourlives/Project.json`) containing the `ourlens` project (and `ourplan`) so a fresh environment loaded via `base_loaddata` always has the project the webhook depends on.

#### Scenario: Fresh environment has the ourlens project
- **WHEN** a fresh environment runs `migrate` + `base_loaddata`
- **THEN** a Project named `ourlens` exists (alongside `ourplan`) and codes can be linked to it without manual admin entry

### Requirement: Token count recorded per order
The system SHALL track the number of codes created per submission on `Order.tokens_used`, accumulating across reconciles.

#### Scenario: tokens_used counts created codes
- **WHEN** a submission creates 5 invitation codes
- **THEN** the Order's `tokens_used` increases by 5

#### Scenario: Re-submit accumulates
- **WHEN** the same order-number is re-submitted and 2 new codes are added
- **THEN** `tokens_used` increases by 2 (existing codes untouched)

### Requirement: Reconcile adds only missing codes
On a re-submission of an existing order-number, the system SHALL add InvitationCodes whose code values are not already linked to the order, and SHALL NOT modify or delete existing codes.

#### Scenario: New code added on reconcile
- **WHEN** a re-submission contains a code value not present on the existing order
- **THEN** only that code is created; existing codes keep their `current_use`, `max_use`, and `sequence`

#### Scenario: Existing code untouched on reconcile
- **WHEN** a re-submission repeats a code already linked to the order
- **THEN** no change is made to that code (its `current_use` history is preserved)

### Requirement: Codes never block order creation
The system SHALL create order and codes regardless of the current token pool state (availability may go negative).

#### Scenario: Order with codes succeeds when pool is exhausted
- **WHEN** `AppSettings.total_tokens` is less than the sum of assigned `max_use` (or availability is already negative)
- **THEN** the order and its codes are still created without validation error

#### Scenario: Created codes count toward availability
- **WHEN** codes are created
- **THEN** `tokens_assigned` and `tokens_available` reflect the new codes (availability may be negative)
