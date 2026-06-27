## Context

The repository `/mnt/hd/develop/django/clients` is empty (no Python source, no venv). The goal is to bootstrap a Django 5.2 project named `clients` with a `core` app, a portless-based local dev loop, S3-compatible media storage, and a `django-unfold` admin theme — all wired via env-first configuration so the same code runs in dev, prod, and CI.

The bootstrap must be the single source of truth for how every future Django project in the team is laid out. It codifies decisions from four internal docs (`django-project-setup`, `django-local-subdomain-setup`, `django-media-storage`, `django-unfold-admin`) and is the only place where defaults (time zone, CORS hosts, OKLCH palette, DRF page size) are decided.

## Goals / Non-Goals

**Goals**
- One-command local dev: `./dev.sh` brings up the app at `https://clients.localhost` via `tmux` + `portless`.
- Env-first settings: no secret, host, or storage flag hard-coded in `settings.py`.
- Storage abstraction that works locally (filesystem) and in prod (S3/DO Spaces) with the same code paths.
- Admin look-and-feel defined once in `UNFOLD` and overridable per environment.
- A deployable artifact: `Dockerfile` + `start.sh` that builds static during image build and runs gunicorn in :80.
- OpenSpec `project.md` populated with stack, conventions, dev/deploy commands.

**Non-Goals**
- Domain models, serializers, views, business logic (no `core/models.py` beyond the auto-generated scaffold).
- Authentication flows beyond DRF defaults (`TokenAuthentication` + `SessionAuthentication`) and Unfold's User/Group admin overrides.
- Email/SMTP — explicitly skipped per user.
- Celery/Redis/background workers.
- Production secrets management (Coolify ARGs are the boundary; no Vault/AWS SM integration).
- CI workflows (GitHub Actions, etc.).
- Frontend.

## Decisions

