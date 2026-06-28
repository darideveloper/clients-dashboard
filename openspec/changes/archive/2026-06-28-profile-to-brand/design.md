## Context

Today the admin personalizes branding *per user* via a 1:1 `Profile` (fields: `avatar`, `primary_color`). The personal `avatar` is rendered in two distinct spots:

1. Top-left header brand logo — via `utils.callbacks.site_icon`, used by Unfold `SITE_ICON`.
2. Bottom-left user-profile circle — via Unfold's `unfold/helpers/navigation_user.html` reading `request.user.avatar_url`.

Real product need is multi-tenant: one **company** (brand) is shared by many **employees** (users). The per-user profile conflates personal avatar (unused) with company branding (used in header). Also, the bottom-left circle is visually redundant — only the top-left company logo is meaningful.

Current implementation touchpoints: `core/models.py`, `core/signals.py`, `core/admin.py`, `utils/callbacks.py`, `project/settings.py`, and `project/templates/admin/base.html`.

## Supersedes

This change **fully retires** two existing capabilities, declared via `## REMOVED Requirements` deltas inside this change:

- `openspec/specs/user-profile/` (archived from `2026-06-27-add-user-profile`) — `Profile` model, `User.avatar_url`, `post_save` auto-creation signal, `ProfileInline`, `avatar_thumb` changelist column, backfill data migration, `SITE_ICON` "viewer" behavior. Every requirement is removed; the 2 MB logo upload cap and the storage-backend contract are re-stated inside `brand-management` so the new capability is self-contained.
- `openspec/specs/per-user-primary-color/` — `Profile.primary_color` and the per-user `oklch(from)` palette injection. The field is reparented to `Brand`; the injection becomes per-brand; both live in `brand-management`.

After this change is archived, `brand-management` is the single living capability covering brand identity in the admin. The two retired capabilities are removed from `openspec/specs/`.

## Goals / Non-Goals

**Goals:**
- Convert `Profile` (1:1 with `User`) into `Brand` (1:N from `User`) so many users share one brand's logo + primary color.
- Remove the bottom-left personal avatar menu picture; replace with the default `person` material icon.
- Keep the top-left site-icon and per-brand primary-palette CSS behavior, now sourced from the user's `Brand`.
- Provide a data migration that preserves existing per-user profiles (one brand per existing profile, plus fallback default brand).
- Restrict brand assignment of users to superusers only in the admin.

**Non-Goals:**
- Self-service brand assignment for non-superusers (permission model is out of scope beyond "superusers only").
- Multi-brand-per-user (a user belongs to exactly one brand).
- Removing/extending the primary_color validator behavior.
- Touching Unfold's site-icon in the header itself (only its data source changes).
- A brand-admin role (manager of a brand) — not introduced now.

## Decisions

### Decision 1: Reuse the existing `Profile` model as `Brand` (rename) rather than introduce a new model
A clean rename preserves the migration history chain and avoids parallel degenerate `Profile` → new `Brand` mappings. The side-effect is that `user.profile` becomes `user.brand`; the concept "this row customizes the admin chrome" is preserved and just shifts from per-user to per-company.

**Alternatives considered**
- Introduce a new `Company` model and repoint callbacks to `user.company.*` while deleting `Profile`. More churn, two migrations (create company, drop profile), and a more complex back-fill that 1:1-maps rows. Rejected — equivalent outcome, more code.
- Keep `Profile` name but change its meaning to "company". Rejected — name is misleading. Rename wins on clarity.

### Decision 2: `User.brand` is exposed via a `Membership` OneToOne carrier (with `on_delete=PROTECT` on the brand side)
A clean direct `User.brand` ForeignKey is blocked by a Django architectural constraint: the migration autodetector cannot see fields attached to `auth.User` from another app's `models.py` (the only ways to make it visible are a custom User model, `User.add_to_class` at runtime — which is invisible to migrations — or hand-edited schema operations, all of which break the "autodetector only" rule for non-trivial reasons). To keep the schema fully auto-generated AND keep the `user.brand` API intact, the link lives on a separate `Membership` model (`OneToOneField(User, on_delete=CASCADE, related_name="membership")` + `ForeignKey(Brand, on_delete=PROTECT, related_name="memberships")`), and `User.brand` is a settable property that reads/writes through the membership row. `PROTECT` on `Membership.brand` preserves the original intent: deleting a brand with users raises `ProtectedError` rather than cascading through to user rows.

