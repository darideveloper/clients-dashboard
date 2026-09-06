## MODIFIED Requirements

### Requirement: Production start script
The repo SHALL contain a `start.sh` script with `set -e` that runs `python manage.py makemigrations --noinput` and `python manage.py migrate --noinput` and `python manage.py base_loaddata`, then `exec gunicorn --bind 0.0.0.0:80 project.wsgi:application`.

#### Scenario: Container start
- **WHEN** the container starts
- **THEN** migrations are applied, base fixtures are loaded via `base_loaddata`, and gunicorn binds 0.0.0.0:80

#### Scenario: Migration failure halts startup
- **WHEN** `migrate` exits non-zero
- **THEN** gunicorn does not start (because of `set -e`)

#### Scenario: Fixture load runs on every start

- **WHEN** the container starts
- **THEN** `base_loaddata` runs after `migrate` so reference data (e.g., Default Brand) is present before the app serves traffic
- **AND** re-running the fixture load on a populated database updates rows in place (no duplicates)
