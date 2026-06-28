## Context

Current state (`project/settings.py:241-269`): `UNFOLD["SIDEBAR"]` has `show_all_applications=False` and a hand-written `navigation` list with two groups (`Authentication` for Users/Groups, an empty `Core` group). Adding a model requires editing `settings.py`; non-superusers see links for models they cannot act on.

Unfold's `SIDEBAR` machinery (`venv/lib/python3.12/site-packages/unfold/sites.py:339`, `navigation.html`, `app_list.html`) has three modes:
1. `navigation` non-empty → renders Unfold-styled groups via `unfold/helpers/app_list.html`. The "All applications" modal at the bottom of that template is gated on `sidebar_show_all_applications`.
2. `navigation` empty → `unfold/helpers/navigation.html:11` falls back to Django's classic `admin/app_list.html` (table markup, not Unfold-styled).
3. There is **no built-in** Unfold-styled "auto sidebar" mode that renders every registered app in the sidebar body.

Django's `AdminSite.get_app_list(request)` (`django/contrib/admin/sites.py:541`, used to build `available_apps` in `each_context`) **already** filters models by `model_admin.has_module_permission(request)` and `get_model_perms(request)` at lines 488-496. So `available_apps` is the natural permission-filtered source.

`project/` already has the template-override infrastructure described in `django-unfold-admin.md §2.2` (`project/templates/` is configured as a templates dir).

## Goals / Non-Goals

**Goals**
- Sidebar body renders all apps and models in Unfold styling (not Django's classic table).
- Each model appears only if the request user has `view` or `change` perms for it (Django default behavior via `available_apps`).
- Apps whose models are all filtered out disappear entirely.
- Zero changes required when adding a new `ModelAdmin` to `core/`.
- Superusers continue to see everything (no behavior change for them).

**Non-Goals**
- Per-user custom ordering, hiding items the user technically has access to, or per-model custom icons in auto mode.
- Overhauling the search/command palette.
- Migrating auth/groups out of `core/admin.py`; the Unfold registration contract from `unfold-auth-admin-registration` stays.
- Changing the dashboard `/admin/` page styling (it already uses `unfold/helpers/app_list_default.html` via `unfold/templates/admin/index.html:14`).

## Decisions

### Decision 1: Template override at `unfold/helpers/navigation.html`, not a custom AdminSite
Unfold resolves the sidebar template by `{% include "unfold/helpers/navigation.html" %}` in `nav_sidebar.html:10`. Overriding the helper template via Django's template loader is the lowest-blast-radius change:
- No subclass of `AdminSite` to register.
- No context processor.
- Survives Unfold upgrades as long as the include site (`nav_sidebar.html:10`) and the helper's external context contract (`available_apps`, `sidebar_navigation`, `sidebar_show_all_applications`, `sidebar_show_search`) stay stable.
- A custom `AdminSite` (alternative) would require touching `project/urls.py`, re-registering all admins, and fighting with `core/apps.py`.

**Alternative considered:** subclass `unfold.sites.AdminSite` and override `get_sidebar_list` to translate `available_apps` into Unfold's `navigation` group shape. Rejected: more moving parts, two parallel sources of truth (Django `available_apps` + Unfold `sidebar_navigation`), and the Unfold helper template would still need the auto-rendering branch.

### Decision 2: Render `available_apps` directly in the override, not translate to `sidebar_navigation`
`available_apps` is already permission-filtered and is the canonical source for Django's admin index. The override reuses it and renders each app as a collapsible group with each model as a sidebar link — the same visual contract as the existing `app_list.html` rendering for manual nav groups. We keep `sidebar_navigation` empty in `settings.py`, so the original Unfold branch (`{% include "unfold/helpers/app_list.html" %}`) is never taken.

**Alternative considered:** populate `sidebar_navigation` from `available_apps` via a context processor and let Unfold's existing template do the work. Rejected: requires translating model metadata (icon, badge, etc.) that Unfold's schema does not carry; Unfold's `app_list.html` would also need to skip the `app_list` dropdown branch.

### Decision 3: Default icon `database` for auto-rendered models, no per-model icon customization
The Unfold manual `navigation` schema supports `icon` per item. Auto mode has no such hook. Use a single Material icon (`database`) for all auto-rendered model links. Adding per-model icon customization in auto mode would require either a model attribute or a registry; out of scope.

**Alternative considered:** introspect `model._meta` for an `icon` attribute via a `ModelAdmin` mixin. Rejected: increases scope, no immediate consumer.

### Decision 4: `show_all_applications` kept, but its purpose is now empty
With the override handling the sidebar body, the "All applications" dropdown button at the bottom of `unfold/helpers/app_list.html` is never rendered (we never include that template in the empty-nav branch). Setting `show_all_applications` to `True` or `False` becomes a no-op for the sidebar. We set it to `True` defensively to match the conceptual intent ("auto"), but document that the override supersedes it.

### Decision 5: New file `project/templates/unfold/helpers/navigation.html`
Sits in the same dir Unfold loads from. Follows the project's existing template override pattern (`project/templates/admin/base_site.html` from `django-unfold-admin.md §6`).

## Risks / Trade-offs

- **Unfold upgrade risk** → The override mirrors Unfold's current `app_list.html` markup for groups. Pin `django-unfold==0.77.1` (already pinned in `requirements.txt` per `django-unfold-admin.md §1`) and re-test on upgrade. Mitigation: keep the override small and well-commented; the Unfold changelog is the source of truth for breakage.
- **No per-model icon in auto mode** → Documented; future change can introduce a `ModelAdmin.icon` mixin. Mitigation: trade-off explicitly accepted, single icon keeps the sidebar consistent.
- **No way to pin/hide a specific model for everyone** → With manual nav gone, you cannot hide, say, `LogEntry` from the auto sidebar short of unregistering its admin. Mitigation: out of scope; can be revisited by reintroducing manual nav as a hybrid layer.
- **Unfold's "All applications" modal no longer reachable** → Acceptable; the sidebar body already lists every app. Mitigation: none needed; document.
- **Permission filtering inherits Django defaults** → `view` and `change` perms gate visibility; `add` alone does not. This matches Django's admin index behavior, so users will not be surprised. Mitigation: if a future need arises (e.g. `add`-only users seeing the changelist), use `ModelAdmin.has_module_permission` override.

## Migration Plan

1. **Apply** the override template and the `settings.py` change in the same commit. No DB impact.
2. **Verify** as superuser: every registered `ModelAdmin` in `INSTALLED_APPS` is visible in the sidebar, grouped by app, collapsible.
3. **Verify** as a non-superuser with limited perms: only the apps/models the user has `view`/`change` access to are visible.
4. **Verify** as a user with no admin perms: sidebar shows the existing "You don't have permission to view or edit anything." message (this comes from `admin/app_list.html:50` if we ever fall through, or we replicate it in the override).
5. **Rollback**: revert the two files; original manual nav is restored.

## Open Questions

- Should the "All applications" dropdown button be removed entirely from the user's experience, or kept as a no-op for future restoration? (Decision 4 says no-op; can be revisited.)
- Do we want a `core/admin.py` mixin that adds a `sidebar_icon` attribute to `ModelAdminUnfoldBase` for the auto mode? Deferred — not in scope of this change.
