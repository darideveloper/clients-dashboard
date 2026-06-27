## 1. Move Unfold auth admin registration to core

- [x] 1.1 Replace `core/admin.py` with the Unfold auth admin registration block: import `BaseUserAdmin`, `BaseGroupAdmin`, `User`, `Group`, `ModelAdminUnfoldBase`, `AdminPasswordChangeForm`, `UserChangeForm`, `UserCreationForm`; call `admin.site.unregister(User)` and `admin.site.unregister(Group)`; define `UserAdmin(BaseUserAdmin, ModelAdminUnfoldBase)` with `form`, `add_form`, `change_password_form`; define `GroupAdmin(BaseGroupAdmin, ModelAdminUnfoldBase)` with `pass`.

## 2. Remove dead project admin module

- [x] 2.1 Delete `project/admin.py` (the file is not in `INSTALLED_APPS` so it is dead code after step 1).

## 3. Surface Groups in the admin sidebar

- [x] 3.1 Edit `project/settings.py` `UNFOLD["SIDEBAR"]["navigation"]` and add a `Groups` entry inside the `Authentication` section's `items` list. The entry uses `gettext_lazy` (`_("Groups")`), the `group` Material Symbols icon, and `reverse_lazy("admin:auth_group_changelist")` as its `link`. Place it directly after the existing `Users` entry.

## 4. Verify

- [x] 4.1 Run `python manage.py check` and confirm no `AlreadyRegistered` errors and no admin autodiscovery warnings.
- [x] 4.2 Run `python manage.py runserver`, log in as a superuser, and confirm:
  - Sidebar shows `Users` and `Groups` under `Authentication`.
  - `/admin/auth/user/` renders with the Unfold theme and per-row "Edit" action button.
  - `/admin/auth/group/` renders with the Unfold theme and per-row "Edit" action button.
  - User change form, user add form, and user password form use Unfold-styled inputs.
  - Leaving the User or Group change form with unsaved data shows the confirmation prompt (`warn_unsaved_form`).
