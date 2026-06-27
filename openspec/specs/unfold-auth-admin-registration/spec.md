# unfold-auth-admin-registration Specification

## Purpose
TBD - created by archiving change fix-unfold-auth-admin. Update Purpose after archive.
## Requirements
### Requirement: Unfold auth admins are registered in a loaded app
The Unfold-styled `UserAdmin` and `GroupAdmin` SHALL be registered in a module that Django imports on startup. They SHALL be registered by unregistering Django's default `User` and `Group` admins from `django.contrib.auth.admin` and re-registering them with the Unfold subclasses defined in this capability. The registration module SHALL live in an app that is listed in `INSTALLED_APPS` (currently `core/admin.py`); the `project/` package SHALL NOT host the registration because it is not an installed app.

#### Scenario: User changelist uses Unfold theme
- **WHEN** a superuser opens `/admin/auth/user/`
- **THEN** the page renders with the Unfold admin theme (Unfold's sidebar, site header, and form styling are present) and the row-action button defined by `ModelAdminUnfoldBase.actions_row` is available on each row.

#### Scenario: Group changelist uses Unfold theme
- **WHEN** a superuser opens `/admin/auth/group/`
- **THEN** the page renders with the Unfold admin theme and the row-action button defined by `ModelAdminUnfoldBase.actions_row` is available on each row.

#### Scenario: Default auth admins are unregistered
- **WHEN** Django starts and loads the auth admin module
- **THEN** `admin.site.unregister(User)` and `admin.site.unregister(Group)` run before the Unfold subclasses are registered, leaving exactly one registration for each model.

### Requirement: Unfold auth admin forms
The registered `UserAdmin` SHALL set `form = unfold.forms.UserChangeForm`, `add_form = unfold.forms.UserCreationForm`, and `change_password_form = unfold.forms.AdminPasswordChangeForm`. The registered `GroupAdmin` SHALL NOT override forms (it uses Unfold's defaults via `ModelAdminUnfoldBase`).

#### Scenario: User change form uses Unfold styling
- **WHEN** a superuser opens `/admin/auth/user/<id>/change/`
- **THEN** the form is rendered using `unfold.forms.UserChangeForm` (Unfold-styled inputs, fieldsets, and submit controls).

#### Scenario: User add form uses Unfold styling
- **WHEN** a superuser opens `/admin/auth/user/add/`
- **THEN** the form is rendered using `unfold.forms.UserCreationForm` (Unfold-styled inputs and submit controls).

#### Scenario: Password change form uses Unfold styling
- **WHEN** a superuser opens `/admin/auth/user/<id>/password/`
- **THEN** the form is rendered using `unfold.forms.AdminPasswordChangeForm`.

### Requirement: Auth admins inherit ModelAdminUnfoldBase
`UserAdmin` and `GroupAdmin` SHALL inherit from `project.admin_base.ModelAdminUnfoldBase` (which itself extends `unfold.admin.ModelAdmin`) mixed with the matching Django base (`BaseUserAdmin` / `BaseGroupAdmin`). The MRO SHALL place the Django base before `ModelAdminUnfoldBase` so Django's fieldsets, list filters, and save behaviour are preserved while Unfold's UI and the project's row-action / unsaved-form / compressed-fields enhancements are layered on top.

#### Scenario: Future model admin consistency
- **WHEN** any other model in the project (e.g. a `Client` model in `core/`) is registered with a `ModelAdminUnfoldBase` subclass
- **THEN** the User/Group changelists present the same per-row "Edit" action, unsaved-form confirmation, compressed fields, and cancel button as that other model.

#### Scenario: Unfold theme is applied to change forms
- **WHEN** a superuser opens the User or Group change form
- **THEN** Unfold's template, form styling, and the `ModelAdminUnfoldBase` enhancements are visible (none of Django's classic admin markup is rendered for the form area).

