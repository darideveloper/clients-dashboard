## Why

Staff track the rep's commission terms per order (e.g. "15%", "$500 flat") but have nowhere to record them. The Billing section already holds the commission paid flag + date; a short free-text note next to them completes the picture so finance sees terms and status in one place.

## What Changes

- Add 1 optional field to `Order`: `rep_commission_note` (`CharField`, max_length=255, blank=True, default ""). No validation; free text like "15%" or "$500 flat".
- Add `rep_commission_note` to the `Billing` fieldset in `OrderAdmin` detail page, on its own row after the `commission_paid` pair. No changes to `list_display`, `list_filter`, `search_fields`.
- New migration for the column (no backfill; existing rows default to "").

## Capabilities

### New Capabilities

- `order-rep-commission-note`: free-text rep commission note on Order and its Billing fieldset presentation in admin detail view.

### Modified Capabilities

- `order-billing-tracking`: Billing section gains one field (additive, non-breaking). Delta spec records the addition.

## Impact

- Affected code: `ourlives/models.py` (`Order`), `ourlives/admin.py` (`OrderAdmin` Billing fieldset), one new migration, `ourlives/tests.py` (new model/admin tests).
- No API, dependency, or data-migration impact. Shared-Postgres worktree note: migrate from one sibling at a time.
