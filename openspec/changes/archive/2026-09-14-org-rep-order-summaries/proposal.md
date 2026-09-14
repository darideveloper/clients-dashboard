## Why

Staff working in the Django admin have no at-a-glance view of an Organization's or Rep's order history: answering "how much has this company ordered, and when last?" requires opening every Order row and adding up amounts by hand — across two different money concepts and potentially several currencies. Computed summaries on the models, surfaced in both the admin list and the change form, remove that manual work.

## What Changes

- `Organization` and `Rep` each gain five read-only calculated summaries: `order_count`, `agreed_scans_total`, `catalog_items_total`, `combined_total`, `last_order_date`.
- Money summaries are **per-currency breakdowns** (e.g. `USD 1,750.00 · EUR 800.00`), never a single raw cross-currency sum. No currency conversion; breakdown only.
- Pilots are included; null `number_of_scans`/`cost_per_scan` count as 0 (unchanged `total_agreed_price` semantics).
- `OrganizationAdmin` and `RepAdmin` list views gain the new summary columns (`order_count` and `last_order_date` sortable; money columns display-only).
- `OrganizationAdmin` and `RepAdmin` change forms gain a new readonly "Order summary" fieldset section with labels and help texts explaining each figure's origin.
- No database migrations, no signals, no denormalized columns, no new dependencies.

## Capabilities

### New Capabilities

- `org-rep-order-summaries`: per-currency order summaries on Organization and Rep (model properties + admin list/detail rendering), including naming, help texts, currency attribution rules (agreed: order currency → pilot currency; items: parent order → product), and "Uncategorized" bucket for currency-less amounts.

### Modified Capabilities

- `organization-management`: `OrganizationAdmin` `list_display` gains summary columns and the change form gains an "Order summary" fieldset.
- `ourlives-lookup-admin`: `RepAdmin` `list_display` gains summary columns and the change form gains an "Order summary" fieldset.

## Impact

- `ourlives/models.py`: new read-only `@property`s on `Organization`/`Rep` (+ small shared formatting helper, no schema change).
- `ourlives/admin.py`: extended `OrganizationAdmin`/`RepAdmin` (`list_display`, `get_queryset` annotations, `fieldsets`/`readonly_fields`, `@admin.display` methods).
- `ourlives/tests.py`: new tests for summaries, breakdown rendering, and edge cases.
- No impact on Order/OrderItem write paths, Stripe flows, fixtures, or Excel export (summaries are not added to exports in this change).
