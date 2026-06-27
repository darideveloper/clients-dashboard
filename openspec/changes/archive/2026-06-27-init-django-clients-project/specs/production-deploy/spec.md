## ADDED Requirements

### Requirement: Docker build excludes secrets and dev artifacts
A `.dockerignore` file at the repo root SHALL exclude `venv`, `.env`, `.env*`, `.git`, `db.*`, `staticfiles/`, `/media`, `__pycache__`, `*.pyc`, `tests/`, `.opencode/`, `.claude/`, `.gemini/`, `.agent/`, `.vscode/`, `*.log*`, `.windsurf/`, `docs/`, and `*.sqlite3`. The `Dockerfile` SHALL NOT override this with an explicit `COPY` of any of these paths.

#### Scenario: Build context does not include secrets
- **WHEN** the image is built
- **THEN** `.env*` files are NOT in `/app/` inside the image (verified by `docker run --rm <image> ls /app | grep env` returning empty)

### Requirement: Production Dockerfile
The repo SHALL contain a `Dockerfile` based on `python:3.12-slim` that sets `PYTHONDONTWRITEBYTECODE=1` and `PYTHONUNBUFFERED=1`, installs `libpq-dev` and `gcc`, installs Python deps from `requirements.txt`, runs `python manage.py collectstatic --noinput`, exposes port 80, and runs `./start.sh`. All sensitive env vars (`SECRET_KEY`, `DB_*`, `CORS_ALLOWED_ORIGINS`, `CSRF_TRUSTED_ORIGINS`, `AWS_*`, `STORAGE_AWS`, `ENV`, `DEBUG`, `ALLOWED_HOSTS`) SHALL be declared as `ARG` and exported as `ENV` so build-time `collectstatic` can reach S3.

#### Scenario: Build with S3 creds
- **WHEN** the image is built with `STORAGE_AWS=True` and valid AWS ARGs
- **THEN** `collectstatic` uploads static files to the configured bucket

#### Scenario: Build without S3
- **WHEN** the image is built with `STORAGE_AWS=False`
- **THEN** `collectstatic` writes to `staticfiles/` locally and the image still builds

### Requirement: Production start script
The repo SHALL contain a `start.sh` script with `set -e` that runs `python manage.py makemigrations --noinput` and `python manage.py migrate --noinput`, then `exec gunicorn --bind 0.0.0.0:80 project.wsgi:application`.

#### Scenario: Container start
- **WHEN** the container starts
- **THEN** migrations are applied and gunicorn binds 0.0.0.0:80

#### Scenario: Migration failure halts startup
- **WHEN** `migrate` exits non-zero
- **THEN** gunicorn does not start (because of `set -e`)

### Requirement: OpenSpec project context
`openspec/project.md` SHALL document the tech stack (Django 5.2, DRF, Unfold, S3, portless + tmux), the dev command (`./dev.sh`), the prod deploy flow (`Dockerfile` + Coolify ARGs), and the local URL (`https://clients.localhost`).

#### Scenario: Context readable
- **WHEN** `openspec` loads project context
- **THEN** it includes the dev and deploy commands for `clients`
