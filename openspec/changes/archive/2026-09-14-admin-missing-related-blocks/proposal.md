## Why

Company (Organization) change pages show orders but not the invitation codes across those orders, and Order change pages show a rich Rep card but only a bare FK for the Company — staff must click away to answer "which codes belong to this company?" and "which company is this order for?".

## What Changes

- Add two read-only paginated `Codes` sections to `OrganizationAdmin`: (a) codes across the company's orders (`InvitationCode.order.organization`), and (b) directly-assigned codes (`InvitationCode.organization`, including orderless ones) — both using the same row format as `OrderAdmin.codes_list`.
- Add read-only `Company` card to `OrderAdmin` Related section mirroring `rep_card` (name link, primary address, contact/order/code counts, "Open company" link).
- No model/schema changes; no new dependencies; both blocks reuse `paginate_related` / `related_list` / `related_footer` / `ChangeRequestStashMixin` permission-guard pattern.

## Capabilities

### New Capabilities

- None — behavior extends the existing cross-linked change-view contract.

### Modified Capabilities

- `admin-cross-linked-change-views`: extend Company page with two Codes requirements (across-orders + directly-assigned) and Order page with Company-card requirement (delta spec).

## Impact

- Affected code: `ourlives/admin.py` (`OrganizationAdmin`, `OrderAdmin`) only; read-only display methods + `fieldsets`/`readonly_fields`.
- Queries: +2 per detail view per new block (count + one page fetch); changelist queries unchanged.
- Permissions: new rows gated on existing `view_invitationcode` / `view_organization`; no permission changes.
