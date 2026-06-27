## 1. Repo bootstrap

- [x] 1.1 Create `requirements.txt` with pinned versions from `django-project-setup`: `Django>=5.2,<5.3`, `djangorestframework>=3.16.1`, `django-filter>=24.3`, `psycopg[binary]>=3.2.3`, `pillow>=11.1.0`, `whitenoise>=6.11.0`, `gunicorn>=24.1.1`, `django-cors-headers>=4.9.0`, `python-dotenv>=1.0.1`, `django-storages==1.14.4`, `boto3==1.34.162`, `django-unfold==0.77.1`, `django-solo>=2.3.0`, `selenium>=4.40.0`, `requests>=2.32.3`. Group with comments per the doc (base/db/images/drf+jwt/testing/admin/tools/storage)
- [x] 1.2 Create `.gitignore` with the full ignore list from the doc: `__pycache__`, `*__pycache__`, `*temp.*`, `temp.*`, `*.log*`, `*.zip`, `venv`, `.env`, `debug.*`, `db.*`, `*.sqlite3`, `*.pyc`, `credentials.json`, `staticfiles/`, `info.txt`, `/media`, `.env*`, `.vscode`, `*/.DS_Store`, `.DS_Store`, `/docs`, `*.temp`, `.windsurf/`
- [x] 1.3 Create `venv/`, activate it, run `pip install -r requirements.txt`, verify `pip check` is clean
- [x] 1.4 Run `django-admin startproject project .` and `python manage.py startapp core`
- [x] 1.5 Create empty `media/` with a `.gitkeep`

## 2. Environment files

- [x] 2.1 Create `.env` with ONLY `ENV=dev`. No other keys — secrets, hosts, DB, storage all live in `.env.dev` / `.env.prod`
- [x] 2.2 Create `.env.dev` with `SECRET_KEY=<random-50+>`, `DEBUG=True`, `ALLOWED_HOSTS=localhost,127.0.0.1,clients.localhost`, `CORS_ALLOWED_ORIGINS=https://clients.localhost,http://localhost:8000`, `CSRF_TRUSTED_ORIGINS=https://clients.localhost,http://localhost:8000`, `HOST=https://clients.localhost`, `DB_ENGINE=django.db.backends.postgresql`, `DB_NAME=clients`, `DB_USER=daridev`, `DB_PASSWORD=`, `DB_HOST=localhost`, `DB_PORT=5432`, `STORAGE_AWS=False`
- [x] 2.3 Create `.env.prod` with `SECRET_KEY=` (placeholder, fill at deploy), `DEBUG=False`, the production hostname in `ALLOWED_HOSTS` (NO `localhost`/`127.0.0.1`), `CORS_ALLOWED_ORIGINS=<prod-frontend>`, `CSRF_TRUSTED_ORIGINS=<prod-frontend>`, `HOST=<prod-hostname>`, `STORAGE_AWS=True`, and AWS placeholders (`AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_STORAGE_BUCKET_NAME`, `AWS_S3_REGION_NAME`, `AWS_S3_ENDPOINT_URL`, `AWS_S3_CUSTOM_DOMAIN`, `AWS_PROJECT_FOLDER=clients`)
- [x] 2.4 Confirm `git status` does not list `.env`, `.env.dev`, or `.env.prod`
- [x] 2.5 Smoke test: temporarily edit `.env.dev` to set `STORAGE_AWS=True` (with dummy AWS vars), run `python manage.py check`, then revert to `False`. Confirms the toggle path works without crashing settings

## 3. `project/` package

- [x] 3.1 Replace `project/settings.py` with the env-first version: two-phase `load_dotenv`, dynamic `DATABASES` (test → sqlite), `TIME_ZONE=America/Mexico_City`, `LANGUAGE_CODE='en-us'`, `USE_I18N=True`, `USE_TZ=True`, `DATE_FORMAT="d/b/Y"`, CORS/CSRF parsing, `STORAGES` toggle on `STORAGE_AWS`, `REST_FRAMEWORK` defaults, `UNFOLD` config block (logo/favicon, OKLCH primary palette, sidebar with auth group and core placeholder), `ALLOWED_HOSTS` split from env, `TEMPLATES[0]['DIRS']` including `BASE_DIR / "project" / "templates"`, and the `*_LOCATION` constants defined unconditionally (fall back to `"static"`/`"media"`/`"private"` when `STORAGE_AWS=False`)
- [x] 3.2 Update `INSTALLED_APPS` order: `unfold`, `unfold.contrib.filters`, `unfold.contrib.forms`, `unfold.contrib.inlines`, `corsheaders`, `rest_framework`, `rest_framework.authtoken`, `solo`, `storages`, `core`, then `django.contrib.{admin,auth,contenttypes,sessions,messages,staticfiles}`
- [x] 3.3 Update `MIDDLEWARE` to put `corsheaders.middleware.CorsMiddleware` at the top, then `whitenoise.middleware.WhiteNoiseMiddleware` after `SecurityMiddleware`
- [x] 3.4 Add `STATICFILES_DIRS = [BASE_DIR / "static"]`, `STATIC_ROOT = BASE_DIR / "staticfiles"`, `MEDIA_URL = "/media/"`, `MEDIA_ROOT = BASE_DIR / "media"`
- [x] 3.5 Replace `project/urls.py` with admin + root redirect to `/admin/` + empty `api/` DRF router + `static()` media serving (gated on `settings.DEBUG`)
- [x] 3.6 Create `project/pagination.py` with `CustomPageNumberPagination` (page_size 12, max 100, rich response)
- [x] 3.7 Create `project/storage_backends.py` with `StaticStorage`, `PublicMediaStorage`, `PrivateMediaStorage`
- [x] 3.8 Create `project/handlers.py` with `custom_exception_handler` wrapping errors as `{status, message, data}`
- [x] 3.9 Replace `project/admin.py` with Unfold-wrapped `User`/`Group` admins
- [x] 3.10 Create `project/templates/admin/base_site.html` extending `admin/base.html` (NOT `unfold/layouts/base.html`) and loading SimpleMDE + 3 local JS files + `style.css`

