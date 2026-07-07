## Context

The `InvitationCode.save()` method currently validates business rules (token pool limits, max_use vs current_use) inside a `transaction.atomic()` block with `SELECT FOR UPDATE` locking. It raises `ValidationError` on failure. Django's admin form validation pipeline only catches `ValidationError` from `Model.clean()` / form validation, not from `Model.save()`. This causes a Django debug error page (`ValidationError at /admin/...`) instead of a user-friendly form error.

The validation must run at two levels: a fast, lock-free check for instant user feedback (form-level), and a locked check for data integrity (save-level).

Previous implementation (from `invitation-code-system` change):
- `InvitationCode.save()` at `ourlives/models.py:62-94`
- `InvitationCodeAdmin` at `ourlives/admin.py:17-30`
- `AppSettings` singleton model at `ourlives/models.py:97-123`

## Goals / Non-Goals

**Goals:**
- Show token pool and business rule violations as inline form errors in Django admin, not debug error pages
- Retain race-condition safety via `SELECT FOR UPDATE` lock in `save()`
- Gracefully handle the rare case where validation passes in `clean()` but fails in `save()` under lock
- Prevent reducing `AppSettings.total_tokens` below `tokens_assigned`
- Existing tests must continue to pass (adjusting for new error location where needed)

**Non-Goals:**
- Changing how `current_use` is incremented (handled externally)
- Adding programmatic API endpoints for invitation code management (admin-only fix)
- Token deallocation on code deletion (existing behavior, no change)
- Changing the database schema or adding new models

## Decisions

### Decision 1: Three-layer validation architecture

```
┌─────────────────────────────────────────────────┐
│ LAYER 1: clean() — Fast, lock-free              │
│ ├─ Token pool check (no SELECT FOR UPDATE)      │
│ ├─ max_use < current_use check                  │
│ └─ Raises ValidationError → INLINE FORM ERROR   │
│     (Catches ~99% of cases instantly)            │
├─────────────────────────────────────────────────┤
│ LAYER 2: save() — Locked safety net             │
│ ├─ SELECT FOR UPDATE lock on AppSettings        │
│ ├─ Same checks repeated under lock              │
│ └─ Raises ValidationError → LAYER 3 catches     │
│     (Handles concurrent admin race condition)    │
├─────────────────────────────────────────────────┤
│ LAYER 3: Admin save_model() — Graceful fallback │
│ ├─ Try/except ValidationError                   │
│ └─ messages.error() → BANNER MESSAGE            │
│     (Last resort — user still informed)          │
└─────────────────────────────────────────────────┘
```

**Rationale**: Pure clean() approach (Option A) loses lock safety. Pure admin catch approach (Option B) loses inline form errors. The hybrid gives both.

**Alternatives considered**:
- **A: Clean() only** — Lose race condition protection. Rejected for data integrity.
- **B: Admin catch only** — Banner messages are worse UX than inline form errors. Rejected.
- **D: Override admin view to inject form errors** — Very complex, brittle against Django internals. Rejected for maintainability.

### Decision 2: What goes in clean() vs save()

Both checks (token pool AND max_use constraints) go in both places:
- `clean()` runs first, lock-free, for instant feedback
- `save()` repeats the checks under lock, as a safety net

The checks in `save()` are redundant in the common case but essential for race conditions. Code duplication is minimal (~10 lines duplicated) and both methods operate on the same business logic, just at different locking levels.

**Important detail for `clean()`'s max_use < current_use check**: Must fetch the old `current_use` from the database (`InvitationCode.objects.get(pk=self.pk).current_use`), not use `self.current_use`. The instance attribute `self.current_use` reflects the value at load time, which may be stale if an external service incremented uses concurrently. Using the DB value ensures the check is correct even under concurrent writes. The `save()` method under lock already does this correctly.

**Error placement**: Both checks in `clean()` should raise `ValidationError({"max_use": "..."})` (field-specific dict format). This makes the error appear inline on the `max_use` field in admin, rather than as a non-field form error at the top of the page. The `save()` method's raises stay as plain `ValidationError("...")` since those are caught by the admin fallback handler and displayed as a banner message — field specificity doesn't apply there.

### Decision 3: Move full_clean() call before transaction block

Currently `full_clean(exclude={"current_use"})` is called at the top of `save()` (line 65) but before the transaction block. This is correct — validation should happen before we acquire the lock. No change needed here.

### Decision 4: AppSettings total_tokens guard

Currently, reducing `total_tokens` below `tokens_assigned` is allowed, creating a state where:
- No new codes can be created (pool exhausted)
- But existing over-assigned codes remain
- The admin has no warning this happened

Adding a `clean()` to `AppSettings` that rejects `total_tokens < tokens_assigned` prevents this invalid state.

### Decision 5: Admin save_model override structure

```python
def save_model(self, request, obj, form, change):
    try:
        super().save_model(request, obj, form, change)
    except ValidationError as e:
        self.message_user(request, str(e), messages.ERROR)
```

This catches the rare lock-level failure. The form still redirects, but the user sees a red banner with the error text. The object is not created/updated.

## Risks / Trade-offs

- **[Concurrent admin race]**: Two admins submit forms simultaneously, both pass `clean()`, one fails in `save()`. → **Mitigation**: Second admin sees a banner message. In practice, Django admin concurrency is extremely rare.
- **[Duplicated validation logic]**: Token pool and max_use checks exist in both `clean()` and `save()`. → **Mitigation**: Only ~10 lines duplicated. `clean()` for UX, `save()` for integrity. Acceptable for a focused model.
- **[Message-based error UX]**: If Layer 3 fires, the error is a banner, not inline. → **Mitigation**: Layer 3 is a last resort. Layer 1 catches the vast majority of cases. Banner is still better than debug error page.
- **[Existing tests may break]**: Tests assert `ValidationError` on `save()`. Now `ValidationError` may come from `clean()` instead. → **Mitigation**: Test assertions should still pass since `clean()` is called from `save()` via `full_clean()`. Minor adjustments if any tests bypass `full_clean()`.
- **[AppSettings `.update()` bypasses guard]**: The AppSettings `clean()` guard only prevents reduction via `.save()`. Direct `.update()` calls (like existing test `test_reduce_total_tokens_below_assigned_succeeds`) bypass it. → **Mitigation**: Admin form always uses `.save()`. For programmatic access, `.update()` bypass is a Django limitation — document and accept.
- **[`super().save()` outside lock]**: The current `save()` calls `super().save()` after the `with transaction.atomic()` block exits. With `ATOMIC_REQUESTS=False` (default), the lock is released before the actual INSERT/UPDATE. This creates a tiny race window where another process could modify data. → **Mitigation**: Pre-existing issue, not introduced by this fix. The window is milliseconds. For a comprehensive fix, the entire `save()` body should be inside the `transaction.atomic()` block — but that's out of scope for this change.

## Migration Plan

1. Add `clean()` method to `InvitationCode`
2. Add `clean()` method to `AppSettings`
3. Refactor `save()` to still validate under lock but let admin catch fallback errors
4. Add `save_model()` override to `InvitationCodeAdmin`
5. Run existing tests, adjust if needed
6. Manually verify in admin: create code exceeding pool → inline error; reduce max_use below current_use → inline error; reduce total_tokens below assigned → inline error

No database migrations needed. No deployment coordination required.

## Open Questions

<!-- None — implementation is straightforward -->
