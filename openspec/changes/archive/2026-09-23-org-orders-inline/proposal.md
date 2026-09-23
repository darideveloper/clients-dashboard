## Why

The Organization detail page shows orders as a hand-rolled HTML list (`orders_list`: number — PO — money, paginated) with no per-order scan visibility. Admins need scans per order plus the total scans in a native inline table showing only the relevant columns.

## What Changes

- Add a display-only `OrgOrderInline` (Unfold tabular inline) on `OrganizationAdmin` with columns `order_number`, `number_of_scans`, `submitted_at` plus the native change link; `extra=0`, no add/delete, all fields readonly.
- **BREAKING** (admin display only): delete the hand-rolled `orders_list` method and its `"Orders"` fieldset section; the inline becomes the single Orders truth on the detail page.
- Add a readonly `total_scans_display` line (`Total: N scans across M orders`; null scans count as 0, shown as `—` per row; count-only `"N orders"` without Order view permission, mirroring the old gate).
- Update detail-view tests asserting the old `orders_list` strings to inline behavior. No model, migration, permission, or changelist changes.

## Capabilities

### New Capabilities
- `org-orders-inline`: tabular Orders inline (relevant columns only) plus total-scans line on the Organization detail page.

### Modified Capabilities
- (none — detail Orders section was not spec-pinned; changelist specs untouched)

## Impact

- Affected: `ourlives/admin.py` (`OrganizationAdmin` + new inline class), `ourlives/tests.py` (detail-view assertions).
- Untouched: `project/admin_base.py`, `ourlives/models.py`, `RepAdmin`, changelist config, permissions, exports.
- No migrations, no API changes.
