## Why

Ops staff open a Company, Rep, or Order change page and cannot see the records linked to it: Company shows no Orders, Rep shows neither Companies nor Orders, and Order shows no Codes and only bare dropdowns for Rep/Contacts. They must hop between changelists to reconstruct one business story.

## What Changes

- Company (Organization) change page gains a read-only, paginated Orders section (25/page) with links to each Order change page plus a "View all" link to the pre-filtered Order changelist. Contacts/Addresses inlines stay editable and unchanged.
- Rep change page gains read-only, paginated Companies and Orders sections (25/page each) with change-page links plus "View all" links to the pre-filtered changelists.
- Order change page gains: a mini Rep card (name + email + company/order counts + link), a full paginated org-contacts list (25/page, with primary/invoice badges, links to Contact change pages), and a paginated Codes table (25/page, main fields only, links to InvitationCode change pages) plus "View all" links. `submitted_at` becomes readonly so "all details" is literal. Existing dropdowns and the OrderItems inline stay editable.
- All new sections are view-only (click through to edit on the related page), permission-guarded per related model, and capped with in-page pagination (GET-param pages) with the filtered changelist as fallback.

## Capabilities

### New Capabilities

- `admin-cross-linked-change-views`: read-only paginated related sections (orders on Company; companies + orders on Rep; rep card + all org contacts + codes on Order) on the three change pages, including pagination, permission guards, empty/add-view states, and queryset prefetching.

### Modified Capabilities

- None — no model, API, or existing spec requirement changes; display-only additions.

## Impact

- Touched: `ourlives/admin.py` (one request-stash helper + 6 display methods + fieldsets + `get_queryset` prefetching), `ourlives/tests.py` (change-view GET tests).
- Untouched: models/migrations, list displays, filters, autocomplete, inlines, exports, sidebar, permissions schema.
- No new dependencies; no breaking changes.
