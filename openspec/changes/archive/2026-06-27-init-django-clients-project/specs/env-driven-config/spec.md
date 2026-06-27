## ADDED Requirements

### Requirement: Two-phase dotenv loading
`project/settings.py` SHALL call `load_dotenv(BASE_DIR / '.env')` before reading `ENV`, then `load_dotenv(BASE_DIR / f'.env.{ENV}')`. The active environment SHALL be the value of the `ENV` variable, defaulting to `dev`.

#### Scenario: Dev environment selected
- **WHEN** `.env` contains `ENV=dev`
- **THEN** Django settings read variables from `.env.dev` and `ENV` in `os.environ` equals `dev`

#### Scenario: Prod environment selected
- **WHEN** `.env` contains `ENV=prod`
- **THEN** Django settings read variables from `.env.prod`

### Requirement: .env file only carries the environment selector
The `.env` file SHALL contain ONLY the `ENV` variable and no other keys. All other configuration (secrets, hosts, DB, storage, AWS, etc.) SHALL live in `.env.dev` and `.env.prod`. The same key may appear in both `.env.dev` and `.env.prod` with environment-appropriate values.

#### Scenario: .env is minimal
- **WHEN** the bootstrap completes
- **THEN** `.env` contains exactly one line: `ENV=dev` (or `ENV=prod`)

#### Scenario: Secrets not in .env
- **WHEN** `git status` runs after bootstrap
- **THEN** `SECRET_KEY` and `DEBUG` appear in `.env.dev` and `.env.prod` (gitignored) but NOT in `.env`

### Requirement: Secret and debug from env
`SECRET_KEY` SHALL be loaded from the environment. `DEBUG` SHALL be `True` only when the `DEBUG` env var equals the string `"True"`. `ALLOWED_HOSTS` SHALL be the comma-split value of the `ALLOWED_HOSTS` env var.

#### Scenario: DEBUG toggle
- **WHEN** `.env.dev` has `DEBUG=True`
- **THEN** `settings.DEBUG` is `True` in the dev process

- **WHEN** `.env.prod` has `DEBUG=False`
- **THEN** `settings.DEBUG` is `False` in the prod process

### Requirement: Dynamic database backend
`settings.DATABASES['default']` SHALL switch engine based on the `DB_ENGINE` env var. When the `manage.py test` command runs (`sys.argv[1] == "test"`), the database SHALL be sqlite at `BASE_DIR/testing.sqlite3`. Otherwise MySQL connections SHALL include `init_command="SET sql_mode='STRICT_TRANS_TABLES'"` and `charset="utf8mb4"`.

#### Scenario: Test isolation
- **WHEN** `python manage.py test` runs
- **THEN** the test runner uses sqlite at `testing.sqlite3` regardless of `DB_ENGINE` in `.env.dev`

#### Scenario: Production Postgres
- **WHEN** `DB_ENGINE=django.db.backends.postgresql` and `DB_*` are populated
- **THEN** Django connects to Postgres on `migrate` and `runserver`

### Requirement: CORS and CSRF origins
`CORS_ALLOWED_ORIGINS` and `CSRF_TRUSTED_ORIGINS` SHALL be derived from comma-split env vars, with each value stripped and trailing slashes removed. The dev `.env.dev` SHALL include `https://clients.localhost` and `http://localhost:8000`; prod SHALL include the production hostname.

#### Scenario: Localhost trusted
- **WHEN** `.env.dev` has `CORS_ALLOWED_ORIGINS=https://clients.localhost,http://localhost:8000`
- **THEN** `settings.CORS_ALLOWED_ORIGINS == ["https://clients.localhost", "http://localhost:8000"]`

### Requirement: Localized time and date formats
`TIME_ZONE` SHALL be `America/Mexico_City`. `LANGUAGE_CODE` SHALL be `en-us`. `USE_I18N` SHALL be `True`. `USE_TZ` SHALL be `True`. `DATE_FORMAT` SHALL be `d/b/Y`, `TIME_FORMAT` SHALL be `H:i`, and `DATETIME_FORMAT` SHALL be `"d/b/Y H:i"`.

#### Scenario: Default timezone
- **WHEN** Django starts
- **THEN** `settings.TIME_ZONE == "America/Mexico_City"`, `LANGUAGE_CODE == "en-us"`, `USE_I18N is True`, `USE_TZ is True`

### Requirement: Templates directory includes project overrides
`TEMPLATES[0]['DIRS']` SHALL include `BASE_DIR / "project" / "templates"` so that the admin template override at `project/templates/admin/base_site.html` is discoverable. `TEMPLATES[0]['APP_DIRS']` SHALL be `True`.

#### Scenario: Admin override template resolved
- **WHEN** Django renders the admin base template
- **THEN** `project/templates/admin/base_site.html` is loaded (verified by a SimpleMDE `.editor-toolbar` element appearing in the DOM)

### Requirement: DRF token app registered
`INSTALLED_APPS` SHALL include `rest_framework.authtoken` because `DEFAULT_AUTHENTICATION_CLASSES` declares `TokenAuthentication`, which requires the token table created by this app's migrations.

#### Scenario: Token table created
- **WHEN** `python manage.py migrate` runs
- **THEN** the `authtoken_token` table exists (the app is registered before any model migration runs)

### Requirement: Production ALLOWED_HOSTS excludes loopback
The `.env.prod` `ALLOWED_HOSTS` SHALL NOT contain `localhost` or `127.0.0.1`. It SHALL contain the production hostname(s) only.

#### Scenario: Prod hosts are not loopback
- **WHEN** `.env.prod` is loaded
- **THEN** `"localhost"` and `"127.0.0.1"` are not in `settings.ALLOWED_HOSTS`
