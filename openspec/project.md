# clients

Greenfield Django 5.2 project. See `openspec/changes/init-django-clients-project/` for the bootstrap change artifacts (proposal, design, specs, tasks).

## Tech stack
- Python 3.12, Django 5.2
- Django REST Framework + Token auth (`rest_framework.authtoken`)
- django-filter, django-solo
- django-unfold admin theme (Unfold 0.77.1)
- django-storages + boto3 (S3 / DigitalOcean Spaces)
- whitenoise (local static), gunicorn (prod)
- psycopg 3 (Postgres), sqlite (test runner)
- python-dotenv for env cascade
- tmux + portless for local dev subdomain

## Conventions
- Env-first config: no secrets, hosts, or storage flags in `settings.py`. Two-phase `load_dotenv` (`.env` then `.env.<ENV>`).
- All env values read via `os.getenv` and coerced explicitly.
- No email/SMTP configured (per project decision).
- `STORAGE_AWS=True` activates S3 backends; `False` falls back to local filesystem + whitenoise.
- Tests force sqlite (`testing.sqlite3`) regardless of `.env.dev` settings.
- `core/` is the only app for now. Future apps go alongside it.

## Local development
```bash
./dev.sh          # tmux session + portless proxy → https://clients.localhost
```
Prereqs: `tmux`, `portless`, Python 3.12, local Postgres (or override `DB_ENGINE` in `.env.dev` to sqlite).

Superuser created during bootstrap: `admin` / `admin12345` (change in any non-toy env).

## Production deploy
Coolify + Dockerfile ARGs. Build context filtered by `.dockerignore` (secrets never reach the image). `collectstatic` runs during build and needs AWS ARGs when `STORAGE_AWS=True`.

```bash
docker build -t clients .    # pass ARGs as build env
./start.sh                    # migrate + gunicorn :80
```

## URLs
- Local: `https://clients.localhost` (via portless)
- Prod: configured via `ALLOWED_HOSTS` and `HOST` in `.env.prod`
- Admin: `/admin/`
- API: `/api/` (DRF, empty router for now)

## Internal docs referenced
- `django-project-setup.md` — full bootstrap procedure
- `django-local-subdomain-setup.md` — portless + tmux dev loop
- `django-media-storage.md` — S3 / DigitalOcean Spaces backends
- `django-unfold-admin.md` — Unfold integration, `ModelAdminUnfoldBase`, OKLCH palette

## OpenSpec
- This change: `openspec/changes/init-django-clients-project/`
- Archive after merge with `/opsx-archive` (or `openspec archive`).
- Future changes: `openspec new change <name>` → fill proposal/design/specs/tasks → apply.
