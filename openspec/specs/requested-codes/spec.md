# requested-codes Specification

## Purpose
Storage, replace-on-repost, admin search/filter, and Excel export of verbatim form-requested codes without creating live invitation codes.
## Requirements
### Requirement: Requested codes stored verbatim per order
The system SHALL store one `OrderRequestedCode` per non-empty `code-N` value in the mapping, linked to the created/reconciled order and the resolved `CodeType` (null when no bundle value is present). Each row SHALL have `sequence` equal to the form's slot number `N` (e.g. `code-16` → sequence 16), preserving gaps. `value` SHALL have no global uniqueness constraint — identical literals across orders are legal.

#### Scenario: Five codes stored for an up-to-5 order
- **WHEN** a production submission has five non-empty `code-1..code-5` values and `how-many-additional-codes-do-you-require="Up to 5 Additional Codes"`
- **THEN** five `OrderRequestedCode`s are stored with `code_type=up_to_5`, `sequence` 1..5, linked to the order

#### Scenario: Twenty codes stored with gap preserved
- **WHEN** a submission has non-empty codes in slots 1..14 and 16..20 (slot 15 blank, e.g. OL-89)
- **THEN** exactly 19 rows are stored with sequences `[1..14, 16..20]` and no renumbering

#### Scenario: Empty code fields are skipped
- **WHEN** only some `code-N` values are non-empty
- **THEN** exactly the non-empty slots are stored

#### Scenario: Storage is independent of the additional-codes toggle
- **WHEN** the toggle is "No" but code values are present
- **THEN** the codes are still stored with `code_type=None` (the values are the source of truth)

#### Scenario: Duplicate literals across orders are allowed
- **WHEN** two different orders submit the same `value` (e.g. `P03-001`)
- **THEN** both rows are stored without collision or skip

#### Scenario: Duplicate literals within one order are stored per slot
- **WHEN** one submission contains the same `value` in multiple slots (e.g. OL-88's five identical `P03TST-`)
- **THEN** one row is stored per non-empty slot (five rows with sequences 1..5), distinguished by `sequence`

#### Scenario: No invitation codes created
- **WHEN** any submission with non-empty `code-N` is ingested
- **THEN** zero `InvitationCode` rows are created and `Order.tokens_used` is not incremented (new orders read `0`)

### Requirement: Bundle request stored on the order
The system SHALL store the codes request on `Order`: `requested_codes_wanted` (True when `i-would-like-additional-codes="Yes"`), `requested_codes_bundle` (verbatim bundle label), and `requested_code_type` (resolved `CodeType`, null when blank).

#### Scenario: Bundle yes with label
- **WHEN** a submission has toggle "Yes" and bundle "Up to 20 Additional Codes"
- **THEN** the order stores `requested_codes_wanted=True`, bundle label verbatim, and `requested_code_type=up_to_20`

#### Scenario: Bundle no without label
- **WHEN** a submission has toggle "No" and blank bundle
- **THEN** the order stores `requested_codes_wanted=False`, blank bundle, and null code type

### Requirement: Repost replaces requested codes
On re-submission of an existing order-number, the system SHALL replace the order's `OrderRequestedCode` rows with the latest mapping (delete all, re-insert current non-empty slots) and refresh the order's bundle fields.

#### Scenario: Codes shrink on repost
- **WHEN** an existing order with 5 requested codes is reposted with 2 non-empty codes
- **THEN** the order ends with exactly those 2 rows and no orphan rows remain

#### Scenario: Repost is idempotent
- **WHEN** the identical mapping is reposted
- **THEN** the requested-codes set is unchanged and no duplicate order is created

### Requirement: Requested codes searchable in admin
The system SHALL register `OrderRequestedCode` in admin inheriting `OurlivesModelAdminBase`, with search by `value` and `order__order_number`, list filters by `code_type` and order, and a tabular inline on the `Order` change form.

#### Scenario: Staff finds order by code value
- **WHEN** a staff user searches `P04-007` in the requested-codes changelist
- **THEN** the matching row(s) with their order numbers are listed

#### Scenario: Order page shows requested codes
- **WHEN** a staff user opens an order with requested codes
- **THEN** the inline lists each `sequence` + `value` + bundle
