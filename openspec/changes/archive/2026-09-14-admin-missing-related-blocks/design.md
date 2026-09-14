## Context

`OrganizationAdmin` (`ourlives/admin.py:48`) renders `orders_list` but no codes; `OrderAdmin` (`ourlives/admin.py:332`) renders `rep_card` + `contacts_list` + `codes_list` but the company is only an autocomplete FK. The relation chain `InvitationCode.order → Order.organization` already exists (`ourlives/models.py:158`), so both gaps are display-only. House pattern for all sibling blocks: readonly `@admin.display` method + `ChangeRequestStashMixin._change_request` for pagination (`paginate_related`, 25/page) and permission guards + `related_rows` / `related_list` / `related_footer` (`project/admin_base.py:25-96`). User decisions (explore): codes rows identical to Order view, rich company card mirroring `rep_card`, read-only lists, no other gaps.

## Goals / Non-Goals

**Goals:**
- Company page lists every code across its orders with the same columns/link style as the Order codes table.
- Order page shows a Company card with the same affordances as the Rep card.
- Zero new queries on changelists; detail views add a constant handful of queries per new block (count + one page per list; a few counts on the card).

**Non-Goals:**
- No model, migration, permission, export, or summary-math changes.
- No editable inlines for codes on Company (2-hop relation can't be a real inline).
- No Unfold tabs / custom templates / new helpers.

## Decisions

- **Company codes: two separate sections mirroring `OrderAdmin.codes_list`** — (a) `codes_across_orders_list`: `InvitationCode.objects.filter(order__organization=obj).select_related("project","code_type").order_by("code")`, page key `org_order_codes_page`, view-all → `admin:ourlives_invitationcode_changelist?order__organization__id__exact=<pk>`; (b) `codes_direct_list`: `InvitationCode.objects.filter(organization=obj).select_related("project","code_type").order_by("code")`, page key `org_codes_page`, view-all → `admin:ourlives_invitationcode_changelist?organization__id__exact=<pk>` (this one matches an existing `list_filter`). Both rows `<a>code</a> — project — code_type|— — used/max`, both perm-guarded by `view_invitationcode` (plain count otherwise), both "No codes yet" when empty. Separate page keys are required because two paginated lists share one change page. Why: the two scopes diverge (orderless codes exist; `order.organization` can differ from `code.organization`), so merging them would mislead; alternative single merged section rejected.
- **`OrderAdmin.organization_card` mirrors `rep_card`** — name link to `admin:ourlives_organization_change`, address line resolving to the primary address else the first address (omitted only when the org has no addresses at all), `N contacts · N orders · N codes` counts (`N codes` = directly-assigned `InvitationCode.organization` count, matching the changelist `organization` filter), `Open company →` link, perm-guard `view_organization` else plain name. Placed in `Related` fieldset beside `rep_card`. Why: symmetric navigation both directions; alternative full-detail embed (address + all contacts inline) rejected — contacts already listed in `contacts_list`, duplication doubles queries.
- **No `get_queryset` / changelist changes** — both blocks render on the detail page only, so list performance is untouched. Counts on the card use `.count()` (3 cheap queries, detail view only).

## Risks / Trade-offs

- [Large org: 1000s of codes] → Mitigation: paginated 25/page, `select_related`, count + one page only — same as existing orders/codes blocks.
- [No primary address] → Mitigation: fall back to first address, else omit address line (never "—" the whole card when org exists).
- [Stale `_change_request` on add view] → Mitigation: same guard as siblings — unsaved parent returns "—".