## 4. `utils/` helpers

- [x] 4.1 Create `utils/__init__.py` and `utils/callbacks.py` with `environment_callback` mapping `prod/staging/dev/local` to badge tuples
- [x] 4.2 Create `utils/admin_helpers.py` with `is_user_admin(user)` checking groups `admins`/`supports` or `is_superuser`
- [x] 4.3 Create `utils/automation.py` with `get_selenium_elems(driver, selectors)`
- [x] 4.4 Create `utils/media.py` with `get_media_url` and `get_test_image`
- [x] 4.5 Create `project/admin_base.py` with `ModelAdminUnfoldBase` (`compressed_fields=True`, `warn_unsaved_form=True`, `list_filter_sheet=False`, `change_form_show_cancel_button=True`, `actions_row=["edit"]`, plus an `edit(object_id)` action decorator) for future model admins to inherit

## 5. Static assets

- [x] 5.1 Create `static/css/style.css` with the markdown preview typography rules from the doc
- [x] 5.2 Create `static/js/add_tailwind_styles.js` adding Tailwind utility classes to `.btn` and `.img-preview`
- [x] 5.3 Create `static/js/load_markdown.js` wiring SimpleMDE to all `textarea`s
- [x] 5.4 Create `static/js/range_date_filter_es.js` localizing `created_at_*` and `updated_at_*` placeholders to `Desde` / `Hasta`
- [x] 5.5 Create `static/js/copy_clipboard.js` (cookie → clipboard helper)
- [x] 5.6 Create `static/js/script.js` placeholder
- [x] 5.7 Drop 1×1 placeholder `static/favicon.png` and `static/logo.webp` (user to replace later)

## 6. Local dev loop

- [x] 6.1 Create `dev.sh` (Case A vanilla): derive `PROJECT_NAME=$(basename "$PWD")`, session `${PROJECT_NAME}_dev`, re-attach if exists, run `portless proxy start && portless trust`, auto-detect venv, port loop from 8000 via `ss -tuln`, single tmux window running `portless clients --app-port $PORT -- python manage.py runserver $PORT`
- [x] 6.2 `chmod +x dev.sh`

## 7. Production deploy

- [x] 7.1 Create `.dockerignore` excluding `venv`, `.env`, `.env*`, `.git`, `db.*`, `staticfiles/`, `/media`, `__pycache__`, `*.pyc`, `tests/`, `.opencode/`, `.claude/`, `.gemini/`, `.agent/`, `.vscode/`, `*.log*`, `.windsurf/`, `docs/`, `*.sqlite3`
- [x] 7.2 Create `Dockerfile` per the doc: `python:3.12-slim`, build args for secrets/AWS, install `libpq-dev` + `gcc` (still needed even with `psycopg[binary]` for the `pg_config` build chain), `pip install -r requirements.txt`, `collectstatic --noinput`, expose 80, `CMD ["./start.sh"]`
- [x] 7.3 Create `start.sh` with `set -e`, `makemigrations --noinput`, `migrate --noinput`, `exec gunicorn --bind 0.0.0.0:80 project.wsgi:application`
- [x] 7.4 `chmod +x start.sh`

## 8. Database init and smoke test

- [x] 8.1 Verify local Postgres is reachable with the `.env.dev` creds (or temporarily set `DB_ENGINE=django.db.backends.sqlite3` in `.env.dev` to bypass) — Postgres requires password for `daridev` user, sqlite fallback used for smoke run
- [x] 8.2 Run `python manage.py makemigrations && python manage.py migrate` — 16 migrations applied including authtoken
- [x] 8.3 Run `python manage.py createsuperuser` (interactive) — non-interactive via DJANGO_SUPERUSER_* env vars (admin / admin12345)
- [x] 8.4 Run `python manage.py check` — passed, no issues
- [x] 8.5 Run `python manage.py test` — passed, 0 tests (test branch verified)
- [x] 8.6 Run `./dev.sh` and visit `https://clients.localhost/admin/` — `/admin/login/` 302, `/admin/` renders Unfold title "clients Admin", `/api/` 401 with custom `{status, message, data}` body, `base_site.html` override injects simplemde + custom JS on change-list/change-form pages (Unfold's login/index pages bypass `base_site.html` by design)

## 9. OpenSpec project context

- [x] 9.1 Populate `openspec/project.md` with: tech stack (Django 5.2, DRF, Unfold, S3, portless + tmux), conventions (env-first, no email), dev command (`./dev.sh`), prod deploy (Coolify + Dockerfile ARGs), local URL (`https://clients.localhost`), references to the four internal docs
- [x] 9.2 Commit all files with message `chore: bootstrap django clients project` — committed as `0701b83`
