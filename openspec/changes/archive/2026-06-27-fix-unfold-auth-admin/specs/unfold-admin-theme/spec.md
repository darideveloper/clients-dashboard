## MODIFIED Requirements

### Requirement: Unfolded auth admin
`core/admin.py` SHALL unregister Django's default `User` and `Group` admins and re-register them using `project.admin_base.ModelAdminUnfoldBase` (which extends `unfold.admin.ModelAdmin`) mixed with `BaseUserAdmin` / `BaseGroupAdmin`. The `User` admin SHALL use `unfold.forms.UserChangeForm`, `unfold.forms.UserCreationForm`, and `unfold.forms.AdminPasswordChangeForm`. The `Group` admin SHALL NOT override forms. The registration SHALL live in `core/admin.py` (not `project/admin.py`) because `core` is in `INSTALLED_APPS` and `project` is not. See the `unfold-auth-admin-registration` capability for the full registration contract.

#### Scenario: User form uses Unfold
- **WHEN** an admin opens the user change form at `/admin/auth/user/<id>/change/`
- **THEN** the form is rendered with Unfold's `UserChangeForm` styling.

#### Scenario: Group form uses Unfold
- **WHEN** an admin opens the group change form at `/admin/auth/group/<id>/change/`
- **THEN** the form is rendered with the Unfold theme (no Django classic admin markup in the form area) and `ModelAdminUnfoldBase` enhancements (row action, compressed fields, warn-unsaved, cancel button) are present.

#### Scenario: Auth admin registration lives in core
- **WHEN** Django starts and `core/apps.py` is loaded
- **THEN** `core/admin.py` is imported and the Unfold `User`/`Group` admins are registered; `project/admin.py` is not loaded (it is not in `INSTALLED_APPS`).

## ADDED Requirements

### Requirement: Authentication sidebar exposes Users and Groups
`UNFOLD["SIDEBAR"]["navigation"]` SHALL include a section titled `Authentication` (or its translated equivalent) whose `items` list contains both a `Users` entry linking to `admin:auth_user_changelist` and a `Groups` entry linking to `admin:auth_group_changelist`. The section SHALL be `collapsible=False` so the entries are visible without interaction. Because `UNFOLD["SIDEBAR"]["show_all_applications"]` is `False`, the manual `items` list is the sole source of auth-related nav links.

#### Scenario: Groups is reachable from the sidebar
- **WHEN** a superuser renders any admin page
- **THEN** the sidebar shows a `Groups` link under the `Authentication` section, the link's `href` resolves to `/admin/auth/group/`, and clicking it loads the Unfold-styled Group changelist.

#### Scenario: Users link is unchanged
- **WHEN** a superuser renders any admin page
- **THEN** the `Users` link under the `Authentication` section is still present and still resolves to `/admin/auth/user/`.
