## Context

The repo integrates `django-unfold` to theme the admin. The Obsidian doc `20-areas/work/django/django-unfold-admin.md` section 7.1 prescribes an Unfold-styled registration for `User` and `Group` and places it in `project/admin.py`. The repo follows that prescription verbatim, but `project` is not in `INSTALLED_APPS` (`project/settings.py:38-55`), so Django's admin autodiscovery never imports `project/admin.py`. The `admin.site.unregister(User)`, `admin.site.unregister(Group)`, and `@admin.register(...)` calls inside that file are dead code.

Consequences observed in the running admin:

1. User/Group changelists render with Django's default admin (classic Django markup), not Unfold — the `unfold.forms.UserChangeForm` / `UserCreationForm` / `AdminPasswordChangeForm` assignments are never applied.
2. `UNFOLD["SIDEBAR"]` is configured with `show_all_applications=False` and a manual `navigation` array. The `Authentication` section's `items` lists only `Users`; `Groups` is absent. Because auto-discovery is disabled, the Group changelist is hidden from the sidebar (it remains reachable at `/admin/auth/group/` but users do not see it).
3. The `ModelAdminUnfoldBase` helper (`project/admin_base.py`) provides `compressed_fields`, `warn_unsaved_form`, `list_filter_sheet`, `change_form_show_cancel_button`, and a per-row `edit` action. The doc's section 8 says all model admins in the project should inherit it; the dead `UserAdmin`/`GroupAdmin` do not, so auth models are the only ones in the project missing those enhancements.

Stakeholders: project owner (sees a half-themed admin), future developers adding models (need a consistent pattern).

## Goals / Non-Goals

**Goals:**
- Make the Unfold `User`/`Group` admins actually load at startup.
- Surface the Group changelist in the sidebar so users can find it.
- Make `UserAdmin` and `GroupAdmin` consistent with every other model admin in the project by inheriting `ModelAdminUnfoldBase`.
- Keep the change small, reversible, and free of migrations or new dependencies.

