## Why

The django-unfold admin currently registers `User` and `Group` with Unfold styling in `project/admin.py`, but that module is never imported at runtime because the `project` package is not in `INSTALLED_APPS`. As a result the User/Group changelists render with Django's default admin (no Unfold theme) and the sidebar only links to Users — Groups is invisible in the navigation despite being registered by `django.contrib.auth`. The fix wires the Unfold auth admins into a loaded app, exposes Groups in the sidebar, and aligns the auth admins with `ModelAdminUnfoldBase` so they share the same row actions, compressed fields, and unsaved-form warnings as every other model in the project.

## What Changes

- Move the Unfold User/Group admin registration from `project/admin.py` (dead code) into `core/admin.py` so it is actually executed (the `core` app is already in `INSTALLED_APPS`).
- Make `UserAdmin` and `GroupAdmin` inherit `ModelAdminUnfoldBase` instead of bare `unfold.admin.ModelAdmin`, so they pick up `compressed_fields`, `warn_unsaved_form`, `list_filter_sheet`, `change_form_show_cancel_button`, and the per-row `edit` action.
- Delete the unused `project/admin.py` file.
- Add a `Groups` entry under the `Authentication` section of `UNFOLD["SIDEBAR"]["navigation"]` in `project/settings.py` so the Group changelist is reachable from the sidebar (which uses `show_all_applications=False` and therefore relies on manual nav entries).

No migrations, no new dependencies, no model changes. No **BREAKING** changes for end users — only the admin UI for User/Group becomes Unfold-themed and a new nav item appears.

## Capabilities

### New Capabilities

- `unfold-auth-admin-registration`: defines where and how the Unfold-styled `User` and `Group` admins are registered, which forms they use, and which base class they inherit.

### Modified Capabilities

- `unfold-admin-theme`: add a requirement that the `Authentication` sidebar section exposes both `Users` and `Groups` admin links (previously only Users). Existing requirements about Unfold app ordering, the `UNFOLD` config block, the `Unfolded auth admin` registration, the admin template override, `ModelAdminUnfoldBase`, the `utils` package, and static assets are unchanged in intent but the `Unfolded auth admin` requirement is refined to point at `core/admin.py` instead of `project/admin.py` and to require `ModelAdminUnfoldBase` as the base.

## Impact

- `core/admin.py` — gains the Unfold auth admin registration block (4 imports, 2 unregisters, 2 `@admin.register` classes).
- `project/admin.py` — deleted.
- `project/settings.py` — `UNFOLD["SIDEBAR"]["navigation"]` `Authentication.items` gains a `Groups` entry.
- No model, migration, URL, or static-asset changes.
- No new dependencies.
- Affected admin URLs (unchanged paths, new look): `/admin/auth/user/`, `/admin/auth/user/<id>/change/`, `/admin/auth/user/add/`, `/admin/auth/user/<id>/password/`, `/admin/auth/group/`, `/admin/auth/group/<id>/change/`.
- Existing superusers continue to work; existing users/groups are not modified.
