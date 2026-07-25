## 1. Model Changes

- [x] 1.1 Add `api_key` (CharField, max_length=255, blank=True) and `storage_base_url` (URLField, blank=True) to `AppSettings` in `ourlives/models.py`

## 2. Admin Changes

- [x] 2.1 Add `get_readonly_fields` override to `AppSettingsAdmin` that makes `api_key` and `storage_base_url` read-only for non-superusers
- [x] 2.2 Add "API Configuration" fieldset with the two fields to `AppSettingsAdmin.fieldsets`

## 3. Migration

- [x] 3.1 Run `python manage.py makemigrations ourlives` to generate the migration

## 4. Verify

- [x] 4.1 Run `python manage.py check` to validate project integrity
- [x] 4.2 Run `python manage.py test ourlives` to verify existing tests pass (2 pre-existing Stripe checkout test failures unrelated to this change)