**Alternatives considered**
- Direct `User.brand` ForeignKey with `null=True` permanently. Rejected — the spec requires the link to be required; weakening the DB constraint leaves a foot-gun.
- Direct `User.brand` ForeignKey with `null=False` enforced by app code only. Rejected — same foot-gun, just moved up a layer.
- `User.add_to_class("brand", ForeignKey(...))` at import time. Rejected — invisible to the migration framework, breaks `makemigrations` consistency checks.
- Hand-edited schema `RunPython` migration adding the column. Rejected — violates the "autodetector only" rule.
- Custom `AUTH_USER_MODEL`. Rejected — too invasive for this change.

### Decision 3: A system default brand always exists ("Default Brand")
Superuser and any user without an explicit assignment need to satisfy the required FK. A `DEFAULT_BRAND_PK = 1` (or relied-upon by name "Default Brand") is created by the migration and used as fallback by `BrandAdmin` logic and `Brand.get_or_create_default()`. Migration also assigns all currently existing users with no profile to this default brand.

**Alternatives considered**
- Make superuser exempt from the FK. Rejected by user — every user must belong.

### Decision 4: File move and data back-fill via a management command, not a hand-edited migration
Avatar files currently live at `media/avatars/user_<id>/<file>`. Since the field is renamed `logo` and lives on `Brand`, files need to relocate to `media/brands/brand_<pk>/<file>`. A Django management command `core/management/commands/seed_brands.py` performs the rename via `os.rename` / `shutil.move` rooted at `settings.MEDIA_ROOT`, and also handles the data back-fill (Default Brand creation, legacy user→brand assignment, blank-brand fallback). The command is idempotent and supports `--reverse` (best-effort file restore, tolerating missing sources). The schema migrations themselves are produced **only** by `makemigrations core` and are never hand-edited, satisfying the "no hand-edited migrations" requirement.

**Alternatives considered**
- Hand-written `RunPython` inside a migration. Rejected — violates the "edit codebase, autogenerate migrations" rule and the user explicitly forbade hand-edited migrations.
- Keep old `upload_to` paths referencing `avatars/user_<id>` even after rename. Stops working once the FK is reversed (no `user_id` on `Brand`). Rejected.
- Use a `post_migrate` signal. Rejected — signals inside migrations re-introduce hidden side-effects; the management-command approach is explicit, testable, and runnable on demand.

### Decision 5: Bottom-left avatar removed via template override only
Override `unfold/helpers/navigation_user.html` by placing a copy under `project/templates/unfold/helpers/navigation_user.html`. Django's `APP_DIRS` template loaders will find this before the unfold-packaged copy if `project` (or its template `DIRS`) precedes unfold in template search order. The override removes the `{% with avatar_url=request.user.avatar_url %}…background-image…` branch and always renders the `person` material icon.

No Python change. `User.avatar_url` is *also* being removed in change B (callbacks now read `user.brand.logo.url` directly, no replacement property is introduced at the `User` level), which is safe because the bottom-left no longer consumes it and the top-left consumes `user.brand.logo.url` directly via `site_icon`.

**Alternatives considered**
- Remove the `User.avatar_url` property without overriding the template. Rejected — top-left `site_icon` reads the same property; this would also break the brand logo.
- Fork Unfold. Rejected — template override is sufficient.

### Decision 6: Superuser-only brand assignment via `UserAdmin` form gating
`UserAdmin.get_readonly_fields(request, obj=None)` returns `("brand",)` when `not request.user.is_superuser`; on add/change, non-superusers cannot set or change `brand`. The `brand` field lives in a dedicated fieldset (e.g., "Brand"). Brand creation/edition (in `BrandAdmin`) is restricted to superusers via `has_add_permission`/`has_change_permission`/`has_delete_permission` overrides.

**Alternatives considered**
- Django object-level permissions / guardian. Rejected — overkill for a single FK gate.

### Decision 7: Callbacks read `user.brand` with safe fallback
`site_icon`/`primary_palette_css` already tolerate missing profiles gracefully. After the change they read `getattr(user, "brand", None)`; when `brand is None` they fall back to the favicon / no palette CSS, identical to today's "no profile" path. This preserves the historical resilience during the brief window before assignment.

## Risks / Trade-offs

