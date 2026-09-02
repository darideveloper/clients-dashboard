## Context

`AppSettingsAdmin` at `ourlives/admin.py:54` is the only singleton admin: `class AppSettingsAdmin(SingletonModelAdmin, OurlivesExportMixin, ModelAdminUnfoldBase)` with `actions_list` and `actions_detail = ["export_all"]` from `project/admin_base.py:93`. Unfold renders change-form header buttons via `unfold/templates/admin/change_form.html:13` (`nav-global` → `change_form_object_tools`) → `unfold/helpers/userlinks.html:8` (`{% action_list %}`) → `unfold/helpers/tab_actions.html:3` (flex `<ul>` containing `{{ nav_global }}` then `actions_detail`). Solo ships `solo/templates/admin/solo/change_form.html` which overrides `object-tools-items` with raw `<li><a class="historylink">History</a></li>`, bypassing Unfold's `unfold/helpers/tab_action.html` and its `action_item_classes` (`border`, `min-lg:-ml-px`, `px-3 py-2`, `whitespace-nowrap`). Export's `-ml-px` therefore pulls it over History's unstyled 1-px-wide hit area, visible as overlap at `/admin/ourlives/appsettings/` on `lg` (≥1024px). Additionally the stock `tab_actions.html` `<ul>` has no gap, so even styled siblings would touch with collapsed borders and have no small spacing, and raw History would not be vertically centered. Other `ourlives` admins (`ProjectAdmin`, `OrganizationAdmin`, etc.) inherit `OurlivesModelAdminBase` without `SingletonModelAdmin` and are unaffected.

Project conventions: `TEMPLATES[0].DIRS = [BASE_DIR/project/templates]` (priority over app templates), existing overrides at `project/templates/admin/base.html`, `project/templates/admin/login.html`, and `project/templates/unfold/helpers/navigation.html`, all admin bases in single source `project/admin_base.py` (no `ourlives/admin_base.py`), Unfold history enabled via `UNFOLD["SHOW_HISTORY"] = True` at `project/settings.py:233`.

## Goals / Non-Goals

**Goals:**
- Eliminate overlap of History and Export all app data on the singleton AppSettings header at all breakpoints, preserving both actions.
- Preserve solo's breadcrumb behavior for `SOLO_ADMIN_SKIP_OBJECT_LIST_PAGE=True` (default).
- Follow Django template-override and Unfold `tab_action.html` idioms; change nothing in `project/admin_base.py` / `ourlives/admin.py` MRO.

**Non-Goals:**
- Changing export semantics, permissions (`has_export_all_permission`), workbook generation, or `ModelAdminUnfoldBase` / `OurlivesExportMixin` APIs.
- Adding CSS/JS, touching `static/`, or introducing new dependencies.
- Fixing non-singleton admins (already correct via Unfold's default `change_form_object_tools.html`).

## Decisions

**D1: Project template override `project/templates/admin/solo/change_form.html` (chosen)**
- Override solo's template via `DIRS` precedence, not `change_form_template` on the ModelAdmin.
- File extends `admin/change_form.html`, re-implements `breadcrumbs` block verbatim from solo (preserving `skip_object_list_page` guard), and replaces `object-tools-items` with Unfold's styled includes (see guardian example at `unfold/contrib/guardian/templates/admin/guardian/model/change_form.html`).
- Rationale: canonical Django mechanism for third-party template fixes; already used in this repo for `admin/base.html`; keeps `AppSettingsAdmin` declaration compliant with `AGENTS.md` singleton rule (`SingletonModelAdmin` first); one-file, reversible fix.
- Alternative considered: set `change_form_template = "admin/change_form.html"` on `AppSettingsAdmin`. Rejected — loses solo breadcrumbs unless re-added elsewhere and obscures that the ModelAdmin is a singleton; template override is more explicit and matches how solo's documented `skip_object_list_page` breadcrumb is intended to coexist with custom themes.
- Alternative considered: forking/patching `solo` in `venv`. Rejected — violates project constraint to not vendor-edit installed packages.

**D2: Use `unfold/helpers/tab_action.html` for History and View-on-site + add gap in `tab_actions.html` — no custom CSS/JS beyond template override**
- Content of `object-tools-items` in `project/templates/admin/solo/change_form.html`:
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
  Matches `unfold/templates/admin/change_form_object_tools.html:8`. Gives both items `action_item_classes` so `tab_actions.html` flex row has two uniformly-bordered siblings; `-ml-px` now collapses a real border rather than overlapping text.
- Additionally override `project/templates/unfold/helpers/tab_actions.html` as copy of stock with `gap-2` / `lg:gap-2` added to the header `<ul>` (`class="... hidden flex-col gap-2 ... lg:flex lg:flex-row lg:gap-2 ..."`) so a small visible spacing appears between History and Export at desktop (`row gap`) and mobile (`flex-col` gap). Vertical centering is via existing chain `div.flex-row.items-center` → `a.flex.grow.items-center gap-2 px-3 py-2` in `tab_action.html`; no extra CSS needed.
- Alternative: hand-written CSS negative-margin fix or inline `style="margin-left:8px"`. Rejected — fragile against Unfold version bumps; the correct fix is to make siblings share the same component and add Tailwind gap via template override, matching existing `navigation.html` override pattern.

**D3: No new capability — delta specs only**
- Behavior change is presentational (header layout), not a new domain capability. Spec deltas record the layout contract so regression is detectable.
- Alternative: create new `singleton-header` capability. Rejected — over-fragments; this belongs under existing `unfold-admin-theme` and `admin-managed-settings`.

## Risks / Trade-offs

- **Solo version bump changes `change_form.html`:** Template override is pinned to solo 2.x structure (breadcrumbs + object-tools-items only). → Mitigation: override is small and mirrors Unfold's own override; diff on upgrade is to compare `site-packages/solo/templates/admin/solo/change_form.html` (two blocks) and re-apply. No Python coupling.
- **Unfold `tab_action.html` API change (icon/variant/attrs):** Wrapper signature could shift. → Mitigation: using stable `title/link/icon` params from `unfold/templates/admin/change_form_object_tools.html`; Unfold documents this as public extension point (guardian example).
- **Future singletons inherit the fix automatically (intended but may surprise):** Any new `SingletonModelAdmin` gets the corrected header. → Mitigation: desired — documents that singleton headers MUST be Unfold-styled.
- **Mobile breakpoint styling:** `tab_actions.html:9` (`max-lg:absolute`, hamburger). Both styled buttons participate in the same `showActions` toggle, so no new mobile-only overlap; verify in QA.

## Migration Plan

1. Add `project/templates/admin/solo/change_form.html` and `project/templates/unfold/helpers/tab_actions.html` (gap-2) as specified.
2. No DB migration, no setting change, no `collectstatic` required (templates only).
3. Deploy; no rollback data concerns — removing the files restores stock behavior (re-introduces overlap/tight spacing, no breakage).
4. Verify manually (no automated template-render test added to keep change minimal; existing admin tests, if any, continue to pass).

## Open Questions

- None blocking. Optional follow-up: should the singleton header also expose a dropdown for future `actions_detail` growth? Out of scope — keep single `Export all app data` button; use Unfold dropdown pattern from `docs/actions/dropdown-actions.md` if a second detail action is added later.
