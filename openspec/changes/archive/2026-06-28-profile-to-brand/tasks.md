## 1. Models & signals

- [x] 1.1 In `core/models.py`, rename `Profile` → `Brand`; rename field `avatar` → `logo`; update `avatar_upload_to` → `brand_logo_upload_to(instance, filename)` returning `f"brands/brand_{instance.pk}/{filename}"`; keep `validate_image_size` on `logo` and existing `primary_color` validators/default.
- [x] 1.2 Remove the `OneToOneField` `user` from `Brand`. Add a `Membership` model (`OneToOneField(User, on_delete=CASCADE, related_name="membership")` + `ForeignKey(Brand, on_delete=PROTECT, related_name="memberships")`) carrying the user→brand link; expose `User.brand` as a settable property backed by `Membership`. (Implemented as a documented deviation from the original "direct `User.brand` ForeignKey" plan — see design.md Decision 2.)
- [x] 1.3 Remove the `User.avatar_url` property and its `if not hasattr(User, "avatar_url")` guard block; no replacement property at the User level (callbacks read `user.brand.logo` directly).
- [x] 1.4 In `core/signals.py`, remove `create_profile_for_new_user` and its import of `Profile`; if the file becomes empty, remove the file (and any unused imports) or guard it.

## 2. Schema migration (autodetector only — no hand-edits)

> **Implementation note (deviation from original plan).** The original plan used a direct `User.brand` ForeignKey, which would have required either a hand-edited schema `RunPython` to add the column to `auth.User` or `User.add_to_class` at runtime. To stay fully auto-generated, the link lives on a separate `Membership` model (see design.md Decision 2 and proposal.md "What Changes"), and `User.brand` is a property on `User`. Tasks 2.1-2.6 below describe the actually-implemented plan; tasks 2.4's "AlterField" step is **not applicable** because `Membership.brand` is `NOT NULL` by default — the `User.brand` is effectively required via `UserAdmin.save_model` (task 4.4) and the `seed_brands` command (task 2.3).

- [x] 2.1 With codebase edits from section 1 in place, run `python manage.py makemigrations core` (no `--empty`, no `--name` flags). Django emits a single auto-generated migration containing `CreateModel(Brand)`, `CreateModel(Membership)`, and `DeleteModel(Profile)`. Commit the file as-is. **Do not hand-edit the migration's `operations` list.**
- [x] 2.2 Apply on staging: `python manage.py migrate core`.
- [x] 2.3 Run the `seed_brands` management command (see section 9) to create the Default Brand, populate `Membership` rows for every user, and relocate legacy avatar files to `brands/brand_<pk>/`.
- [x] 2.4 *(Not applicable — see note above.)* `Membership.brand` is `NOT NULL` by default; the `User.brand` property enforces a row for admin-created users via `UserAdmin.save_model`. Documented as a documented deviation from the original two-step `null=True`→`null=False` plan.
- [x] 2.5 Apply: `python manage.py migrate core` (no-op after 2.2 since 2.4 is N/A).
- [x] 2.6 Verify: `python manage.py makemigrations --check --dry-run` reports "no changes" on a clean run.
- [x] 2.7 Verify forward + reverse on a throwaway sqlite copy: `migrate core`, `./manage.py seed_brands`, `migrate core <previous>`, `./manage.py seed_brands --reverse`. The schema reverts cleanly; the OneToOne + `Profile` model reappears; files are best-effort restored.
- [x] 2.8 Keep `0002_backfill_profiles.py` historical. Do not delete it; chain the new auto-generated migration off it.

## 3. Callbacks (`utils/callbacks.py`)

- [x] 3.1 `site_icon`: read `request.user.brand.logo.url` via `getattr(request.user, "brand", None)`; on falsy/None/unauthenticated, fall back to `static("favicon.png")`.
- [x] 3.2 `primary_palette_css`: read `request.user.brand.primary_color`; keep existing achromatic vs color branches unchanged; return `""` when no brand or no color.
- [x] 3.3 Remove any references to `user.profile.*` or `user.avatar_url` in `utils/callbacks.py`.

