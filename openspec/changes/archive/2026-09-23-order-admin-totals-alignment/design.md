## Context

`OrderAdmin` (`ourlives/admin.py`) previously rendered a single `total_agreed_price_display` ("Total agreed", bare number) in the list and "Terms" fieldset. The org admin used different labels and a per-currency rollup. The `Order` model already has `Order.total_order_value` (`models.py:681`) = agreed + Σ items, and `OrderItem.line_total` exists. `OrgOrderInline` already had a `total_order_value_display` with inline formatting logic.

## Goals / Non-Goals

**Goals:**
- Use the org's money labels in the Order admin ("Agreed scans total", "Catalog items total", "Total Order Value").
- Render all three totals on the Order detail page; only the final total in the list.
- Share identical formatting between Order admin and org-orders inline.

**Non-Goals:**
- Renaming model identifiers (`total_agreed_price`, `total_order_value`) — display-label-only.
- Changing the org rollup math or the per-order formulas.
- New migrations, APIs, or sections (totals live in the existing "Terms" fieldset per user decision).

## Decisions

- **Shared `format_order_money(order, amount)` helper** (module-level in `ourlives/admin.py`): resolves one display string per order — code via `_order_currency_code` (order → pilot), falling back to the first resolvable item `Product.currency`, else the `UNCATEGORIZED_CURRENCY` ("No Currency") label; `"CODE amount"`, `—` when the amount is falsy or obj is unsaved. Both `OrderAdmin` display methods and `OrgOrderInline.total_order_value_display` call it, so the two screens can't drift. Alternative (duplicate formatting per method) rejected as a drift hazard.
- **Agreed renders via the helper too** (`CODE amount` instead of bare `1250.00`) so the three Terms money fields look consistent next to each other.
- **List shows only final total**: `total_order_value_display` replaces `total_agreed_price_display` in `list_display` (display-only, non-sortable, consistent with org list). Detail Terms carries all three.
- **N+1 guard**: `get_queryset` gains `prefetch_related("items__product__currency")`; the helper iterates `order.items.all()`, and both the list total column and Terms fields read from the prefetched cache, so the changelist stays constant-query.
- **Mixed-currency items** render under the first resolvable code (single figure) — the same documented rule as the org rollup; the org rollup keeps per-currency separation; the per-order figure uses a single code.

## Risks / Trade-offs

- [Risk] Per-order totals iterate related items in Python → Mitigation: items prefetched in `get_queryset`; bounded rows per order.
- [Risk] Mixed-currency order shown under one code → Mitigation: documented single-figure rule; matches inline behavior; org rollup remains per-currency.
- [Risk] List column is non-sortable → Mitigation: consistent with org list; no `ordering=` applied.
- [Risk] Label-only rename leaves `total_agreed_price` identifiers in code → Mitigation: accepted; spec delta updates the *display contract* (order-admin-registration `list_display`).

## Open Questions

None — all resolved in the plan (placement: Terms fieldset; list: final total only; agreed format: via helper; helper naming/location: module-level in `admin.py`).