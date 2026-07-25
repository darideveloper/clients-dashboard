## Context

The codebase has a `Project` model (name + description) that invitation codes FK to. We need an additional `Organization` dimension on invitation codes — an Organization represents the billing/account entity, while a Project represents technical scope. Both are independent concepts; an invitation code can belong to any combination.

Current state: `InvitationCode.project` (FK, required)

Target state: `InvitationCode.project` (FK, required) + `InvitationCode.organization` (FK, required)

## Goals / Non-Goals

**Goals:**
- New `Organization` model with `name` (unique) and `description`
- `InvitationCode` gains a required `organization` FK
- Admin UI supports managing Organizations and filtering/searching invitation codes by organization
- `import_invitation_codes` command accepts `--organization` as a required argument

**Non-Goals:**
- No validation rules on Organization (internal control only)
- No user-facing API endpoints — admin-only for now
- No changes to the `Project` model or its relationship with InvitationCode
- No token-pool changes (tokens remain global, not per-organization)

## Decisions

| Decision | Choice | Rationale |
|---|---|---|
| Organization name uniqueness | Unique (matches Project convention) | Data integrity constraint, not business validation. Required for deterministic name-based lookup in management command (same pattern as Project). |
| Organization FK nullability | Required (non-null) | Every invitation code must be traceable to an organization; avoids nullable-FK complexity |
| Deletion protection | `on_delete=PROTECT` | Matches `InvitationCode.project` — prevents accidental cascade deletion |
| Organization FK related_name | Default (`invitationcode_set`) — no explicit `related_name` | Avoids collision with `project` FK which already uses `related_name="invitation_codes"` on the same model |
| Organization admin tab position | Between Project and InvitationCode in sidebar | Alphabetical by model name would be fine, but explicit ordering in sidebar makes navigation clearer |
| Backfill strategy for existing codes | Data migration: prompt user to specify a default organization name, or create "Legacy" org automatically | All existing invitation codes need an organization assigned before the non-null FK is applied |

## Risks / Trade-offs

| Risk | Mitigation |
|---|---|
| Existing invitation codes have no organization | Data migration in a separate migration step — create a default org and assign all existing codes to it before adding the non-null constraint |
| `import_invitation_codes` grows another required arg | Backward-compatible: if `--organization` is omitted, propose keeping existing codes as-is; but the new arg SHOULD be required going forward to match the model constraint |
| Two separate FK lookups (project + org) in admin list display could slow down | Both are indexed by default (FKs get DB indexes), and the codebase is small — no performance concern|
