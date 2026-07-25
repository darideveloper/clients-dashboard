## 1. Model Changes

- [x] 1.1 Remove `api_key` field from `AppSettings` in `ourlives/models.py`

## 2. Admin Changes

- [x] 2.1 Remove `api_key` from the "API Configuration" fieldset in `ourlives/admin.py`
- [x] 2.2 Remove `api_key` from `get_readonly_fields` override in `ourlives/admin.py`

## 3. Test Changes

- [x] 3.1 Remove `api_key` assertions from `AppSettingsAdminTests` in `ourlives/tests.py`

## 4. Migration

- [x] 4.1 Run `python manage.py makemigrations ourlives` to generate the removal migration

## 5. Verify

- [x] 5.1 Run `python manage.py check`
- [x] 5.2 Run `python manage.py test ourlives` (2 pre-existing Stripe checkout failures unrelated)