### 1. Env-first via `python-dotenv` over `django-environ` / `python-decouple`
**Choice:** `python-dotenv` loaded in two passes from `settings.py` — first `.env` to read `ENV`, then `.env.<ENV>`.
**Why:** Matches the team's existing `django-project-setup` doc verbatim. Two-phase load is sufficient because the only meta-variable is `ENV` itself. No need for type casting (we coerce booleans/ints ourselves) or interpolation features we don't use.
**Alternatives:** `django-environ` (richer casting, but extra dep, not in current `requirements.txt`); `python-decouple` (mentioned in the subdomain doc, but `dotenv` is what the main setup doc mandates and `decouple` doesn't natively load a per-env file cascade).

### 2. Project module named `project/` (not `clients/`)
**Choice:** The Django settings package is `project/`; the primary app is `core/`. The repo dir is `clients`.
**Why:** Decouples code import path from repo name so the repo can be renamed without touching `import` lines or `STORAGES` backend dotted paths. Matches the doc's `project.storage_backends.*` references.
**Alternatives:** Name the package `clients` (causes import path collision risk with the `core` app if a future app is also called `clients`; harder to read in `INSTALLED_APPS`).

### 3. Three S3 storage backends (Static / Public / Private) over a single bucket prefix
**Choice:** `StaticStorage`, `PublicMediaStorage`, `PrivateMediaStorage` in `project/storage_backends.py`, each pointing to a different `location` under `AWS_PROJECT_FOLDER`.
**Why:** Static files benefit from long-lived cache headers and `public-read`; user uploads need `public-read` but `file_overwrite = False`; private documents (contracts, IDs) need signed URLs and must bypass any CDN (`custom_domain = False`). Mixing these into one bucket prefix would force all uploads to share an ACL.
**Alternatives:** Two backends (drop private) — rejected because the doc explicitly defines a private tier and `utils/media.py` is shaped around it. One backend (everything public) — rejected on security grounds.

### 4. `STORAGE_AWS` toggles a full `STORAGES` block, not per-backend overrides
**Choice:** `if STORAGE_AWS: STORAGES = {... S3 ...} else: STORAGES = {... FileSystem ...}`.
**Why:** `STORAGES` is a single source of truth in Django 4.2+; mixing backends per key depending on env produces surprising precedence. A clean branch keeps the two code paths auditable.
**Alternatives:** Always set `STORAGES` to S3 backends and override `default` with `FileSystemStorage` in dev — works but obscures the dev path and makes `.env.dev` flags the only thing keeping local dev working.

### 5. `DRF` defaults: `IsAuthenticated`, `TokenAuthentication`, custom pagination
**Choice:** `DEFAULT_PERMISSION_CLASSES = ("rest_framework.permissions.IsAuthenticated",)`; auth = `TokenAuthentication` + `SessionAuthentication`; pagination = `CustomPageNumberPagination` (page_size 12, max 100, exposes `count/next/previous/page/page_size/total_pages/results`); exception handler wraps every error as `{status, message, data}`.
**Why:** Matches doc. Authenticated-by-default prevents accidental public endpoints; rich pagination payload is what the team's frontend expects (per the `leochan.sh` template that this project forks from).
**Alternatives:** `AllowAny` default — rejected (no project should ship that as the default). Cursor pagination — rejected (frontend is already wired to page-number).

### 6. `django-unfold` placed before `django.contrib.admin` in `INSTALLED_APPS`
**Choice:** `unfold`, `unfold.contrib.{filters,forms,inlines}` first, then `django.contrib.admin`.
**Why:** Unfold monkey-patches admin templates via template loader precedence. If `django.contrib.admin` is registered first, its templates win and Unfold's overrides are ignored.
**Alternatives:** Use `TEMPLATES[0]['OPTIONS']['loaders']` reordering — works but is harder to reason about and breaks if Django changes loader semantics.

### 7. Admin template override extends `admin/base.html`, not `unfold/layouts/base.html`
**Choice:** `project/templates/admin/base_site.html` → `{% extends "admin/base.html" %}`.
**Why:** Unfold's internal layout handles the sticky bottom bar and responsive grid. Extending it directly risks breaking that. The `admin/base.html` shim is what Unfold is designed to be extended through.
**Alternatives:** Extend `unfold/layouts/base.html` and re-implement the sticky bar — fragile and version-coupled.

### 8. `dev.sh` uses Case A (vanilla) from the subdomain doc
**Choice:** Single tmux window running `portless clients --app-port $PORT -- python manage.py runserver $PORT`. No Celery, no frontend.
**Why:** User confirmed vanilla project. Port auto-increment (`ss -tuln` loop from 8000) keeps multiple projects conflict-free. Re-attach on subsequent runs.
**Alternatives:** Bare `python manage.py runserver` (no subdomain, no TLS — breaks cookies/sessions for OAuth and is harder to share with webhooks). Full Case B (Celery + Redis + Stripe) — out of scope for bootstrap.

### 9. `Dockerfile` ARGs vs. runtime env for AWS creds
**Choice:** All sensitive vars (DB, AWS, `SECRET_KEY`, `ALLOWED_HOSTS`) are Docker `ARG`s, exported as `ENV`s so the build-time `RUN python manage.py collectstatic` can reach S3. Runtime override is via Coolify env.
**Why:** `collectstatic` needs credentials at build time. If we relied on runtime env only, static files wouldn't make it into the bucket during image build. The doc codifies this; deviating silently breaks deploys.
**Alternatives:** Two-stage build (build stage has creds, runtime stage doesn't) — adds complexity without security gain since secrets are in the image layer either way at build time.

### 10. OpenSpec `project.md` populated, not left as a template
**Choice:** Fill in the tech stack, dev command (`./dev.sh`), deploy command (`Dockerfile` + Coolify), and the four internal doc references.
**Why:** Future OpenSpec proposals need this context. Leaving it empty forces every future change to re-establish the stack.
**Alternatives:** Skip `project.md` (it's optional in the schema) — rejected because the team uses OpenSpec to coordinate every change.

## Risks / Trade-offs

- **`STORAGE_AWS=True` in prod with empty S3 creds will break `collectstatic` at build time** → Mitigation: `.env.prod` ships with explicit empty values; deploy step in Coolify must populate ARGs before first build. Tasks include a pre-deploy checklist.
- **Local Postgres dependency** → Mitigation: `.env.dev` defaults to Postgres, but the dynamic DB block falls back to sqlite if `DB_NAME` is empty. Tasks include a "verify local Postgres exists" step; if absent, the user can temporarily set `DB_ENGINE=django.db.backends.sqlite3` in `.env.dev`.
- **`SECRET_KEY` committed in `.env`** → Mitigation: `.env` is git-ignored per `.gitignore`. A 50+ char random key is generated and dropped in only at the dev step; prod uses a Coolify-provided key.
- **`STORAGE_AWS` env-var string vs boolean mismatch** → The doc coerces with `os.getenv(...) == "True"`. Inconsistency (`"true"` vs `"True"`) silently falls back to local storage → Mitigation: tasks call out the exact `True` casing and add a smoke test that toggles it.
- **Unfold version drift** → Pinned to `0.77.1` in `requirements.txt`. Upgrades require touching `UNFOLD` config keys that often rename between minors → Mitigation: tasks include a "verify Unfold renders at `/admin/`" smoke step after install.
- **Portless not installed on dev machine** → Mitigation: `dev.sh` calls `portless proxy start && portless trust` which is a no-op-friendly first-run but will fail loudly if the binary is missing; tasks list it as a prereq.
- **No automated tests in the skeleton** → The `core` app is a stub; no model tests yet. `python manage.py test` will pass (no tests defined) but won't validate the storage/admin paths → Mitigation: tasks include a `manage.py check` + a manual `/admin/` and `/api/` smoke test, not unit tests, since requirements are not yet defined.
- **OKLCH primary palette chosen as neutral purple (hue 296) in the doc** → May not match the `clients` brand → Mitigation: tasks include swapping the palette (one constant change) before the first visual review.
- **`STATIC_LOCATION` / `PUBLIC_MEDIA_LOCATION` / `PRIVATE_MEDIA_LOCATION` referenced by `project/storage_backends.py` but only defined inside the `STORAGE_AWS=True` branch** → Hidden assumption: `storage_backends` is only imported via `STORAGES` when S3 is active. If any code path imports it in dev, Django raises `AttributeError`. → Mitigation: tasks 3.1 and the new `s3-media-storage` requirement define these constants unconditionally with safe local defaults.
- **Source docs contradict on admin template inheritance** → `django-project-setup.md` line 502 extends `unfold/layouts/base.html`; `django-unfold-admin.md` line 356 extends `admin/base.html` with an explicit warning in §8 against extending the internal layout. The `unfold-admin` doc is canonical. → Mitigation: `unfold-admin-theme` spec and task 3.10 pin `admin/base.html`; design decision 7 records the rationale.
- **No `.dockerignore` in source doc** → `Dockerfile` does `COPY . /app/`, which would ship `venv/`, `.env*`, `.git/`, etc. into the image and leak prod secrets into the build layer. → Mitigation: new task 7.1 creates a `.dockerignore` and the `production-deploy` spec requires it.
- **Source doc `INSTALLED_APPS` omits `rest_framework.authtoken`** → `TokenAuthentication` requires this app to create the `authtoken_token` table; without it migrations won't include the table and `ObtainAuthToken` will fail at runtime. → Mitigation: task 3.2 adds it; `env-driven-config` spec requires it.
- **Deliberate divergence from source doc on `.env`** → Source doc has `ENV=prod` in `.env` (because it was written for an already-deployed project). This bootstrap uses `ENV=dev` because the project is greenfield. Acceptable, but documented here to avoid future "fix" of "inconsistency" with the doc.
- **Deliberate divergence on `.env.dev` `DB_NAME`** → Source doc leaves `DB_NAME=` empty (falling back to sqlite default). This bootstrap uses `DB_NAME=clients` to target a local Postgres DB. If local Postgres is not available, the user can either create the `clients` database or temporarily set `DB_ENGINE=django.db.backends.sqlite3` in `.env.dev`.

## Migration Plan

This is a greenfield bootstrap, so no migration of existing data. Deploy steps once code is pushed:

1. **Local:** `./dev.sh` → visit `https://clients.localhost/admin/`, log in with `createsuperuser` creds, verify Unfold theme renders, verify the empty `/api/` route returns the DRF browsable API root.
2. **Image build (Coolify):** pass all `ARG`s as Build Environment Variables; confirm `collectstatic` uploads to the configured bucket.
3. **First run (Coolify):** `start.sh` runs `migrate --noinput` and starts gunicorn on :80. Verify `/admin/` and `/api/` are reachable on the production hostname.
4. **Rollback:** delete the deploy in Coolify; no data loss (no models shipped yet).

## Open Questions

- **OpenSpec `project.md`** — does the user want to fill it by hand or have me draft the content? (Tasks will draft it; user can edit.)
- **Brand color** — keep the doc's purple OKLCH palette or swap to a different hue? (Tasks will keep purple as the default; user can change one block.)
- **Local Postgres availability** — confirmed by user, but tasks include a "verify connection" step that will surface any issue.
- **AWS/DO creds for prod** — none yet; tasks leave `.env.prod` placeholders empty and flag this in the deploy checklist.
