## Context

`ourlives/admin.py` registers `OrganizationAdmin` (Contact + Address stacked inlines, no Orders), `RepAdmin` (own fields only, no inlines), and `OrderAdmin` (`OrderItemInline` only). All missing relations are reverse FKs to independent `PROTECT` entities: `Order.organization → orders`, `Organization.assigned_rep → organizations`, `Order.rep → orders`, `InvitationCode.order → invitation_codes`. Owned `CASCADE` children are already editable inlines; the change follows that established rule. Stack: Django 5.2, django-unfold 0.77.1, no custom change templates; `format_html` + `reverse()` link pattern exists (`AppSettingsAdmin.sync_stripe_price_link`). Scale confirmed <100 rows per relation. Requested: 25/page in-page pagination with changelist fallback, full org-contacts list on Order, mini Rep card on Order.

## Goals / Non-Goals

**Goals:**
- Each of the three change pages surfaces its missing relations as read-only, paginated, permission-guarded link sections.
- Click-through editing on the related page (no duplicate edit forms).
- No N+1 regressions; no new queries on unrelated pages.

**Non-Goals:**
- Editable `OrderInline` / `InvitationCodeInline` (rejected: Order has ~15 mostly-required fields; InvitationCode token-pool `SUM` + `select_for_update` validation in `models.py:106-165` is not formset-safe).
- Same-org enforcement for `primary/invoice_contact` (data-integrity change, separate proposal).
- Custom change templates, new dependencies, model/schema changes, Contact/Code page changes.

## Decisions

- **Read-only display methods over inlines** for all six sections. Rationale: matches the existing CASCADE-inline / PROTECT-link split, ~10 lines per section using the established `format_html` pattern, zero validation duplication. Alternative (editable inlines) rejected per Non-Goals.
- **Request stash via `change_view` override** (`self._change_request = request`) so display methods can read pagination GET params. Rationale: `@admin.display` methods receive only `(obj)`; this is the minimal stdlib-free mechanism (6 lines, one place). Alternative (custom template tags / views) rejected as heavier for the same outcome.
- **Per-list GET keys** (`org_orders_page`, `rep_companies_page`, `rep_orders_page`, `order_codes_page`, `order_contacts_page`) with `django.core.paginator.Paginator(…, 25)`. Rationale: Rep and Order pages host 2–3 lists each; shared `?page=` keys would collide. Page links copy `request.GET` and replace only the own key.
- **Filtered changelist as co-primary fallback**: every section ends with `View all N →` (`?organization__id__exact=`, `?assigned_rep__id__exact=`, `?rep__id__exact=`, `?order__id__exact=`). Rationale: native Unfold pagination for free; if Unfold ever strips query strings from readonly output, the fallback still carries full pagination.
- **Explicit `fieldsets`** on all three admins (currently none). Rationale: readonly additions need a home (`Orders` on Company; `Companies`/`Orders` on Rep; `Related` on Order) instead of piling at the form bottom; also hosts new readonly `submitted_at` on Order.
- **Queryset tuning**: `RepAdmin.get_queryset += prefetch_related("organizations","orders")`; `OrderAdmin.get_queryset += select_related("organization","rep","primary_contact","invoice_contact","currency","pilot_currency")` (keeping `prefetch_related("order_types")`); each related list runs its own page-bounded query (count + one 25-row slice) with `select_related` for row columns (`organization`; `project`/`code_type`; `contact_type`) instead of full-relation prefetches. Rationale: at <100 rows/page-bounded queries load less than prefetching whole relations, with no N+1 either way.

## Risks / Trade-offs

- [Risk] Unfold strips or escapes pagination query strings inside readonly fields → Mitigation: view-all fallback links carry native pagination; page links use plain `<a href="?key=N">` with `format_html`.
- [Risk] `_change_request` stale across requests (admin instance shared) → Mitigation: set on every `change_view` call before rendering; display methods fall back to page 1 when absent (add view, tests without full request).
- [Risk] Extra ~2 queries per section (count + slice) → Mitigation: confirmed scale <100; counts come from the same filtered queryset; no prefetch of full related tables.
- [Risk] Permission leak (emails in Rep card / contacts) → Mitigation: each section checks its `view_*` perm and degrades to count-only text; no emails rendered without `view_rep`/`view_contact`.