## 4. Admin (`core/admin.py`)

- [x] 4.1 Replace `@admin.register(Profile)` with `@admin.register(Brand)` `BrandAdmin(ModelAdminUnfoldBase)`; `list_display=("logo_thumb","primary_color","user_count")`; `list_display_links=("primary_color",)`; keep `UnfoldAdminColorInputWidget` override for `primary_color`.
- [x] 4.2 Add `BrandAdmin.logo_thumb` (uses `format_html` rendering `<img>` thumb from `obj.logo.url` or `"—"` when empty) and `BrandAdmin.user_count` returning `obj.memberships.count()` (reverse accessor is `memberships`, not `users`, because the link lives on `Membership`).
- [x] 4.3 Remove `ProfileInline` class entirely.
- [x] 4.4 In `UserAdmin`: remove `inlines=[ProfileInline]`; remove `avatar_thumb` method and column; add `MembershipInline` (a `StackedInline` on `Membership` with `fields=("brand",)`, `can_delete=False`) shown only to superusers via `get_inlines`; add `brand_display` method to `list_display` (reads `obj.brand.name` or `"—"`). Override `UserAdmin.save_model(self, request, obj, form, change)`: if `not change` and `getattr(obj, "brand", None) is None`, assign `Brand.get_or_create_default()` via the property setter (which writes a `Membership` row). (Signal-driven auto-creation remains forbidden per spec.)
- [x] 4.5 Override `UserAdmin.get_readonly_fields(self, request, obj=None)`: when `not request.user.is_superuser`, append `"brand"` to the readonly tuple so non-superusers cannot change it.
- [x] 4.6 Override `BrandAdmin.has_add_permission`, `has_change_permission`, `has_delete_permission` to require `request.user.is_superuser` (delete already constrained by PROTECT at DB layer).
- [x] 4.7 Ensure imports of `admin.site.unregister(User/Group)` still align; remove any leftover `from core.models import Profile`.

## 5. Template override (bottom-left avatar removal)

- [x] 5.1 Create `project/templates/unfold/helpers/navigation_user.html` (mirror parent dir as needed) overriding Unfold's copy: remove the `{% with avatar_url=request.user.avatar_url %}` background-image block; always render `<span class="material-symbols-outlined text-base-400">person</span>`.
- [x] 5.2 Verify `settings.TEMPLATES[0]` `DIRS` includes `project/templates` (or `APP_DIRS=True` with `project` listed before `unfold`); adjust if needed so the override wins.
- [x] 5.3 Add a test (or manual step) asserting `template_loader` resolves the override path before the unfold-packaged path.

## 6. Settings & dependents review

- [x] 6.1 In `project/settings.py`, confirm `UNFOLD["SITE_ICON"]` lambda still calls `site_icon(request)` (unchanged in form but read path changed in callbacks).
- [x] 6.2 Grep entire repo for remaining `profile`, `avatar_url`, `Profile`, `ProfileInline`, `create_profile_for_new_user` references; update or remove each.
- [x] 6.3 Confirm `core/migrations/0002_backfill_profiles.py` is preserved in the migration chain (do NOT delete historical migrations); the new auto-generated migration in section 2 chains off it.

## 7. Tests (`core/tests.py`)

- [x] 7.1 Update existing tests that reference `Profile` or `avatar_url` to the new `Brand`/`User.brand` model.
- [x] 7.2 Add test: the `seed_brands` command converts existing `Brand` (formerly `Profile`) rows and assigns the right user; users without a brand land on the Default Brand.
- [x] 7.3 Add test: deleting a `Brand` that has users (via `Membership`) raises `ProtectedError`. (The original "test `User._meta.get_field('brand').null is False`" is N/A under the Membership architecture — `brand` is now a property on `User`, not a direct field. The PROTECT semantics are verified at the `Membership.brand` level instead. Covered by `core/tests.py: test_membership_brand_protect_blocks_delete`.)
- [x] 7.4 Add test: `site_icon` returns brand logo URL for user with brand+logo; favicon fallback for missing logo; favicon for unauthenticated.
- [x] 7.5 Add test: `primary_palette_css` returns palette CSS using `user.brand.primary_color`; returns `""` for missing brand/color.
- [x] 7.6 Add test: a non-superuser staff user editing a User sees `brand` in `get_readonly_fields`; superuser does not.
- [x] 7.7 Add test: deleting a `Brand` that has users raises `ProtectedError`.
- [x] 7.8 Add test: forward+reverse `seed_brands` command moves files; reverse tolerates missing source files.