**Non-Goals:**
- Replacing Django's `User` model with a custom user model.
- Changing the `User`/`Group` model fields, permissions, or `AUTH_PASSWORD_VALIDATORS`.
- Restyling the auth admin templates manually (Unfold's templates are the source of truth).
- Adding or removing other sidebar nav sections.
- Localising the `Authentication` / `Users` / `Groups` strings beyond what `gettext_lazy` already wraps (the doc already uses `_()`).

## Decisions

### Decision 1: Move registration to `core/admin.py` (not register `project` as an app)
**Why:** `core` is already in `INSTALLED_APPS` (`project/settings.py:48`), and `core/admin.py` is auto-imported by Django on startup. Moving the existing block requires zero `INSTALLED_APPS` or `AppConfig` changes, keeps the change small, and avoids creating a no-op `project` app.

**Alternatives considered:**
- *Add `project` to `INSTALLED_APPS` and create `project/apps.py`.* Works, but introduces a new app whose only purpose is to host `admin.py`. Adds an `AppConfig`, a `default_auto_field`, and migration directories. More surface area for the same outcome.
- *Move registration into a new `accounts` app.* Out of scope: no model lives there, and it would conflict with Django's `auth` app naming conventions.

### Decision 2: Inherit `ModelAdminUnfoldBase` (not bare `unfold.admin.ModelAdmin`)
**Why:** `ModelAdminUnfoldBase` extends `unfold.admin.ModelAdmin` and adds `compressed_fields=True`, `warn_unsaved_form=True`, `list_filter_sheet=False`, `change_form_show_cancel_button=True`, and `actions_row=["edit"]`. Using it on `UserAdmin`/`GroupAdmin` gives auth models the same row-action button and unsaved-form warning as every other model in the project (per doc section 8), so the user no longer sees an inconsistent admin area.

**MRO:** `class UserAdmin(BaseUserAdmin, ModelAdminUnfoldBase)` resolves to `UserAdmin → BaseUserAdmin → ModelAdminUnfoldBase → unfold.admin.ModelAdmin → django.contrib.admin.ModelBase → object`. Django's `BaseUserAdmin` comes first so its fieldsets, list filters, and `save_model` are preserved; Unfold's `ModelAdmin` (and the project subclass) is consulted afterwards for template rendering and Unfold-specific attrs. This is the standard Unfold pattern (Unfold's own docs mix `BaseUserAdmin` with `unfold.admin.ModelAdmin`); substituting a subclass for `ModelAdmin` is non-breaking.

**Alternatives considered:**
- *Keep `unfold.admin.ModelAdmin` (literal doc example).* Leaves auth models inconsistent with the rest of the project. The user already asked for "design doesn't look good", which is partly driven by this inconsistency.
- *Inherit from `ModelAdminUnfoldBase` only (drop `BaseUserAdmin` / `BaseGroupAdmin`).* Would require re-implementing User/Group fieldsets, filters, and password change URL manually. High risk of regression; no upside.

### Decision 3: Delete `project/admin.py`
**Why:** After Decision 1, the file is unreachable. Leaving it as dead code is a future footgun: a developer may "fix" the file expecting it to take effect, or a test runner may pick it up and re-introduce duplicate registrations. Deleting is the safest end state.

**Alternatives considered:**
- *Leave the file with a one-line docstring* (`# Auth admin registration moved to core/admin.py`). Defensible if any tooling expects the file to exist; in this repo nothing does. Delete is cleaner.

### Decision 4: Add a `Groups` entry to the sidebar (not enable auto-discovery)
**Why:** The doc's section 2.2 (`UNFOLD["SIDEBAR"]`) explicitly sets `show_all_applications=False` to allow manual grouping. Flipping it to `True` would expose every registered model under the `Authentication` and `Core` sections automatically, but it would also bypass the curated `navigation` list — undesirable because future apps (e.g. `store`) would silently appear in the sidebar before their UI is reviewed.

**Icon:** Material Symbols `group` (consistent with the doc's `person` icon for Users; alternative `groups` is acceptable but `group` matches the Material "single group" glyph and the doc's icon naming convention).

**Translation:** the existing `Authentication` section already uses `gettext_lazy` (`_(...)`) for its `title` and `Users` `title`. The new `Groups` entry follows the same pattern.

## Risks / Trade-offs

- **[Risk] `actions_row = ["edit"]` is redundant on User/Group because the default changelist row already links to the change page.** → Acceptable: the button is consistent with other models and the `permissions=["change"]` guard means users without change permission won't see it. If undesired, it can be overridden on `UserAdmin`/`GroupAdmin` with `actions_row = []` without touching the base.
- **[Risk] MRO with `ModelAdminUnfoldBase` could shadow a Django auth-admin method.** → Unlikely: `ModelAdminUnfoldBase` only adds new attrs and one custom `@action`; it does not override Django's `save_model`, `get_fieldsets`, `get_queryset`, or form overrides. The `form` / `add_form` / `change_password_form` assignments on `UserAdmin` are preserved.
- **[Risk] Deleting `project/admin.py` could break an external tool that imports it.** → Nothing in this repo imports it (`grep` of `project/admin.py` references shows zero importers). Safe to delete.
- **[Risk] `core/admin.py` may grow as the project adds models.** → Fine: that is the standard place for `core` app admin code. `core/apps.py` already exists and `core` is in `INSTALLED_APPS`.
- **[Risk] Migrations or DB changes required?** → None. `User` and `Group` are unchanged. `INSTALLED_APPS` order is unchanged. `UNFOLD` config edits are settings-only.
- **[Trade-off] Future auth models (custom user, profile) will also need to inherit `ModelAdminUnfoldBase`.** → Documented in the new `unfold-auth-admin-registration` spec.

## Migration Plan

Single deploy. Steps:

1. Replace `core/admin.py` with the new contents (registration block).
2. Delete `project/admin.py`.
3. Edit `project/settings.py` `UNFOLD["SIDEBAR"]["navigation"]` `Authentication.items` to add the `Groups` entry.
4. Run `python manage.py check` to confirm no admin duplication errors.
5. Run `python manage.py runserver`, log in, verify:
   - Sidebar shows `Users` and `Groups` under `Authentication`.
   - `/admin/auth/user/` renders with Unfold theme and the per-row "Edit" action.
   - `/admin/auth/group/` renders with Unfold theme and the per-row "Edit" action.
   - User change/add/password pages use Unfold-styled forms.

**Rollback:** revert the three file changes (no DB migration to undo). If a cached `staticfiles` build is in use, rerun `collectstatic` after reverting.

## Open Questions

None. The only ambiguity (whether to use `ModelAdminUnfoldBase` on auth admins) was resolved with the user.
