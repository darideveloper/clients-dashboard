## Context

The Organization admin changelist (`OrganizationAdmin`, `ourlives/admin.py:81`) shows `combined_total_display` last, fed by `OrderSummaryAdminMixin.combined_total_display` (`project/admin_base.py:257`, description "Combined total"). The same mixin serves `RepAdmin`, so both share the label. Missing-currency money falls into the `UNCATEGORIZED_CURRENCY = "Uncategorized"` bucket (`ourlives/models.py:21`), rendered by `format_currency_breakdown`. The org change page embeds `OrgOrderInline` (`admin.py:49`, `UnfoldTabularInline`): plain-text `order_number` + `order_link` Change/View column, no money column. Unfold's `tabular_title.html` renders `str(order)` (= order number) as a per-row title, duplicating the first column. `Order` has `total_agreed_price` (scans × cost) but no agreed+items combined figure.

## Goals / Non-Goals

**Goals:**
- Rename the visible money label to "Total Order Value" in Org + Rep admin (list + details).
- Give currency-less money a business-friendly "No Currency" bucket everywhere.
- Make the Orders inline navigable (linked order number) and informative (per-order total), without the doubled title.

**Non-Goals:**
- Renaming `combined_total` / `combined_total_display` code identifiers (label-only change).
- Changing attribution math (currency → pilot → product fallback stays).
- New migrations, API, or checkout-flow changes.
- Touching `OrderAdmin`'s own "Total agreed" column.

## Decisions

- **Label-only rename.** `@admin.display(description="Total Order Value")` on the shared mixin method. Alternative (full code rename over ~40 references incl. specs/tests/annotations) rejected: wide diff, zero runtime benefit; user decision.
- **`UNCATEGORIZED_CURRENCY = "No Currency"`.** A real `Currency` row is impossible (`code` is `max_length=3`), so the bucket stays a display constant — just renamed. One-line change propagates to org/rep rollups, `attach_money_breakdowns`, exports, and seed. Alternative (DB record / nullable-code hack) rejected: violates the 3-char ISO-code invariant.
- **New `Order.total_order_value` property** (`total_agreed_price + Σ items.line_total`) + `OrgOrderInline.total_order_value_display` readonly. Follows the existing property + `*_display` convention (`total_agreed_price` / `OrderAdmin.total_agreed_price_display`). Currency via existing `_order_currency_code(order)` with product-currency fallback for the items portion (same chain as `catalog_items_total`); `—` when the total is zero (same as `format_currency_breakdown` empty-state). Alternative (agreed-only reuse) rejected: mislabeled as "total" while ignoring items; user decision.
- **`order_number_link` readonly on the inline**, mirroring `order_link`'s perm-aware Change/View + `inlinechangelink`/`inlineviewlink` classes, description "Order number", swapped into `fields`/`readonly_fields`. Keeps the existing action column (user decision: two linked columns).
- **`hide_title = True`** on `OrgOrderInline` (supported Unfold opt, default `False` in `unfold/admin.py:265`). Removes the doubled title row; per-row history shortcuts in that row go with it (accepted: history remains on the Order change page).
- **N+1 guard:** `prefetch_related("items")` (plus `select_related("currency", "pilot_currency")`) on the inline queryset; totals computed in Python per row over a bounded row set.

## Risks / Trade-offs

- [Risk] Per-row Python totals could regress change-page queries → Mitigation: prefetch in `OrgOrderInline.get_queryset`; assert query count in tests.
- [Risk] Items in a different currency than the order get attributed to the order's currency code → Mitigation: same documented rule as the org rollup ("amounts in different currencies are never added together" applies across holders, not within one order's display); currency code shown next to the figure.
- [Risk] Label-only rename leaves `combined_total` identifiers visible in code/specs → Mitigation: accepted explicitly; spec deltas document the display label as the contract.
- [Risk] `hide_title` also hides the row's view/history shortcuts → Mitigation: accepted; navigation covered by the two link columns.

## Open Questions

None — all gaps resolved in explore (rename depth: label-only; perms: mirror; currency fallback: full chain; missing currency: "No Currency" global; zero: —; title row: hide entire row).