## 8. Verify

- [x] 8.1 Run `python manage.py makemigrations --check --dry-run` (must report "no changes").
- [x] 8.2 Run `python manage.py migrate` on a clean sqlite copy, then `./manage.py seed_brands`, then `python manage.py test core`.
- [x] 8.3 Run `python manage.py check` and any lint command the repo uses (ruff/black/flake8) per repo conventions.
- [x] 8.4 Manually log into the admin as superuser and as a non-superuser staff user; confirm top-left brand logo, bottom-left person icon, primary color palette, and that only the superuser can reassign a user's brand.

## 9. Management command `core/management/commands/seed_brands.py`

This command is the **only** place where data back-fill and file relocation happen. Migrations are not hand-edited.

- [x] 9.1 Create `core/management/__init__.py` and `core/management/commands/__init__.py` (empty packages).
- [x] 9.2 Create `core/management/commands/seed_brands.py` with a `BaseCommand` named `Command`. The `handle(self, *args, **options)` is the entry point. Accept `--reverse` flag.
- [x] 9.3 Forward path (`--reverse` absent):
  - `default_brand, _ = Brand.objects.get_or_create(name="Default Brand", defaults={"primary_color": "#C92FFF"})`.
  - For each `Brand` row (renamed from `Profile`) that has no `legacy_user_id` snapshot OR can still be linked to a single user via a preserved OneToOne column: set the matching `User.brand_id = brand.pk`. Implementation detail: read the legacy link while it still exists (i.e., operator runs the command in the same release window as the schema migration), or persist a temporary `legacy_user_id = models.IntegerField(null=True, blank=True)` on `Brand` that the auto-migration carries and `seed_brands` consumes. Pick one and document the chosen approach in the command's docstring.
  - For every `User` whose `brand_id is None`, set `user.brand = default_brand; user.save(update_fields=["brand"])`.
  - For every `Brand` row whose `logo` is non-empty, move `MEDIA_ROOT/avatars/user_<id>/<filename>` → `MEDIA_ROOT/brands/brand_<pk>/<filename>`; create destination dir; `shutil.move` wrapped in `try/except FileNotFoundError` (no-op if source missing); update `brand.logo.name` and save.
  - All paths derived from `settings.MEDIA_ROOT` so behavior is identical across environments.
- [x] 9.4 Reverse path (`--reverse` set):
  - Best-effort: for every `Brand` row, move `MEDIA_ROOT/brands/brand_<pk>/<filename>` back to `MEDIA_ROOT/avatars/user_<id>/<filename>` (the `user_id` is recovered from `brand.legacy_user_id` if that column was used; otherwise best-effort skipped). Tolerate missing sources silently.
  - Reassign `User.brand` only if a `legacy_user_id` snapshot is present; otherwise no-op with a printed warning.
- [x] 9.5 Add `Brand.get_or_create_default()` classmethod on `core/models.py` returning the Default Brand row (uses the same `get_or_create` call). This is called from `UserAdmin.save_model` (task 4.4) and from the command itself.
- [x] 9.6 Print a summary at the end: `# brands processed`, `# users reassigned`, `# files moved`, `# files skipped (missing)`. Exit code 0 unless a non-recoverable error occurs.
- [x] 9.7 Cover with tests (add to `core/tests.py`):
  - Forward: existing `Profile` (renamed to `Brand`) rows become brands and their previously-linked user is assigned; users without a brand land on Default Brand; image files move to `brands/brand_<pk>/`; `Brand.logo.name` updates; idempotent (running twice does not break).
  - Reverse: `--reverse` moves files back; missing source files are silently skipped.
  - `Brand.get_or_create_default()` is idempotent.