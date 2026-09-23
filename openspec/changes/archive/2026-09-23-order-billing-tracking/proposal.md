## Why

Staff cannot track post-order billing milestones (company invoice sent/paid, rep commission paid) anywhere in the admin. These three states with their dates need to live on the `Order` detail page so finance follow-up happens in one place.

## What Changes

- Add 6 fields to `Order`: `invoice_sent` (bool, default False) + `invoice_sent_on` (date, null+blank), `invoice_paid` (bool, default False) + `invoice_paid_on` (date, null+blank), `commission_paid` (bool, default False) + `commission_paid_on` (date, null+blank). No validation coupling bool and date (explicitly: tick-without-date allowed, date-without-tick allowed, fully manual).
- Add a new `Billing` fieldset to `OrderAdmin` detail page containing exactly those 6 fields, placed after `Terms` and before `Details`. No changes to `list_display`, `list_filter`, `search_fields`.
- New migration for the 6 columns. Excel export picks them up automatically via existing mixins (no per-model wiring).

## Capabilities

### New Capabilities

- `order-billing-tracking`: billing milestone flags + dates on Order and their Billing fieldset presentation in admin detail view.

### Modified Capabilities

- `crm-orders`: Order model field set grows (additive, non-breaking); admin detail layout gains a Billing section. No existing requirement text changes behavior — delta spec records the additions.

## Impact

- Affected code: `ourlives/models.py` (`Order`), `ourlives/admin.py` (`OrderAdmin` fieldsets), one new migration, `ourlives/tests.py` (new model/admin tests).
- No API, dependency, or data-migration impact; existing rows get defaults (`False` / `NULL`). Shared-Postgres worktree note: run migration from one sibling at a time.
