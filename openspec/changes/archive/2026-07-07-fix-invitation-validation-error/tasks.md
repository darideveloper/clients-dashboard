## 1. Add InvitationCode.clean() validation

- [x] 1.1 Add `clean()` method to `InvitationCode` with token pool check (assigned + max_use > total_tokens) raising field-specific `ValidationError({"max_use": "..."})` so error appears inline on the max_use field in admin
- [x] 1.2 Add max_use < current_use check to `clean()` for updates — must fetch `old = InvitationCode.objects.get(pk=self.pk)` from DB (do NOT use `self.current_use` which may be stale), raising `ValidationError({"max_use": "..."})`
- [x] 1.3 Keep lock-based token pool and max_use checks in `save()` as race-condition safety net (do NOT remove — these run under SELECT FOR UPDATE and catch concurrent admin races)

## 2. Add AppSettings.clean() validation

- [x] 2.1 Add `save()` override to `AppSettings` that calls `clean()` via `full_clean()`
- [x] 2.2 Add `clean()` method to `AppSettings` rejecting total_tokens < tokens_assigned

## 3. Update admin for graceful error handling

- [x] 3.1 Override `save_model()` in `InvitationCodeAdmin` to catch `ValidationError` and use `messages.error()` as fallback — note: user sees red banner + redirect to list, not inline form re-render
- [x] 3.2 Add `from django.contrib import messages` import to admin.py

## 4. Update tests

- [x] 4.1 Verify existing tests still pass with validation moved to `clean()`
- [x] 4.2 Adjust tests if any rely on ValidationError being raised in `save()` specifically (vs `clean()`)
- [x] 4.3 Add test for reducing total_tokens below tokens_assigned raising ValidationError via `.save()` (not `.update()` — which bypasses validation)
- [x] 4.4 Review `test_reduce_total_tokens_below_assigned_succeeds` — it uses `.update()` which bypasses `save()`. Add assertion that `.save()` is rejected, or rename to clarify it tests `.update()` bypass behavior

## 5. Manual verification

- [x] 5.1 Manually create invitation code exceeding token pool → confirm inline form error, no debug page
- [x] 5.2 Manually edit invitation code with max_use < current_use → confirm inline form error
- [x] 5.3 Manually reduce AppSettings total_tokens below assigned → confirm inline form error
