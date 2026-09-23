## Context

`OrganizationAdmin` (`ourlives/admin.py:48`) renders orders via the hand-rolled `orders_list` display method (`:82-109`): one HTML row per order (`order_number — po_number — total_agreed_price`), custom 25/page pagination, custom empty/permission strings. The admin already uses real inlines (`ContactInline`, `OrganizationAddressInline`, both `UnfoldStackedInline` with `extra=0`), and `UnfoldTabularInline` is already imported (`admin.py:10`). `Order.organization` is the single FK to `Organization` (`related_name="orders"`, `Meta.ordering = ["order_number"]`), so an inline needs no `fk_name` and rows arrive pre-sorted. Decisions from explore: columns `order_number`/`number_of_scans`/`submitted_at`; replace (not coexist); total as a cheap readonly line.

## Goals / Non-Goals

**Goals:**
- Display-only tabular Orders inline on the Organization detail page with relevant columns only.
- Per-order scans visible plus a total-scans line (`Total: N scans across M orders`).
- Delete `orders_list`; the inline is the single Orders truth.

**Non-Goals:**
- Inline editing/adding/deleting of orders from the Organization page.
- Custom inline template or footer row.
- Pagination on the inline; changes to changelist, models, permissions, exports.

## Decisions

1. **`OrgOrderInline(UnfoldTabularInline)` with `fields = readonly_fields = ("order_number", "number_of_scans", "submitted_at")`, `extra=0`, `can_delete=False`, `show_change_link=True`, `has_add_permission → False`.**
   Rationale: declarative replacement for ~28 lines of hand-rolled HTML; Django owns rendering, links, and empty/perm states. Readonly-all avoids inline validation against required fields (`rep`, `po_number`); `extra=0` + no add permission means no empty forms ever validate. Alternative (keep `orders_list` and append scans) rejected per user choice; alternative (editable inline) rejected — order editing belongs on the Order page.
2. **Total as separate readonly `total_scans_display` field, not an inline footer.**
   Rationale: Django has no native inline footer; a custom template would fork Unfold's tabular styling (highest-risk piece). A one-method aggregate (`Coalesce(Sum("number_of_scans"), 0)` over full `obj.orders`) is zero-template and pagination-proof. Accepted downside: fieldsets render above inlines, so the total sits above the table.
3. **Null scans render `—` per row, count as 0 in the total; permission behavior is explicit per element.**
   Rationale: null handling matches `total_agreed_price` (`models.py:666`) and `agreed_scans_total` (`models.py:64`). Django hides the whole inline without Order view/change permission (stricter than the old `"N orders"` count fallback — accepted). `total_scans_display` has no automatic gate, so it replicates the old branch explicitly: without `view_order` it renders count-only (`"N orders"`), never the sum.
4. **No `select_related` on the inline queryset.**
   Rationale: all shown columns (`order_number`, `number_of_scans`, `submitted_at`) are local fields — no FK traversal, so the inline's single filtered query stays flat. Add `select_related` only if a related column joins the inline later.

## Risks / Trade-offs

- [Risk] Inline renders ALL orders (no pagination; previous list paged at 25) → Mitigation: 3 narrow columns + `select_related`; acceptable unless an org holds hundreds of orders, then revisit (custom template or paginated list).
- [Risk] Existing tests assert `orders_list` strings (`"View all 1 order"`, `"No orders yet"`, perm `"1 order"`) → Mitigation: update those assertions to inline behavior in the same change.
- [Risk] `total_scans_display` sits above the inline table (fieldsets render before inlines) → Mitigation: accepted; alternative (template footer) rejected as higher risk.
