## MODIFIED Requirements

### Requirement: Project layout
The repository SHALL contain a Django 5.2 project using `project/` as the settings package, `core/` as the primary app, and `utils/` for shared helpers. The repo root SHALL hold `manage.py`, `requirements.txt`, `dev.sh`, `start.sh`, `Dockerfile`, `.env`, `.env.dev`, `.env.prod`, `.env.example`, `worktree-new.sh`, and `.gitignore`.

#### Scenario: Files present after bootstrap
- **WHEN** the bootstrap tasks complete
- **THEN** `python manage.py check` reports `System check identified no issues`

#### Scenario: App discoverable
- **WHEN** `python manage.py startapp core` runs
- **THEN** `core` appears in `INSTALLED_APPS` and `python manage.py showmigrations` lists the `core` app

#### Scenario: Worktree bootstrap files tracked
- **WHEN** a fresh sibling worktree is created
- **THEN** `worktree-new.sh`, `.env.example`, and `docs/django-worktrees.md` are present (tracked in git)

### Requirement: Git ignored paths
The `.gitignore` file SHALL exclude `__pycache__`, `*__pycache__`, `*.pyc`, `venv`, `.env`, `.env*`, `db.*`, `*.sqlite3`, `staticfiles/`, `/media`, `/docs`, `*.log*`, `*.zip`, `debug.*`, `credentials.json`, `info.txt`, `.vscode`, `.DS_Store`, `*/.DS_Store`, `*.temp`, `*temp.*`, and `.windsurf/`, with narrow exceptions `!.env.example` and `!docs/django-worktrees.md` so the worktree runbook and env template carry into siblings.

#### Scenario: Secrets never tracked
- **WHEN** `git status` runs after creating `.env` and `.env.dev`
- **THEN** neither file appears as untracked

#### Scenario: Runbook tracked despite docs ignore
- **WHEN** `git check-ignore docs/django-worktrees.md .env.example` runs
- **THEN** neither path is ignored
