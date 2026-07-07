## Context

The `ourlives` app currently exists as an empty skeleton (stub models.py, admin.py, views.py, tests.py) and is not registered in INSTALLED_APPS. We need to add three models, admin integration, token pool validation, and DB-level constraints. The token pool is managed via django-solo (already installed but unused). An external service consumes codes by incrementing `current_use` directly in the database.

## Goals / Non-Goals

**Goals:**
- Project CRUD: name (unique), description (textarea), `__str__` = name, verbose_name/plural
- InvitationCode CRUD: FK to Project, auto-generated code (editable via override), is_active, max_use (with help_text), current_use (read-only in admin, with help_text), `__str__` = code, verbose_name/plural
- AppSettings singleton: total_tokens (editable, with help_text), computed status (assigned, used, available), `__str__` = "App Settings", verbose_name
- Token pool validation: `SUM(max_use)` of all codes must never exceed `total_tokens`
- DB-level check constraint: `current_use <= max_use` (guard against external service overflow)
- Race condition prevention via row-level lock on AppSettings during save
- All models registered in admin with django-unfold, inheriting `ModelAdminUnfoldBase`
- Each admin: `sidebar_icon`, `list_display_links`, custom `@admin.display` methods for computed fields
- Validation errors surfaced clearly in admin forms

**Non-Goals:**
- No REST API endpoints (will be added later if needed)
- No user registration flow (external service handles consumption)
- No audit trail for code deletion (handled by admin permissions)
- No email notifications, expiry dates, or batch operations
- No signals or webhooks

## Decisions

### Decision 1: django-solo for singleton (not manual `is_default` pattern)

**Choice:** Use `solo.models.SingletonModel` for `AppSettings`.

**Alternatives considered:**
- Manual singleton (Brand's `is_default` pattern): Works but requires custom `save()` overrides and admin hacks.
- Generic singleton app: Overkill for one singleton.

**Rationale:** `django-solo` is already installed in the project but unused. It provides `get_solo()` (idempotent get-or-create), `SingletonModelAdmin` (auto-hides add/delete buttons), and is well-tested. Follows the principle of using existing dependencies.

### Decision 2: Computed properties on AppSettings (not denormalized columns)

**Choice:** `tokens_assigned`, `tokens_used`, `tokens_available` as `@property` methods that run `SUM` queries.

**Alternatives considered:**
- Denormalized columns updated via signals: Faster reads but risk of drift and complexity.
- Materialized view: Overkill for admin-only access.

**Rationale:** Data volumes are small (hundreds of codes, not millions). Aggregation queries are fast. Computed properties are always consistent, cannot drift, and require no sync machinery.

### Decision 3: Validation in `save()` + `full_clean()` with `select_for_update()`

**Choice:** Lock the AppSettings row inside a transaction before computing the token sum. Validate in `save()` (always fires) and call `full_clean()` from `save()` (admin-friendly errors).

**Alternatives considered:**
- `clean()` only: Misses direct ORM saves (`.update()`, `.bulk_create()`).
- Optimistic locking: Retry logic adds complexity with no practical benefit for admin-only access.
- DB trigger: Harder to maintain, non-Django-idiomatic.

**Rationale:** Race conditions are possible (two admins saving simultaneously). A row-level lock on AppSettings serializes all code creation/update, making the check-and-save atomic. Django's `select_for_update()` is the standard approach.

### Decision 4: `CheckConstraint` for `current_use <= max_use` at DB level

**Choice:** Add `models.CheckConstraint(current_use__lte=models.F('max_use'))`.

**Rationale:** The external service updates `current_use` directly in the DB, bypassing Django validation. A DB-level constraint is the only guaranteed enforcement point. Django 5.2 supports `F()` references in constraints.

### Decision 5: Code auto-generated via `default` callable on the field

**Choice:** `code = models.CharField(..., default=uuid_hex_callable)`.

**Alternatives considered:**
- Auto-generate in admin only (`get_form()` override): Works but doesn't handle direct model creation.
- Post-generate UUID on first save: More complex, harder to test.

**Rationale:** A `default` callable on the model field auto-populates everywhere (admin shell scripts, fixtures) and can be overridden manually. Simple Django pattern.

### Decision 6: Model order in models.py to avoid circular imports

**Choice:** Define in order: Project → InvitationCode → AppSettings. Use inline imports for cross-references in methods.

**Rationale:** `InvitationCode.save()` references `AppSettings` (defined later) — handled by deferred import inside the method body. `AppSettings` properties reference `InvitationCode` (defined earlier) — no issue since Python resolves properties at call time.

### Decision 7: Admin registration patterns (unfold best practices)

**Choice:** Follow existing core/admin.py conventions: override `sidebar_icon` per admin (material icon names), set `list_display_links` to primary name field, use `@admin.display(description="...")` for custom list columns and readonly display methods.

**Rationale:** The `ModelAdminUnfoldBase` base class provides defaults (`sidebar_icon="database"`, `compressed_fields=True`, `warn_unsaved_form=True`, `list_filter_sheet=False`, `change_form_show_cancel_button=True`). Each admin overrides only what differs. `InvitationCodeAdmin` adds `usage_percentage` with `@admin.display`. `AppSettingsAdmin` uses `SingletonModelAdmin` (hides add/delete automatically) and provides computed status fields via readonly display methods.

## Risks / Trade-offs

| Risk | Mitigation |
|------|-----------|
| Race condition (TOCTOU) on token pool | `select_for_update()` lock on AppSettings row inside a transaction |
| External service exceeds `current_use > max_use` | DB-level `CheckConstraint` prevents the write |
| `select_for_update()` on fresh singleton | `get_solo()` creates row first, then re-fetch with lock |
| ValidationError in `save()` vs admin UX | Call `full_clean()` at start of `save()` so admin form shows field errors |
| Admin reduces `total_tokens` below current `assigned` | Allow the save — new code creation is blocked until pool grows; no data loss |
| Admin reduces `max_use` below `current_use` | Reject with `ValidationError` — prevent data integrity violation |
