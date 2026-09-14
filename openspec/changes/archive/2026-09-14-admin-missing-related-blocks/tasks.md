## 1. Company codes lists

- [x] 1.1 Add `OrganizationAdmin.codes_across_orders_list` (`filter(order__organization=...)`, `org_order_codes_page`, view-all `order__organization__id__exact`) and `OrganizationAdmin.codes_direct_list` (`filter(organization=...)`, `org_codes_page`, view-all `organization__id__exact`), both mirroring `OrderAdmin.codes_list` row format with `view_invitationcode` guards, wired into `fieldsets`/`readonly_fields`
- [x] 1.2 Verify both sections: empty ("No codes yet"), add-view ("—"), no-permission (count only), independent pagination, and view-all links

## 2. Order company card

- [x] 2.1 Add `OrderAdmin.organization_card` display mirroring `rep_card` (name link, primary-else-first address, contact/order/direct-code counts, `view_organization` guard) and wire into Related `fieldsets`/`readonly_fields`
- [x] 2.2 Verify unsaved/no-org ("—"), no-permission (plain name), no-addresses (omit line), and link/count states

## 3. Verification

- [x] 3.1 Run admin-related tests and changelist/detail smoke check (no per-row changelist query regression)
