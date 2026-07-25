## ADDED Requirements

### Requirement: api_key and storage_base_url on AppSettings

The `AppSettings` singleton model SHALL have an `api_key` field (CharField, max_length=255, blank=True) and a `storage_base_url` field (URLField, blank=True). Both SHALL be stored in the `ourlives_appsettings` database table via a new Django migration.

#### Scenario: Fields exist on model
- **WHEN** `AppSettings.get_solo()` is called
- **THEN** the returned instance has `api_key` and `storage_base_url` attributes defaulting to `""`

#### Scenario: Migration applies cleanly
- **WHEN** `python manage.py migrate` runs
- **THEN** the migration adds two nullable columns to `ourlives_appsettings` without data loss

### Requirement: Superuser-only editing in admin

The `AppSettingsAdmin` SHALL display `api_key` and `storage_base_url` in a dedicated "API Configuration" fieldset. Non-superuser staff (`is_staff=True` but `is_superuser=False`) SHALL see the fields as read-only. Superusers SHALL see editable inputs.

#### Scenario: Superuser can edit
- **WHEN** a superuser opens the AppSettings change form
- **THEN** the `api_key` and `storage_base_url` fields are editable text inputs

#### Scenario: Non-superuser sees read-only
- **WHEN** a staff user who is not a superuser opens the AppSettings change form
- **THEN** the `api_key` and `storage_base_url` fields display as read-only text
