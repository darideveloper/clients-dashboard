## 1. Command skeleton

- [x] 1.1 Create `ourlives/management/__init__.py` and `ourlives/management/commands/__init__.py` package files
- [x] 1.2 Create `ourlives/management/commands/import_invitation_codes.py` with `BaseCommand` subclass and docstring explaining full usage (CSV format, column mapping, token pool behavior, idempotency)
- [x] 1.3 Add `--project` argument (required, project name string)
- [x] 1.4 Add `--csv` argument (required, path to CSV file)

## 2. Validation layer (all upfront, no DB writes)

- [x] 2.1 Validate CSV file exists and is readable; exit with error if not
- [x] 2.2 Parse CSV header, validate required columns present (`code`, `max_use_rate`, `current_use_rate`, `is_active`), exit with error listing missing columns
- [x] 2.3 Validate each row: `code` non-empty, `max_use_rate` and `current_use_rate` are positive integers, `is_active` is a recognizable boolean, `current_use_rate ≤ max_use_rate`
- [x] 2.4 Look up `Project` by name, exit with error if not found

## 3. Token pool adjustment

- [x] 3.1 Calculate sum of all `max_use_rate` values from CSV rows
- [x] 3.2 Compare against `AppSettings.total_tokens`; if insufficient, set `total_tokens` to required sum, report old → new value, save

## 4. Bulk insert with fallback

- [x] 4.1 Build `InvitationCode` object list (unsaved) from validated rows, mapped to the resolved project
- [x] 4.2 Attempt `InvitationCode.objects.bulk_create(objects)`; if successful, report count created
- [x] 4.3 On `IntegrityError` (unique constraint from pre-existing codes), fall back to per-row `update_or_create(code=code, defaults={...})` with progress output per row

## 5. Summary and verification

- [x] 5.1 Print final summary: total rows processed, created count, updated count, errors (if any from fallback path)
- [x] 5.2 Manual smoke test: run command with the provided `invitations_codes.csv` against the "ourlens" project, verify all 42 codes appear in Django admin
  *(Ran 2026-07-09. Result: 42 codes created, 0 updated. Token pool bumped 100→255. All codes verified via SQL query.)*

## 6. Verification-fix cycle

- [x] 6.1 Fix swapped variables in "Token pool sufficient" message (was printing "X needed ≤ Y" with labels reversed)
- [x] 6.2 Fix missing f-prefix in dead-code path on line 228
- [x] 6.3 Make `_boolish()` raise ValueError on unrecognized values to enforce spec's non-boolean validation
- [x] 6.4 Narrow `except Exception` to `except IntegrityError` on bulk_create fallback
- [x] 6.5 Account for existing codes in token pool check (`needed = existing_assigned + new_tokens`)
- [x] 6.6 Reject `max_use <= 0` (spec says "positive integer")
- [x] 6.7 Add 12 unit tests covering all spec scenarios
