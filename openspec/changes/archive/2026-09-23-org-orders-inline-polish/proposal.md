## Why

The Orders inline's change link renders in the title row spanning the table instead of as a per-row action, and the Orders section sits last below Contacts/Addresses. Admins need a per-row Change action in its own last column and Orders as the first inline section.

## What Changes

- Replace the title-row change link (`show_change_link=False`) with a readonly `order_link` last column (blank header; permission-aware `"Change"`/`"View"` label via `inlinechangelink`/`inlineviewlink` class; blank for unsaved rows).
- Reorder `OrganizationAdmin.inlines` to `(OrgOrderInline, ContactInline, OrganizationAddressInline)` so Orders renders first.
- Update inline assertions and rendered-content tests. No model, migration, permission, changelist, or fieldset changes.

## Capabilities

### New Capabilities
- (none)

### Modified Capabilities
- `org-orders-inline`: inline column set gains the trailing action column; inline section order changes (Orders first); link becomes permission-aware.

## Impact

- Affected: `ourlives/admin.py` (`OrgOrderInline` + `inlines` order), `ourlives/tests.py` (inline assertions, rendered content).
- Untouched: `project/admin_base.py`, `ourlives/models.py`, fieldsets, changelist, permissions, exports.
- No migrations, no API changes.
