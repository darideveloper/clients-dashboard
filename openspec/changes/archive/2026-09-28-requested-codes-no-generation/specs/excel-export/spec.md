## ADDED Requirements

### Requirement: Full export includes requested codes
The full-app workbook SHALL include an `OrderRequestedCode` sheet (one row per requested code: order, sequence, value, bundle/code type) discovered automatically via the existing `sorted(apps.get_models())` mechanism, requiring no export-code changes beyond registering the model with `OurlivesModelAdminBase`.

#### Scenario: Requested codes sheet present
- **WHEN** a permitted staff user clicks "Export all app data"
- **THEN** the workbook contains an `OrderRequestedCode` sheet with one row per stored requested code alongside all existing model sheets
