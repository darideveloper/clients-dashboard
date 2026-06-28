## Why

The admin currently personalizes branding (logo + primary color) on a *per-user* basis via a 1:1 `Profile` model. Real-world usage is multi-tenant: one company needs the same branding applied to all of its employees, not a separate profile per user. At the same time, the personal profile picture shown in the bottom-left user menu is unused and visually redundant — only the company brand in the top-left header matters.

## What Changes

### Change A — Remove bottom-left personal avatar in user menu
- Override `unfold/helpers/navigation_user.html` to always render the default `person` material icon, dropping the `request.user.avatar_url` background-image block.
- `User.avatar_url` is no longer consumed anywhere (the template no longer references it; `site_icon` reads `user.brand.logo.url` directly instead).

### Change B — Replace per-user `Profile` with a one-to-many `Brand` **BREAKING**
- Create new `Brand` model representing a company/tenant (fields: `name`, `logo`, `primary_color`). Delete the old `Profile` model. The schema migration emits `CreateModel(Brand)`, `CreateModel(Membership)`, `DeleteModel(Profile)` — no renames.
- Field `Profile.avatar` is recreated as `Brand.logo` with the same upload validators but a new storage path (`brands/brand_<pk>/`).
- The `User ↔ Profile` OneToOne is removed; the user→brand link is re-homed onto a new `Membership` model (`OneToOneField(User, on_delete=CASCADE, related_name="membership")` + `ForeignKey(Brand, on_delete=PROTECT, related_name="memberships")`). This design is required because Django's migration autodetector cannot see fields added to `auth.User` from another app's `models.py`.
- `User.brand` is exposed as a settable property on `User` that reads/writes through the membership row. The public API (`user.brand`) is preserved. The reverse accessor is `brand.memberships` (not `brand.users`); use `brand.memberships.count()` to get user count.
- `Membership.brand` FK uses `on_delete=PROTECT` so a brand with users cannot be accidentally deleted.
- A system default brand ("Default Brand") always exists so that superusers and any user without an explicit assignment still satisfy the link.
- `site_icon` and `primary_palette_css` callbacks are repointed from `user.profile.*` to `user.brand.*`.
- Remove the `post_save` signal that auto-created a `Profile` per new user (brands are created/assigned by superusers via admin, not per user).
- Admin changes:
  - `ProfileAdmin` → `BrandAdmin` (list/edit brand; show logo thumb, primary color, user count via `memberships.count()`).
  - `BrandAdmin` restricts add/change/delete to `is_superuser`.
  - Remove `ProfileInline` from `UserAdmin`.
  - Add `MembershipInline` (fields: brand selector) shown **only to superusers** via `get_inlines` — non-superusers see no brand selector at all.
  - `UserAdmin.save_model` assigns the Default Brand to newly created users that have no brand set.
  - Replace the `avatar_thumb` list-display column on `UserAdmin` with a `brand_display` column (shows `brand.name` or `"—"`).

### Data back-fill (one-shot, not a hand-edited migration)
- A Django management command `core/management/commands/seed_brands.py` performs the data and file back-fill **outside** of the migration system. Operator runs it once after the auto-generated schema migration applies.
- Command responsibilities (idempotent, tolerant of missing files):
  - Get-or-create `Brand(name="Default Brand", primary_color="#C92FFF")`.
  - For every user without a `Membership` row, assign them to the Default Brand via the property setter.
  - For each `Brand` row whose `logo` points at the legacy `avatars/` path, move the file to `brands/brand_<pk>/` and update `Brand.logo.name`. Missing source files are silently skipped.
  - The user→brand link is recovered naturally because `Membership` rows are already created by the schema migration (the `Membership` model exists in the auto-generated migration). No `legacy_user_id` column is needed.
- Schema changes (`CreateModel(Brand)`, `CreateModel(Membership)`, `DeleteModel(Profile)`) are produced **only** by `python manage.py makemigrations core`. The resulting migration file is committed as-is — it is never hand-edited.

## Capabilities

### New Capabilities
- `brand-management`: CR(U/D) for `Brand` entities (logo + primary_color), assignment of users to a brand by superusers, and exposure of the active brand's logo/color to the admin chrome (top-left site icon + primary palette).

### Modified Capabilities
- `user-profile` — **fully superseded and retired** by `brand-management`. Every requirement in `openspec/specs/user-profile/spec.md` is removed: `Profile` model (1:1 with `User`), `User.avatar_url` property, the `post_save` auto-creation signal, `ProfileInline`, `avatar_thumb` changelist column, the `site_icon` "viewer" behavior, and the backfill data migration. Their successors live in `brand-management` (with the 2 MB logo upload cap and the storage-backend behavior restated there so the new capability is self-contained).
- `per-user-primary-color` — **fully superseded and retired** by `brand-management`. The `Profile.primary_color` field is reparented onto `Brand`; the per-user palette injection becomes per-brand. Both replacements live in `brand-management`.

Formal spec deltas (REMOVED Requirements) are provided at:
- `openspec/changes/profile-to-brand/specs/user-profile/spec.md`
- `openspec/changes/profile-to-brand/specs/per-user-primary-color/spec.md`

## Impact

- **Code**:
  - `core/models.py` — create `Brand` (name, logo, primary_color) + `Membership` (OneToOne→User, FK→Brand PROTECT); add `User.brand` settable property; delete `Profile` model; remove `User.avatar_url` property.
  - `core/signals.py` — remove `create_profile_for_new_user`.
  - `core/admin.py` — `ProfileAdmin`→`BrandAdmin` (superuser-gated CRUD, logo_thumb, user_count); add `MembershipInline` in `UserAdmin` (superuser-only via `get_inlines`); `brand_display` column replaces `avatar_thumb`; `save_model` assigns Default Brand on user-create.
  - `core/validators.py` — unchanged (image size + color contrast still apply to brand logo/color).
  - `utils/callbacks.py` — `site_icon` and `primary_palette_css` read from `user.brand` instead of `user.profile`.
  - `project/settings.py` — `UNFOLD["SITE_ICON"]` callback path unchanged in reference but behavior shifts (reads brand logo).
  - `project/templates/unfold/helpers/navigation_user.html` — new override rendering `person` icon.
- **Migrations**: one auto-generated migration (`makemigrations core`, **not hand-edited**) that performs `CreateModel(Brand)`, `CreateModel(Membership)`, and `DeleteModel(Profile)`. Historical migrations (including `0002_backfill_profiles.py`) are preserved and not deleted. No `AlterField` step needed because `User.brand` is a property backed by `Membership.brand` (which is `NOT NULL` by default), not a direct FK on `User`.
- **Management command**: `core/management/commands/seed_brands.py` (codebase, not a migration) handles all data back-fill and file relocation. Idempotent; supports `--reverse`.
- **Templates**: depends on Django's `APP_DIRS` discovering the project's `templates/unfold/helpers/` before unfold's packaged templates; verify TEMPLATES `DIRS`/order.
- **Dependencies**: none new.
- **Risk**: schema replacement (delete Profile, create Brand + Membership) is breaking; lossy if any user-defined migration is skipped. Brand deletion guarded by `PROTECT` on `Membership.brand`.
- **Tests**: existing tests (`core/tests.py`) referencing `Profile`/`avatar_url` must be updated.