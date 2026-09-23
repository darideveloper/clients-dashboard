## Why

The Organization changelist is too wide: money totals (agreed scans, catalog items, combined) plus description crowd the list view. Admins need a slim scannable list (Name / Orders / Rep / Last Order / Usage % / Combined total last) with full totals kept on the detail page.

## What Changes

- Organization changelist columns become exactly: Name, Orders, Rep, Last Order, Usage %, Combined total (last).
- Rep renders as "First Last" linked to the Rep change page (`—` when unassigned).
- Usage % is a dummy display returning `0%` (non-sortable, no queries, upgrade path open).
- `combined_total_display` (final total) stays in the list; agreed-scans and catalog-items breakdowns move to detail-only.
- No changes to `OrderSummaryAdminMixin`, `RepAdmin`, models, or queryset logic; only display config on `OrganizationAdmin` (including `list_select_related = ("assigned_rep",)` to keep the linked Rep column query-free).

## Capabilities

### New Capabilities
- `org-admin-slim-list`: slim Organization changelist layout with linked Rep, dummy Usage % column, and Combined total last.

### Modified Capabilities
- `organization-management`: list-view column requirements change (slim 6-column list; partial breakdowns detail-only).

## Impact

- Affected: `ourlives/admin.py` (`OrganizationAdmin` only) and `ourlives/tests.py` (changelist display tests).
- Untouched: `project/admin_base.py`, `ourlives/models.py`, `RepAdmin`, other admins.
- No migrations, no API changes, no permission changes.
