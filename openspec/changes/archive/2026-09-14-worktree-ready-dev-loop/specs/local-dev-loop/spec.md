## MODIFIED Requirements

### Requirement: Portless subdomain dev script
The repo SHALL contain a `dev.sh` script that boots a `tmux` session named `${PROJECT_NAME}_dev` (where `PROJECT_NAME` is `basename "$PWD"`) running `portless clients --app-port $PORT -- python manage.py runserver $PORT`. The script SHALL call `portless proxy start` and `portless trust` before launching the session. Port selection SHALL prefer the portless-injected `$PORT` when set (failing fast if it is taken) and SHALL otherwise auto-increment `$PORT` starting at 8000 while `ss -tuln` shows the port is in use.

#### Scenario: First port chosen
- **WHEN** port 8000 is free and `./dev.sh` runs
- **THEN** the Django server binds to 8000 and is reachable at `https://clients.localhost`

#### Scenario: Port conflict avoidance
- **WHEN** port 8000 is already bound
- **THEN** `./dev.sh` selects 8001 (or the next free port) and the app remains reachable at `https://clients.localhost`

#### Scenario: Injected port honored
- **WHEN** `$PORT` is injected by portless and free
- **THEN** `./dev.sh` binds exactly that port instead of scanning

## ADDED Requirements

### Requirement: Concurrent sibling domains
Each sibling checkout SHALL serve its own basename-derived portless domain (e.g. `../clients-feature-x` → `https://clients-feature-x.localhost`) with a unique tmux session (`${PROJECT_NAME}_dev`), so any number of siblings run concurrently.

#### Scenario: Two siblings side by side
- **WHEN** `./dev.sh` runs in both `clients` and `clients-feature-x`
- **THEN** two tmux sessions (`clients_dev`, `clients-feature-x_dev`) exist and `portless list` shows both domains on different ports
