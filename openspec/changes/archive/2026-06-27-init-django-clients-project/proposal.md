## Why

The `clients` project starts as an empty directory. We need a production-grade Django 5.2 foundation that the rest of the application can be built on top of: environment-driven configuration, S3-compatible media storage from day one, an `unfold`-themed admin, and a portless subdomain local dev loop. Booting all of this in a structured, reproducible way is required before any feature work can begin.

## What Changes

- Initialize a Django 5.2 project (`project/`) with a primary app (`core/`) and full dependency set pinned in `requirements.txt` (DRF, `django-filter`, `psycopg`, `pillow`, `whitenoise`, `gunicorn`, `cors-headers`, `python-dotenv`, `django-storages`, `boto3`, `django-unfold`, `django-solo`, `selenium`, `requests`).
- Add env-first configuration: `.env` (selector) + `.env.dev` + `.env.prod`, loaded by `python-dotenv` from a `load_dotenv` sequence at the top of `settings.py`.
- Wire `ALLOWED_HOSTS`, `CORS_ALLOWED_ORIGINS`, and `CSRF_TRUSTED_ORIGINS` to include `clients.localhost` and `localhost:8000` for local dev.
- Add dynamic database selection (Postgres in dev/prod, sqlite for the test runner) and timezone `America/Mexico_City`.
- Wire S3/DO Spaces storage via `django-storages` + `boto3` with three backends (Static, Public Media, Private Media) in `project/storage_backends.py`, toggled by `STORAGE_AWS`. Local file storage fallback for dev.
- Install `django-unfold` admin theme with custom `UNFOLD` config (logo, favicon, OKLCH primary palette, sidebar navigation stub) and override `admin/base_site.html` to inject SimpleMDE and three custom JS enhancements.
- Add `DRF` defaults: `IsAuthenticated` default permission, `TokenAuthentication` + `SessionAuthentication`, custom pagination (`project/pagination.py`), custom exception handler (`project/handlers.py`).
- Drop in `utils/` helpers (`callbacks.py` env badge, `admin_helpers.py` group checks, `automation.py` selenium helpers, `media.py` URL resolver + test image helper).
- Add `dev.sh` (Case A vanilla): `tmux` session + `portless` proxy so the app is reachable at `https://clients.localhost` with auto-incrementing port detection.
- Add `Dockerfile` and `start.sh` for Coolify-style production deploys (gunicorn on :80, `collectstatic` at build time, ARGs for AWS creds).
- Initialize OpenSpec `project.md` with stack, conventions, and dev/deploy commands.

## Capabilities

### New Capabilities
- `project-bootstrap`: initial scaffolding, dependency manifest, and git/file layout for a new Django project.
- `env-driven-config`: env-first settings loader, `.env`/`.env.dev`/`.env.prod` separation, dynamic DB and storage backends.
- `s3-media-storage`: S3/DO Spaces integration with Static/Public/Private backends and local fallback.
- `unfold-admin-theme`: `django-unfold` setup, custom UNFOLD config, admin template override, and supporting static assets.
- `local-dev-loop`: `dev.sh` + `portless` + `tmux` to expose the app at `https://clients.localhost`.
- `production-deploy`: `Dockerfile` + `start.sh` with build-time `collectstatic` and gunicorn entrypoint for Coolify.

### Modified Capabilities
_None — this is a greenfield change._

## Impact

- New files in repo root: `requirements.txt`, `manage.py`, `dev.sh`, `start.sh`, `Dockerfile`, `.env`, `.env.dev`, `.env.prod`, `.gitignore`.
- New packages: `project/`, `core/`, `utils/`, `static/`, `media/`, `openspec/`.
- New runtime deps (pinned in `requirements.txt`): Django 5.2, DRF 3.16, `django-storages` 1.14.4, `boto3` 1.34.162, `django-unfold` 0.77.1, `django-solo`, `whitenoise`, `gunicorn`, `psycopg` 3, `cors-headers`, `python-dotenv`, `pillow`, `django-filter`, `selenium`, `requests`.
- New tooling on dev machine: `tmux`, `portless` (prereqs only — no install steps in scope).
- No external systems affected yet (DB and S3 creds left as placeholders in `.env.prod`).
- Out of scope: any models, views, serializers, URL routes beyond `/admin/` and `/api/` (empty DRF router), email configuration (skipped per user), Celery/Redis (not needed for this skeleton).
