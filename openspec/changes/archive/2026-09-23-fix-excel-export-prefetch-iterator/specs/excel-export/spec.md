## MODIFIED Requirements

### Requirement: Per-model Excel export via bulk actions
Every changelist-based `ModelAdmin` that inherits `project.admin_base.ModelAdminUnfoldBase` (and `TokenAdmin` as `class TokenAdmin(ModelAdminUnfoldBase, BaseTokenAdmin)`) SHALL expose two Django admin bulk actions operating on the checkbox-selected queryset, declared with `unfold.decorators.action` and gated on `view` so read-only models remain exportable (`AppSettings` singleton has no changelist and is excluded — covered by the full-app header action):

- **Export to Excel** (`export_selected`) — single sheet, no related sheets.
- **Export to Excel (with related)** (`export_selected_with_related`) — main sheet plus one sheet per directly-related model (forward FK/OneToOne only, single hop).

Both actions SHALL be declared as `@action(description="Export to Excel", icon="download", permissions=["view"])` / `@action(description="Export to Excel (with related)", icon="download", permissions=["view"])`, SHALL define `has_export_selected_permission` / `has_export_selected_with_related_permission` delegating to `has_view_permission`, SHALL optimize the queryset via `select_related(*fk_names)` after clearing unused prefetches via `prefetch_related(None)` and iterate via `.iterator(chunk_size=2000)` (explicit chunk size so incoming changelist querysets carrying `prefetch_related`, e.g. `OrderAdmin`'s `order_types` / `items__product__currency` prefetches, never raise `ValueError`), and SHALL return an `HttpResponse` with `Content-Type: application/vnd.openxmlformats-officedocument.spreadsheetml.sheet` and RFC 5987 `Content-Disposition: attachment; filename="..." ; filename*=utf-8''...` (filename sanitized, non-ASCII handled). The main queryset received from the admin is the already-filtered selected set — the action SHALL NOT re-fetch via `request.POST["_selected_action"]`. Selecting no rows and invoking the action SHALL call `self.message_user(request, "Select at least one row to export.", messages.WARNING)` and return `None` (no file).

#### Scenario: Export selected rows without related data
- **WHEN** a staff user ticks 3 `InvitationCode` rows and runs "Export to Excel"
- **THEN** the downloaded workbook contains one sheet named after the model and exactly 3 data rows (plus header), and no additional sheets

#### Scenario: Export selected rows with related data (forward FKs only)
- **WHEN** a staff user ticks 2 `InvitationCode` rows (referencing Project A/B and Organization X) and runs "Export to Excel (with related)"
- **THEN** the workbook contains a main `InvitationCode` sheet with 2 rows plus separate `Project` and `Organization` sheets each containing only the referenced rows (deduped via `target.objects.filter(pk__in=distinct_ids)`), and contains no `StripeEvent` or transitive sheets

#### Scenario: Empty selection shows warning
- **WHEN** a user runs either export action with no rows selected
- **THEN** the admin displays a warning message "Select at least one row to export." and no file is downloaded

#### Scenario: Permission gated on view (read-only models included)
- **WHEN** a user without `view` permission on a model loads its changelist
- **THEN** the export actions are not available for that model
- **WHEN** a user with `view` but not `change` on `StripeEvent` (which has `has_change_permission=False`) loads the `StripeEvent` changelist
- **THEN** the export actions are still available (gated on `view`, not `change`)

#### Scenario: Singleton note
- **WHEN** a user opens the `AppSettings` singleton admin (no changelist)
- **THEN** per-model bulk actions are not surfaced there; AppSettings is still exported via the full-app header action

#### Scenario: Export tolerates prefetch-carrying queryset (Order regression)
- **WHEN** a staff user ticks `Order` rows (whose changelist queryset carries `prefetch_related`, e.g. `order_types` and `items__product__currency`) and runs either "Export to Excel" action
- **THEN** the request succeeds with `200` and a valid `.xlsx` (header + selected rows) instead of `ValueError: chunk_size must be provided when using QuerySet.iterator() after prefetch_related()`

### Requirement: Related sheets contain referenced rows only
When `include_related` is true, for each distinct forward FK/OneToOne target model of the exported model, the workbook SHALL include one additional sheet named after the target model containing only the rows referenced by the selected queryset (distinct, via `pk__in` of the collected FK ids; related querysets use `.iterator(chunk_size=2000)`; the fallback ID-collection path SHALL also use `chunk_size=2000` when iterating the incoming queryset). The main sheet SHALL still contain the two FK columns (`__str__` + `_id`). Reverse relations, M2M, and transitive (second-hop) models SHALL NOT produce sheets.

#### Scenario: Related sheets are referenced-only
- **WHEN** 5 `InvitationCode`s are selected that collectively reference 2 distinct `Project`s out of 10 total projects
- **THEN** the `Project` sheet contains exactly 2 rows regardless of total projects in the DB

#### Scenario: No transitive sheets
- **WHEN** a model A has FK to B and B has FK to C, and A is exported with related
- **THEN** the workbook contains sheets for A and B only, not C

#### Scenario: With-related export tolerates prefetch-carrying queryset
- **WHEN** `Order` rows (queryset with `prefetch_related`, e.g. `order_types` and `items__product__currency`) are exported with related data
- **THEN** the workbook contains the main `Order` sheet plus forward-FK target sheets with referenced rows only, with no `ValueError`
