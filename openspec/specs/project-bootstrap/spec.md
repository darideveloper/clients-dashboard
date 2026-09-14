# project-bootstrap Specification

## Purpose
TBD - created by archiving change init-django-clients-project. Update Purpose after archive.
## Requirements
### Requirement: Project layout
The repository SHALL contain a Django 5.2 project using `project/` as the settings package, `core/` as the primary app, and `utils/` for shared helpers. The repo root SHALL hold `manage.py`, `requirements.txt`, `dev.sh`, `start.sh`, `Dockerfile`, `.env`, `.env.dev`, `.env.prod`, `.env.example`, `worktree-new.sh`, `worktree-done.sh`, and `.gitignore`.

#### Scenario: Files present after bootstrap
- **WHEN** the bootstrap tasks complete
- **THEN** `python manage.py check` reports `System check identified no issues`

#### Scenario: App discoverable
- **WHEN** `python manage.py startapp core` runs
- **THEN** `core` appears in `INSTALLED_APPS` and `python manage.py showmigrations` lists the `core` app

#### Scenario: Worktree bootstrap files tracked
- **WHEN** a fresh sibling worktree is created
- **THEN** `worktree-new.sh`, `worktree-done.sh`, `.env.example`, and `docs/django-worktrees.md` are present (tracked in git)

### Requirement: Pinned dependency manifest
The `requirements.txt` file SHALL pin every runtime and tooling dependency listed in the team's `django-project-setup` doc, including `Django>=5.2,<5.3`, `djangorestframework>=3.16.1`, `django-filter>=24.3`, `psycopg[binary]>=3.2.3`, `pillow>=11.1.0`, `whitenoise>=6.11.0`, `gunicorn>=24.1.1`, `django-cors-headers>=4.9.0`, `python-dotenv>=1.0.1`, `django-storages==1.14.4`, `boto3==1.34.162`, `django-unfold==0.77.1`, `django-solo>=2.3.0`, `selenium>=4.40.0`, and `requests>=2.32.3`.

#### Scenario: Install succeeds
- **WHEN** `pip install -r requirements.txt` runs in a fresh venv
- **THEN** every package installs without resolution errors and `pip check` reports no broken deps

### Requirement: Git ignored paths
The `.gitignore` file SHALL exclude `__pycache__`, `*__pycache__`, `*.pyc`, `venv`, `.env`, `.env*`, `db.*`, `*.sqlite3`, `staticfiles/`, `/media`, `/docs`, `*.log*`, `*.zip`, `debug.*`, `credentials.json`, `info.txt`, `.vscode`, `.DS_Store`, `*/.DS_Store`, `*.temp`, `*temp.*`, and `.windsurf/`, with narrow exceptions `!.env.example` and `!docs/django-worktrees.md` so the worktree runbook and env template carry into siblings.

#### Scenario: Secrets never tracked
- **WHEN** `git status` runs after creating `.env` and `.env.dev`
- **THEN** neither file appears as untracked

#### Scenario: Runbook tracked despite docs ignore
- **WHEN** `git check-ignore docs/django-worktrees.md .env.example` runs
- **THEN** neither path is ignored

