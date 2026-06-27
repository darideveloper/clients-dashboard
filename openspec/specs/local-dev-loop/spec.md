# local-dev-loop Specification

## Purpose
TBD - created by archiving change init-django-clients-project. Update Purpose after archive.
## Requirements
### Requirement: Portless subdomain dev script
The repo SHALL contain a `dev.sh` script that boots a `tmux` session named `${PROJECT_NAME}_dev` (where `PROJECT_NAME` is `basename "$PWD"`) running `portless clients --app-port $PORT -- python manage.py runserver $PORT`. The script SHALL call `portless proxy start` and `portless trust` before launching the session, and SHALL auto-increment `$PORT` starting at 8000 while `ss -tuln` shows the port is in use.

#### Scenario: First port chosen
- **WHEN** port 8000 is free and `./dev.sh` runs
- **THEN** the Django server binds to 8000 and is reachable at `https://clients.localhost`

#### Scenario: Port conflict avoidance
- **WHEN** port 8000 is already bound
- **THEN** `./dev.sh` selects 8001 (or the next free port) and the app remains reachable at `https://clients.localhost`

### Requirement: Re-attach on subsequent runs
If a tmux session with the same name already exists, `dev.sh` SHALL attach to it instead of creating a new one.

#### Scenario: Re-attach
- **WHEN** `./dev.sh` runs a second time while the first session is detached
- **THEN** the existing `clients_dev` tmux session is attached to

### Requirement: Virtualenv auto-detection
`dev.sh` SHALL activate `venv/bin/activate` if the `venv` directory exists, or `.venv/bin/activate` if `.venv` exists, before launching any service.

#### Scenario: Venv activation
- **WHEN** `./dev.sh` runs from a checkout that has `venv/`
- **THEN** the Python interpreter used by the runserver command is the venv's interpreter

