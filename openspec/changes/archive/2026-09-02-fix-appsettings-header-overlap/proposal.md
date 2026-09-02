## Why

At `/admin/ourlives/appsettings/` the header shows **History** and **Export all app data** overlapping. Root cause: `AppSettingsAdmin` uses `SingletonModelAdmin` (`solo`), whose `solo/templates/admin/solo/change_form.html` overrides `object-tools-items` with a raw `<li><a class="historylink">` — bypassing Unfold's styled `unfold/helpers/tab_action.html`. Unfold's `tab_actions.html` renders `nav_global` (History) and `actions_detail` (Export) in the same flex `<ul>`; Export's `action_item_classes` (`min-lg:-ml-px`, border) assumes a styled sibling, so its negative margin pulls Export over the unstyled History text, causing overlap.

## What Changes

- Add a project template override `project/templates/admin/solo/change_form.html` that restores Unfold-compatible header buttons while preserving solo's breadcrumb behavior for `SOLO_ADMIN_SKIP_OBJECT_LIST_PAGE=True` (the default).
- Replace the raw History `<li>` with `{% include "unfold/helpers/tab_action.html" with title=title link=link icon="history" %}` (and matching `View on site` handling), matching the idiomatic Unfold pattern (`unfold/contrib/guardian/templates/admin/guardian/model/change_form.html` and `unfold/templates/admin/change_form_object_tools.html`).
- Add a project template override `project/templates/unfold/helpers/tab_actions.html` (copy of `unfold` stock with `gap-2` / `lg:gap-2` added to the header `<ul>`) so History and Export have a small visible spacing at desktop (`lg` row gap) and mobile (`flex-col` gap) and History is vertically centered via the existing `flex items-center` chain (`div.flex-row.items-center` + `a.flex.grow.items-center`).
- No changes to `project/admin_base.py` or `ourlives/admin.py` admin bases/MRO; `AppSettingsAdmin(SingletonModelAdmin, OurlivesExportMixin, ModelAdminUnfoldBase)` and `OurlivesModelAdminBase` remain as the single source for export actions.
- Verification via manual QA: History and Export render side-by-side with gap without overlap at desktop (`lg`) and collapse into the hamburger menu with vertical gap at `<lg`; both buttons are vertically centered; history/history-view routing unaffected.

## Capabilities

### New Capabilities
- none — this is a bug fix to an existing presentation layer; no new capability.

### Modified Capabilities
- `unfold-admin-theme`: Header object-tools rendering for singleton change forms SHALL use Unfold-styled `tab_action.html` so History (and View on site) share the same `action_item_classes` as Unfold `actions_detail` buttons, eliminating overlap. Captured as a delta spec.
- `admin-managed-settings`: Clarify/confirm `AppSettingsAdmin` remains a singleton with `SingletonModelAdmin` first in MRO and uses the corrected template; no functional behavior change but adds a header-layout scenario.

## Impact

- Affected code: `project/templates/admin/solo/change_form.html` and `project/templates/unfold/helpers/tab_actions.html` (new files, override `solo` and `unfold` stock templates via `DIRS` precedence); no Python/admin registration changes.
- Dependencies: `unfold`, `django-solo`. Uses existing Unfold helper `unfold/helpers/tab_action.html` and Django `TEMPLATES[0].DIRS` precedence — no new dependencies.
- Risk: Low. Pure template overrides; reversible by deleting the files. No DB migration, no permission change.