- **Risk: Template lookup order** — `project/templates` may not precede unfold's packaged templates. → Mitigation: verify `settings.TEMPLATES[0]["DIRS"]` includes the project templates path, or that `project` app appears before `unfold` in `INSTALLED_APPS`. Add a one-line test asserting the override path resolved first.
- **Risk: Reverse back-fill command's file moves fail** if files already deleted. → Mitigation: wrap `shutil.move` in `try/except FileNotFoundError` and treat as no-op; document this in the `seed_brands` command's docstring and `--reverse` help text.
- **Risk: Existing tests reference `Profile`/`avatar_url`**. → Mitigation: update `core/tests.py` as part of the change; add tests covering `Brand` FK back-fill, `site_icon`/`primary_palette_css` reading from brand, template override presence, and superuser-only gate.
- **Trade-off: Required brand FK makes future "global admin with no brand" awkward.** → Accepted; mitigate with the system default brand.
- **Trade-off: `PROTECT` blocks brand deletion when it has users.** → Acceptable; admin UX should hide delete button (Unfold already shows delete only when permitted) — relying on Django's protected-error message for now.
- **Risk: Renaming `avatar` field loses any external URL references to `media/avatars/...`.** → Mitigation: bookmarks/links are fine to 404 from old paths; document the file-move in release notes.
- **Risk: Concurrent user creation during deploy before migration applied.** → Mitigation: deploy migration atomically before any code referencing `Brand` is active; signals `create_profile_for_new_user` removed in the same change/commit so no orphan Profiles are created mid-flight.

## Migration Plan

The migration plan separates **schema** (autodetected, never hand-edited) from **data + files** (a one-shot management command). No hand-edited migration files.

1. **Branch + commits**: implement change in a feature branch.
2. **Codebase edits only** (no migration hand-edits):
   - `core/models.py` — rename `Profile`→`Brand`, rename `avatar`→`logo`, add `Membership` (`OneToOneField(User)` + `ForeignKey(Brand, PROTECT)`) with `User.brand` exposed as a settable property, remove `User.avatar_url`.
   - `core/signals.py` — remove `create_profile_for_new_user`.
   - `core/admin.py` — `ProfileAdmin`→`BrandAdmin`; superuser-only `UserAdmin.brand`; `save_model` assigns Default Brand on user-create when missing.
   - `utils/callbacks.py` — read from `user.brand`.
   - `core/templates/...` — bottom-left avatar override.
   - `core/management/commands/seed_brands.py` — new command (see below).
3. **Generate schema migration (autodetector only)**:
   - `python manage.py makemigrations core` → emits `RenameModel`, `RenameField`, `RemoveField` (OneToOne), `AddField(User.brand, null=True)`. Commit the file as-is.
4. **Apply on staging**: `python manage.py migrate core`.
5. **Run back-fill command**: `python manage.py seed_brands`.
   - Get-or-create `Brand(name="Default Brand", primary_color="#C92FFF")`.
   - For each `Brand` row, look up its previously-linked user (via the OneToOne that the auto-migration removed only after this step, OR via a preserved `legacy_user_id` column if introduced) and set `User.brand`.
   - Assign users without a brand → Default Brand.
   - Move image files `MEDIA_ROOT/avatars/user_<id>/<filename>` → `MEDIA_ROOT/brands/brand_<pk>/<filename>`; update `Brand.logo.name`.
6. **Generate follow-up migration**: `python manage.py makemigrations core` again → autodetector emits `AlterField(User.brand, null=False)`. Commit as-is. (Safe because every row now has a brand.)
7. **Apply**: `python manage.py migrate core`.
8. **Re-test admin chrome** (top-left brand logo, primary color palette, bottom-left person icon, superuser-only brand select).
9. **Rollback**:
   - `python manage.py migrate core <previous>` reverts the schema (reverses `AlterField`, drops the FK, restores the OneToOne and `Profile` model).
   - `./manage.py seed_brands --reverse` moves files back best-effort.
   - Manual revert of code commits if the rollback is a full revert.

## Open Questions

- None outstanding — confirmations during exploration were:
  - Model rename: `Brand` (chosen over `Company`, `Profile`).
  - Assignment perms: **superusers only**.
  - Migration: **one brand per existing profile**, plus a default brand for users without one.
  - Required FK: every user must belong to a brand (_nullable=False_).
- Verified defaults recorded in this design:
  - `on_delete=PROTECT`.
  - System default brand `"Default Brand"` always exists.
  - File move performed as RunPython inside the migration.