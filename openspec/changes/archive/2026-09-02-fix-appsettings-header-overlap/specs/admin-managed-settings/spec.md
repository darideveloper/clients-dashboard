# Delta: admin-managed-settings — header layout clarification

## ADDED Requirements

### Requirement: Singleton changeform header layout (no overlap)

The `AppSettings` singleton changeform at `/admin/ourlives/appsettings/` SHALL render the header object-tools as two styled siblings (History and Export all app data) without visual overlap and with a small gap and vertical centering at desktop (`lg`, ≥1024px) and in the collapsed hamburger at `<lg`. This is achieved by the project overrides `project/templates/admin/solo/change_form.html` and `project/templates/unfold/helpers/tab_actions.html` (`gap-2` / `lg:gap-2`) described under `unfold-admin-theme`. `AppSettingsAdmin` SHALL keep its declaration `class AppSettingsAdmin(SingletonModelAdmin, OurlivesExportMixin, ModelAdminUnfoldBase)` (`SingletonModelAdmin` first, export mixin next — `project/admin_base.py` remains the single source for admin bases per `AGENTS.md`) and SHALL NOT set `change_form_template` to bypass solo; the template overrides are the supported mechanism. The functional contract of `AppSettings` (singleton `storage_base_url`, superuser-only editing) remains unchanged.

#### Scenario: Overlapping bug is fixed on singleton
- **WHEN** a staff user with `ourlives` module perms (any `is_staff` user passing `has_export_all_permission`) loads `/admin/ourlives/appsettings/` (the singleton changeform rendered via `admin/solo/change_form.html` + `tab_actions.html` gap)
- **THEN** the History button and the Export all app data header button are rendered as adjacent `tab_action.html` items in the header's flex row with a visible gap (`gap-2` / `lg:gap-2`) without overlapping text or borders, both are vertically centered, and both are clickable.

#### Scenario: Singleton MRO unchanged
- **WHEN** `AppSettingsAdmin.__mro__` is inspected
- **THEN** `SingletonModelAdmin` appears before `OurlivesExportMixin` and `ModelAdminUnfoldBase`, preserving solo singleton routing (`^$` → `change_view`, `^history/$` → `history_view`).

#### Scenario: Export permission unchanged on singleton
- **WHEN** a staff user without `ourlives` module perms loads `/admin/ourlives/appsettings/`
- **THEN** History remains (gated by Unfold's `show_history`) and Export all app data is hidden (Unfold checks `has_export_all_permission` → `has_module_perms("ourlives")`), with no empty placeholder causing layout shift.
