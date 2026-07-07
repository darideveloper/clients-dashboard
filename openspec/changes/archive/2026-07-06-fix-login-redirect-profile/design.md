## Context

Django's `LoginView` (used by admin) redirects to `settings.LOGIN_REDIRECT_URL` after successful authentication when no `next` parameter is present. The Django default is `/accounts/profile/`, which doesn't exist in this project.

The admin login can be reached directly at `/admin/login/` (without `?next=/admin/`), for example when a user bookmarks it, or when the `next` param is invalid. In those cases, Django falls back to `LOGIN_REDIRECT_URL`.

## Goals / Non-Goals

**Goals:**
- Redirect to `/admin/` after successful admin login, regardless of how the login page was reached
- Minimal change — one-line config addition

**Non-Goals:**
- No new views, URLs, or auth flow changes
- No changes to brand middleware, login templates, or other auth components

## Decisions

| Decision | Choice | Rationale |
|---|---|---|
| Where to set LOGIN_REDIRECT_URL | `project/settings.py` | Standard Django convention. No env-var needed — `/admin/` is always correct for this project. |
| Value | `"/admin/"` | Matches existing root `RedirectView` target. Named URL `admin:index` could be used but a hardcoded path is simpler and works with Django's `LOGIN_REDIRECT_URL` which doesn't resolve named URLs. |
| Should this be env-configurable? | No | The admin URL is fixed. No use case for changing it per environment. |

## Risks / Trade-offs

- **Risk: None.** This is a single-line settings change with no side effects. Django's `LoginView` always reads `LOGIN_REDIRECT_URL` at import time, and `/admin/` is a valid path in the project.
