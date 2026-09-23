## ADDED Requirements

### Requirement: Sortable invitation-code usage column
The system SHALL annotate the InvitationCode queryset with `_usage_pct` (`current_use*100.0/max_use`, NULL when `max_use=0`) and the admin `usage_percentage` column SHALL sort by it, rendering NULL as `—`.

#### Scenario: Sort codes by usage
- **WHEN** a staff user clicks the "Usage %" column header on the InvitationCode changelist
- **THEN** rows order by `_usage_pct` with `—` rows last in both directions

#### Scenario: Zero-quota code renders safely
- **WHEN** a code has `max_use=0`
- **THEN** the column shows `—` and no division error occurs

### Requirement: Invitation-code pagination
The system SHALL show 50 results per page on the InvitationCode changelist.

#### Scenario: Browse codes
- **WHEN** a staff user opens the InvitationCode changelist
- **THEN** at most 50 rows are shown per page

### Requirement: Usage bucket filter
The system SHALL provide a `UsageBucketFilter` with buckets Unused (`=0%`), Low (`>0–<50%`), Half (`50–<80%`), Warning (`80–<100%`), Full (`=100%`), No quota (NULL), available on the InvitationCode changelist.

#### Scenario: Find codes about to run out
- **WHEN** a staff user selects the Warning bucket
- **THEN** only codes with `_usage_pct >= 80 AND < 100` are listed

### Requirement: Usage threshold filter
The system SHALL provide a numeric threshold filter (`usage >= X%`, `usage <= Y%`, combinable) on the InvitationCode changelist.

#### Scenario: Ad-hoc threshold query
- **WHEN** a staff user sets `>= 90`
- **THEN** only codes with `_usage_pct >= 90` are listed

### Requirement: Token-weighted order usage
The system SHALL annotate each Order with `_codes_used = SUM(invitation_codes.current_use)`, `_codes_max = SUM(invitation_codes.max_use)`, `_usage_pct = _codes_used*100.0/_codes_max` (NULL when no codes or `_codes_max=0`), shown as a sortable `—`-on-empty column with the same bucket + threshold filters.

#### Scenario: Sort orders by code consumption
- **WHEN** a staff user sorts the Order changelist by usage
- **THEN** orders with the highest token-weighted consumption rank first and codeless orders render `—` last

### Requirement: Token-weighted organization usage (combined, dedup-safe)
The system SHALL annotate each Organization with combined sums over direct codes (`invitationcode.organization = org`) plus order codes (`order.organization = org`), where a single InvitationCode row matching both paths SHALL be counted exactly once; `_usage_pct` is NULL when combined `_codes_max` is 0/NULL. The column SHALL be sortable with the same bucket + threshold filters.

#### Scenario: Org with direct and order codes
- **WHEN** an organization has 1 direct code (used 4/10) and 1 order code (used 6/10)
- **THEN** the org usage shows `50%` (10/20 token-weighted), not an average of per-code percentages

#### Scenario: Dually-linked code counted once
- **WHEN** a code has `organization=X` and its order also belongs to `X`
- **THEN** its `max_use`/`current_use` contribute exactly once to X's sums
