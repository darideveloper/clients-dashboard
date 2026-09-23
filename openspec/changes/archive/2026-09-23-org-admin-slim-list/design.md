## Context

`OrganizationAdmin` (`ourlives/admin.py:48`) currently reuses `OrderSummaryAdminMixin.order_summary_displays` (5 columns) in `list_display` plus `name`/`description` → 7-column changelist. The mixin (`project/admin_base.py:184`) is shared with `RepAdmin` and provides annotated/sortable `order_count_display` + `last_order_date_display` and bulk-attached money breakdowns. Detail page already has the "Order summary" fieldset. Decisions from explore: Usage % dummy `0%`; Rep = linked "First Last"; detail section unchanged.

## Goals / Non-Goals

**Goals:**
- Slim 6-column changelist: Name, Orders, Rep, Last Order, Usage %, Combined total last.
- Zero-query dummy Usage %; reuse existing annotations for Orders/Last Order; reuse bulk-attached combined total.
- Keep all totals on detail page unchanged.

**Non-Goals:**
- Real Usage % formula (no `InvitationCode` aggregation, no annotations).
- Changes to mixin, models, `RepAdmin`, permissions, exports.
- Sortable Rep-link or Usage % columns.

## Decisions

1. **Override `list_display` on `OrganizationAdmin` only, don't touch mixin.**
   Rationale: mixin is shared with `RepAdmin`; per-admin override is a 1-line diff with no blast radius. Alternative (mixin flag / subclass param) rejected as unneeded abstraction.
2. **Rep as small `@admin.display(description="Rep")` method with `format_html` + `reverse("admin:ourlives_rep_change")`, fallback `—`.**
   Rationale: matches existing `orders_list` link pattern in the same class; plain `assigned_rep` FK would render unlinked text. Alternative (plain FK column) rejected per user request for link. Non-sortable accepted — sortable rep would need `ordering="assigned_rep__last_name"` annotation work; add when asked.
3. **Dummy `usage_pct_display` returns literal `"0%"`, no ordering, no queryset work.**
   Rationale: YAGNI — real formula TBD; `# ponytail:` comment marks upgrade path (likely `sum(current_use)/sum(max_use)` bulk-attach like `attach_money_breakdowns`). Alternative (model property / annotation now) rejected.
4. **Keep `fieldsets`/`readonly_fields` referencing `order_summary_displays` as-is; keep `combined_total_display` in the list as the final total.**
   Rationale: the final total stays scannable in the list at zero extra cost (already bulk-attached by `changelist_view`); the two partial breakdowns move to detail-only.

## Risks / Trade-offs

- [Risk] Linked rep adds one FK lookup per row → Mitigated via `list_select_related = ("assigned_rep",)` on `OrganizationAdmin` (no per-row queries).
- [Risk] Dummy `0%` could be mistaken for real data → Mitigation: `design.md`/code comment marks it dummy; real formula is a follow-up change.
- [Risk] Existing tests asserting old 7-column `list_display` → Mitigation: update/extend admin display tests in same change.
