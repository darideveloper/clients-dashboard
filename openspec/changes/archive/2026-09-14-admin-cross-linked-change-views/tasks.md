## 1. Shared pagination helper

- [x] 1.1 Add request-stash `change_view` override plus a small paginate-and-render helper (`Paginator` 25/page, per-list GET key, prev/next + "Page X of Y" + view-all link via `format_html`) in `ourlives/admin.py`
- [x] 1.2 Verify helper degrades to page 1 when no request stashed (add view / bare calls) and to last/first page on invalid input

## 2. Company change page

- [x] 2.1 Add `Orders` fieldset with `orders_list` readonly to `OrganizationAdmin`
- [x] 2.2 Implement `orders_list` (`order_number — po_number — total`, links to `admin:ourlives_order_change`, `?org_orders_page=N`, view-all `?organization__id__exact=`, `view_order` guard, "—" / "No orders yet" states)

## 3. Rep change page

- [x] 3.1 Add `Companies` / `Orders` fieldsets with `companies_list` / `orders_list` readonly to `RepAdmin`
- [x] 3.2 Implement `companies_list` (names → `admin:ourlives_organization_change`, `?rep_companies_page=N`, view-all `?assigned_rep__id__exact=`, `view_organization` guard)
- [x] 3.3 Implement `orders_list` (numbers → `admin:ourlives_order_change`, `?rep_orders_page=N`, view-all `?rep__id__exact=`, `view_order` guard)
- [x] 3.4 Extend `RepAdmin.get_queryset` with `prefetch_related("organizations", "orders")`

## 4. Order change page

- [x] 4.1 Add `Related` fieldset (`rep_card`, `contacts_list`, `codes_list`, existing displays, readonly `submitted_at`) to `OrderAdmin`
- [x] 4.2 Implement `rep_card` (name link → `admin:ourlives_rep_change`, `mailto:`, company/order counts, "Open rep", `view_rep` guard)
- [x] 4.3 Implement `contacts_list` (all org contacts with type/email/phone, `(primary)`/`(invoice)` badges, links → `admin:ourlives_contact_change`, `?order_contacts_page=N`, view-all `?organization__id__exact=`, `view_contact` guard)
- [x] 4.4 Implement `codes_list` (`code`, `project`, `code_type`, `current/max`, links → `admin:ourlives_invitationcode_change`, `?order_codes_page=N`, view-all `?order__id__exact=`, `view_invitationcode` guard)
- [x] 4.5 Extend `OrderAdmin.get_queryset` with `select_related("organization", "rep", "primary_contact", "invoice_contact")` plus list prefetches (keep existing `prefetch_related("order_types")`)

## 5. Verification

- [x] 5.1 Add change-view GET tests in `ourlives/tests.py`: sections render with links; `?*_page=2` and invalid pages behave; add view "—"; no-perm count-only; empty "No … yet"
- [x] 5.2 Run `python manage.py check` and the targeted tests; manually open the three change pages and click row + view-all + pagination links
