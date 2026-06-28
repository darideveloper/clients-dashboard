## 1. Configure sidebar to auto mode

- [x] 1.1 In `project/settings.py`, replace `UNFOLD["SIDEBAR"]["navigation"]` (the two-group list with `Authentication` and `Core`) with an empty list `[]`.
- [x] 1.2 In the same `SIDEBAR` block, set `show_all_applications: True` (was `False`). Keep `show_search: True`.

## 2. Create sidebar template override

- [x] 2.1 Create `project/templates/unfold/helpers/navigation.html`. The template SHALL extend Unfold's sidebar chrome: load `i18n` and `unfold` template tags, render `<nav id="nav-sidebar-inner" class="...">` (copy Tailwind classes from the bundled `unfold/helpers/navigation.html`).
- [x] 2.2 In the override, `{% include "unfold/helpers/navigation_header.html" %}` then `{% include "unfold/helpers/search.html" %}` (preserves header and search input).
- [x] 2.3 Add a body block that, when `sidebar_navigation|length == 0`, iterates over `available_apps` and renders each app as a collapsible Unfold-style group (matching the DOM in `venv/lib/python3.12/site-packages/unfold/templates/unfold/helpers/app_list.html` lines 9-47). The first group MUST NOT emit a top `<hr class="border-t border-base-200 mx-6 my-2 dark:border-base-800" />` separator; subsequent groups MUST emit one.
- [x] 2.4 Inside each group, iterate over `app.models` and render each model as an `<li><a href="{{ model.admin_url }}" class="...active-classes...">...</a></li>` with the Material `database` icon. Apply the `active` class set when `model.admin_url in request.path`. Skip models whose `admin_url` is `None` or empty.
- [x] 2.5 Add a fallback paragraph for the case when `available_apps` is empty (no registered models visible to the user): render the translated message "You don't have permission to view or edit anything." using the same `unfold/helpers/messages/error.html` partial Unfold uses at `app_list.html:91-93`.
- [x] 2.6 Close the override with `{% include "unfold/helpers/navigation_user.html" %}` to preserve the user menu at the bottom of the sidebar.

## 3. Verify

- [x] 3.1 Run `python manage.py check` — no template load errors.
- [x] 3.2 Run the dev server (`./dev.sh` or `python manage.py runserver`) and log in as a superuser. Confirm the sidebar shows one collapsible group per installed app with at least one registered `ModelAdmin`, and that `Authentication` (Users, Groups) and every `core` model are listed. (Verified server-side via Django test client: override template loaded, 3 app groups rendered, Users/Groups/Profile links present, chevron toggle, `navigation_user` partial included.)
- [x] 3.3 Create or use a non-superuser test account with limited perms (e.g. only `view` on one `core` model). Log in and confirm only that model is visible and its app group is shown; other apps are absent. (Verified: limited user with only `view_profile` sees Profile link; no Users/Groups link.)
- [x] 3.4 Log in as a user with no admin permissions; confirm the sidebar shows the "You don't have permission to view or edit anything." message and the rest of the admin chrome (header, user menu) is intact. (Verified: user with no perms sees the error message via `unfold/helpers/messages/error.html` partial.)
- [x] 3.5 Navigate to a model's changelist and confirm the active link is highlighted with the Unfold `active` class set. (Verified: GET /admin/auth/user/ adds the full Unfold `active` class set to the Users link.)

## 4. Document

- [x] 4.1 Update `/home/daridev/Desktop/obsidian/daridev/20-areas/work/django/django-unfold-admin.md` §3 to reflect the new `SIDEBAR` config (`show_all_applications: True`, `navigation: []`, no curated groups) and add a short note pointing to the new override template at `project/templates/unfold/helpers/navigation.html`.
