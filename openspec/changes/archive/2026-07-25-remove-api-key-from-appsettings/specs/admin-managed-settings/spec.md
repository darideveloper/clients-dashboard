## REMOVED Requirements

### Requirement: api_key and storage_base_url on AppSettings
**Reason**: The `api_key` field is not needed — the intended external service doesn't require a per-instance API key
**Migration**: Remove `api_key` field via new migration. `storage_base_url` remains unchanged.

## MODIFIED Requirements

### Requirement: storage_base_url on AppSettings
The `AppSettings` singleton model SHALL have a `storage_base_url` field (URLField, blank=True). The field SHALL be stored in the `ourlives_appsettings` database table.

#### Scenario: storage_base_url exists on model
- **WHEN** `AppSettings.get_solo()` is called
- **THEN** the returned instance has `storage_base_url` attribute defaulting to `""`

#### Scenario: api_key is removed
- **WHEN** `AppSettings.get_solo()` is called
- **THEN** the returned instance does NOT have an `api_key` attribute

#### Scenario: Migration drops column cleanly
- **WHEN** `python manage.py migrate` runs
- **THEN** the migration drops the `api_key` column from `ourlives_appsettings` without data loss

### Requirement: Superuser-only editing in admin
The `AppSettingsAdmin` SHALL display `storage_base_url` in the "API Configuration" fieldset. Non-superuser staff SHALL see it as read-only. Superusers SHALL see an editable input.

#### Scenario: Superuser can edit storage_base_url
- **WHEN** a superuser opens the AppSettings change form
- **THEN** the `storage_base_url` field is editable

#### Scenario: Non-superuser sees read-only
- **WHEN** a staff user who is not a superuser opens the AppSettings change form
- **THEN** the `storage_base_url` field displays as read-only text
