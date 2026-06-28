# unfold-admin-theme Specification

## Purpose
TBD - created by archiving change init-django-clients-project. Update Purpose after archive.
## Requirements
### Requirement: Unfold app ordering
`INSTALLED_APPS` SHALL list `unfold`, `unfold.contrib.filters`, `unfold.contrib.forms`, and `unfold.contrib.inlines` BEFORE `django.contrib.admin`.

#### Scenario: Unfold overrides admin templates
- **WHEN** an admin page is rendered
- **THEN** the Unfold-styled template is used (Unfold's `SITE_HEADER` "clients Admin" appears in the sidebar)

### Requirement: Unfold config block
`settings.UNFOLD` SHALL set `SITE_TITLE`, `SITE_HEADER`, `SITE_SUBHEADER`, `SITE_URL="/"`, `SITE_ICON` resolving to `static("favicon.png")` (overridden per-user by `utils.callbacks.site_icon`, which sources from `user.brand.logo.url`), `SITE_LOGO` resolving to `static("logo.webp")`, `SITE_SYMBOL`, `SITE_FAVICONS` containing a 32×32 PNG whose `href` resolves via `utils.callbacks.site_favicon(request)` (per-brand callback falling back to `static("favicon.png")`), `SHOW_HISTORY=True`, `SHOW_VIEW_ON_SITE=True`, `ENVIRONMENT` pointing to `utils.callbacks.environment_callback`, `THEME="light"`, an OKLCH `primary` color palette covering shades 50–950, and a `SIDEBAR` block with `show_search=True`, `show_all_applications=True`, and an empty `navigation: []`. The sidebar body SHALL be rendered by the override template `project/templates/unfold/helpers/navigation.html`, which auto-renders every registered `ModelAdmin` filtered by the request user's per-model permissions; see the `unfold-permission-sidebar` capability for the rendering contract.

#### Scenario: Site branding
- **WHEN** the admin loads
- **THEN** the sidebar shows the favicon/logo and the site header text "clients Admin"

#### Scenario: Per-brand favicon in browser tab
- **WHEN** an authenticated user with a brand logo loads the admin
- **THEN** the browser tab icon SHALL be the brand's generated 32×32 favicon (sourced from `utils.callbacks.site_favicon`)

#### Scenario: Fallback favicon for brands without logo
- **WHEN** an authenticated user whose brand has no logo loads the admin
- **THEN** the browser tab icon SHALL fall back to `static("favicon.png")`

#### Scenario: Environment badge
- **WHEN** `ENV=dev` and `utils.callbacks.environment_callback` runs
- **THEN** it returns `["Development", "info"]`

#### Scenario: Sidebar uses auto-render with permission filter
- **WHEN** a user loads any admin page
- **THEN** the sidebar body is populated from `available_apps` (permission-filtered by Django's `AdminSite.get_app_list`) via the override template at `project/templates/unfold/helpers/navigation.html`, and `UNFOLD["SIDEBAR"]["navigation"]` is `[]`.

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

### Requirement: Admin template override
`project/templates/admin/base_site.html` SHALL extend `admin/base.html` (NOT `unfold/layouts/base.html` — extending the internal layout breaks Unfold's sticky bottom bar and responsive grid; this contradicts the `django-project-setup` doc which shows `unfold/layouts/base.html`, but `django-unfold-admin` doc §8 is the canonical guidance). The template SHALL load `simplemde.min.css`, `simplemde.min.js` from the SimpleMDE CDN, the local `static/css/style.css`, and the local JS files `add_tailwind_styles.js`, `load_markdown.js`, and `range_date_filter_es.js`.

#### Scenario: Markdown editor injected
- **WHEN** an admin form contains a `textarea`
- **THEN** SimpleMDE replaces the textarea after the page loads (verified by the presence of `.editor-toolbar` in the DOM)

### Requirement: ModelAdminUnfoldBase reusable class
`project/admin_base.py` SHALL define a `ModelAdminUnfoldBase` class extending `unfold.admin.ModelAdmin` with `compressed_fields = True`, `warn_unsaved_form = True`, `list_filter_sheet = False`, `change_form_show_cancel_button = True`, and `actions_row = ["edit"]`. It SHALL expose an `edit(object_id)` action that redirects to the change view of the bound model. Future model admins in the project SHALL inherit from this class so the row-action button and unsaved-form warning are consistent.

#### Scenario: Future model admin inherits base
- **WHEN** a future change introduces `class ClientAdmin(ModelAdminUnfoldBase)` in `core/admin.py`
- **THEN** the change list shows a per-row "Edit" action and leaving the change form with unsaved data shows a confirmation prompt

### Requirement: utils package is importable
The `utils/` package SHALL be located at the repo root (not inside `project/`) and SHALL be importable as `utils.callbacks.environment_callback`. This relies on `manage.py` adding `BASE_DIR` to `sys.path` (Django default), so `BASE_DIR` SHALL remain the repo root.

#### Scenario: Unfold resolves the environment callback
- **WHEN** the admin renders with `ENV=dev`
- **THEN** `utils.callbacks.environment_callback` is invoked and returns `["Development", "info"]`

### Requirement: Static assets for admin enhancements
The repo SHALL include `static/css/style.css` with markdown preview typography rules, `static/js/add_tailwind_styles.js` that adds Tailwind utility classes to `.btn` and `.img-preview` elements, `static/js/load_markdown.js` that wires SimpleMDE to all textareas, and `static/js/range_date_filter_es.js` that localizes the `created_at_from/to` and `updated_at_from/to` placeholders to `Desde` / `Hasta`.

#### Scenario: Range date filter localized
- **WHEN** the admin renders a list filter for `created_at`
- **THEN** the `created_at_from` input's `placeholder` attribute is `Desde` and `created_at_to` is `Hasta`

