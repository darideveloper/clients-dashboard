## MODIFIED Requirements

### Requirement: Both production and test/dev submissions are processed
The system SHALL save and process submissions regardless of `executionMode`. `production` and `test` (dev / n8n `webhook-test`) submissions both create/update rows, and the mode SHALL be recorded on the `FormWebhookEvent` for provenance.

#### Scenario: Test execution mode is ingested
- **WHEN** a valid token is sent with `executionMode="test"`
- **THEN** the system returns 200 and creates/updates Order, Rep, Contact, Address, Items, and RequestedCodes exactly as a production submission would, recording `execution_mode="test"` on the audit row

#### Scenario: Missing execution mode is still ingested
- **WHEN** a valid token is sent with no `executionMode` field
- **THEN** the system still processes the submission and records the mode as unknown/empty on the audit row
