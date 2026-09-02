# Delta: unfold-admin-theme — singleton header fix

## MODIFIED Requirements

### Requirement: Admin template override
`project/templates/admin/base_site.html` SHALL extend `admin/base.html` (NOT `unfold/layouts/base.html` — extending the internal layout breaks Unfold's sticky bottom bar and responsive grid; this contradicts the `django-project-setup` doc which shows `unfold/layouts/base.html`, but `django-unfold-admin` doc §8 is the canonical guidance). The template SHALL load `simplemde.min.css`, `simplemde.min.js` from the SimpleMDE CDN, the local `static/css/style.css`, and the local JS files `add_tailwind_styles.js`, `load_markdown.js`, and `range_date_filter_es.js`.

Additionally, singleton change forms (any `ModelAdmin` inheriting `solo.admin.SingletonModelAdmin`) SHALL NOT render raw `solo/templates/admin/solo/change_form.html` history markup. The project SHALL provide `project/templates/admin/solo/change_form.html` overriding solo's default, extending `admin/change_form.html` and implementing `object-tools-items` via Unfold's helper so header buttons share Unfold's `action_item_classes` and do not overlap in `unfold/helpers/tab_actions.html`.

Specifically, the override `project/templates/admin/solo/change_form.html` SHALL:

- Extend `admin/change_form.html` and load `i18n admin_urls`.
- Preserve solo's `breadcrumbs` block: when `skip_object_list_page` is true, render `Home › <app_config.verbose_name> › <verbose_name>`; otherwise `{{ block.super }}` (matching `solo` 2.x).
- Render `object-tools-items` as:
  ```django
  {% if show_history %}
    {% url opts|admin_urlname:'history' original.pk|admin_urlquote as history_url %}
    {% trans 'History' as title %}{% add_preserved_filters history_url as link %}
    {% include "unfold/helpers/tab_action.html" with title=title link=link icon="history" %}
  {% endif %}
  {% if has_absolute_url and show_view_on_site %}
    {% trans 'View on site' as title %}
    {% include "unfold/helpers/tab_action.html" with title=title link=absolute_url blank=1 icon="open_in_new" %}
  {% endif %}
  ```
  matching `unfold/templates/admin/change_form_object_tools.html` and the `guardian/change_form.html` example, so both History and Unfold `actions_detail` items (e.g. `Export all app data`) are rendered as `<li class="{% action_item_classes %}"><a class="flex gap-2 px-3 py-2 whitespace-nowrap">` siblings inside the same `tab_actions.html` flex `<ul>`.

The override SHALL live at `project/templates/admin/solo/change_form.html` (taking precedence via `TEMPLATES[0].DIRS = [BASE_DIR/project/templates]` over `solo` app templates) and SHALL NOT add custom CSS/JS.

The project SHALL also provide `project/templates/unfold/helpers/tab_actions.html` as a copy of `unfold` stock `tab_actions.html` with `gap-2` and `lg:gap-2` added to the header `<ul>` (`class="... hidden flex-col gap-2 ... lg:flex lg:flex-row lg:gap-2 ..."`), so History and Export (and any `actions_list`/`actions_detail` siblings) have a small visible spacing at desktop (row gap) and mobile (column gap) and remain vertically centered via the existing `flex flex-row items-center` parent and `a.flex grow items-center` in `tab_action.html`. The override SHALL be a minimal diff against stock (only the added gap classes) and SHALL NOT add custom CSS/JS.

#### Scenario: History and Export share Unfold styling on singleton
- **WHEN** a staff user with `ourlives` perms loads `/admin/ourlives/appsettings/` (singleton changeform with `actions_detail=["export_all"]`)
- **THEN** the header `<ul>` contains two `<li>` elements rendered via `unfold/helpers/tab_action.html` — one titled `History` with `icon="history"` and one titled `Export all app data` with `icon="download"` — each with `action_item_classes` borders and `px-3 py-2` padding, displayed in a single `lg:flex-row` with a small gap (Tailwind `gap-2` / `lg:gap-2`) without text overlap, and both buttons are vertically centered via `flex items-center`.

#### Scenario: Gap between History and Export at desktop and mobile
- **WHEN** the header is rendered at `lg` (≥1024px, `lg:flex-row`) and at `<lg` (e.g. 768px, `flex-col` hamburger `max-lg:flex`)
- **THEN** the `<ul>` has `gap-2` (mobile column gap) and `lg:gap-2` (desktop row gap) so a visible 0.5rem spacing separates the two `<li>` siblings in both layouts, and no `-ml-px`/`-mt-px` text overlap occurs.

#### Scenario: Mobile collapses both buttons into hamburger
- **WHEN** the viewport is `<lg` (e.g. 768px)
- **THEN** both History and Export appear under the `more_horiz` toggle in `tab_actions.html` (`max-lg:absolute`, `x-show="showActions"`), with no absolute-position overlap.

#### Scenario: History link still navigates correctly
- **WHEN** a staff user clicks History on the singleton changeform
- **THEN** the browser navigates to `admin:ourlives_appsettings_history` (solo's `^history/$` route) and the history page renders.

#### Scenario: Solo breadcrumbs preserved when skip_object_list_page is true
- **WHEN** `SOLO_ADMIN_SKIP_OBJECT_LIST_PAGE` is `True` (default) and the singleton changeform is rendered
- **THEN** the breadcrumbs block shows `Home › <app_config.verbose_name> › <verbose_name>` from the override, not Django's default `opts` breadcrumbs.

#### Scenario: No overlap regression on non-singleton ourlives admins
- **WHEN** a staff user loads any non-singleton ourlives changelist or changeform (e.g. `/admin/ourlives/project/`)
- **THEN** the override is not used (template path `admin/solo/change_form.html` not in that render branch) and Unfold's default `change_form_object_tools.html` continues to render History correctly alongside `actions_detail` without overlap.
