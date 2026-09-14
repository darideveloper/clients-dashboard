## Context

`ourlives/admin.py` registers 16 models via `OurlivesModelAdminBase` (plus `AppSettings` singleton). Current `search_fields` are all valid but uneven: `StripeEvent` has no search, `OrganizationAddress.line2` is missing, `Order`/`Contact`/`InvitationCode` lack linkage traversals staff type daily, and three categorical FKs lack filters. Scale is hundreds of rows (postgres prod, sqlite dev) — wide `icontains` ORs are still cheap, but M2M/double-hop joins would set a bad precedent. Autocomplete backends already satisfied (every target has `search_fields`). `OrderAdmin` already uses `list_select_related` + `prefetch order_types`.

## Goals / Non-Goals

**Goals:**
- Search bar finds rows by identifiers staff actually type (codes, order/PO numbers, phones, descriptions, org/rep/contact names, Stripe event IDs).
- Every low-cardinality category is one click away via `list_filter`; no search duplicate where a filter already serves.
- Keep per-admin search to ~5–8 fields and ≤2 FK JOINs as a guideline with zero M2M searches; codes use index-friendly prefixes. Documented exception: `Order` uses 11 fields across 4 single-hop JOINs (organization, rep, primary/invoice contacts) — no M2M, fine at hundreds of rows.

**Non-Goals:**
- No model/schema/migration changes; no autocomplete, export, permission, or list-display changes.
- No full-text engine (`@`), no `get_search_results` override (single-token search is enough at this scale).
- No numeric-field search (`quantity`, `amount_cents`, `token_count`) — filters/ranges cover those later if needed.

## Decisions

- **Prefixes: `^` for codes/numbers, bare for names.** `^code`, `^order_number`, `^po_number`, `^iso2/iso3`, `=stripe_event_id` give `istartswith`/`iexact` (`LIKE 'term%'`, B-tree usable) instead of `%term%` scans. Names/descriptions stay `icontains`. Alternative (all bare) rejected: slower at scale and noisier for unique codes.
- **Filter-over-search rule.** Where `list_filter` already exists (`contact_type`, `order_types`, `countries`, `currency`, `country` on addresses), do NOT add the same axis to `search_fields`. High-cardinality FKs (`organization`, `rep`, contacts, `order__order_number`) stay as search because a 100+ entry dropdown is worse than typing. Alternative (mirror everything in both) rejected per user decision: wider ORs for zero UX gain.
- **Three new filters, nothing more.** `InvitationCode.code_type`, `Order.pilot_currency`, `Organization.assigned_rep` — all low-cardinality, all fit existing filter widgets. `Project`/`Rep` get no filter (nothing categorical to filter on). `organization`/`contacts` on `Order` stay out of filters (high cardinality).
- **Cut the expensive traversals.** `Order.items__product__name` (2 hops + DISTINCT) and any `__countries__name` / `__order_types__` M2M search excluded as nice-to-have. Covered by existing `list_filter` + inline visibility.
- **`search_help_text` on 3 heavy admins** (`Order`, `InvitationCode`, `StripeEvent`) so staff know what's covered; cheap, no query cost.

## Risks / Trade-offs

- [Risk] Wider `OR` on `Order`/`Contact` adds JOINs → slower scans → Mitigation: capped field count, `^` prefixes, existing `list_select_related`/pagination bound the cost; re-measure with `EXPLAIN` past ~100k rows.
- [Risk] `^` prefix changes partial-match behavior (infix no longer matches codes) → Mitigation: `search_help_text` documents it; codes are prefix-typed in practice (`OL-`, ISO, currency codes).
- [Risk] `Organization.list_filter=(assigned_rep,)` dropdown grows with Reps → Mitigation: Reps are few by nature (sales team); revisit to autocomplete-style filter if it ever exceeds ~50.
- [Risk] Dropped search axes (`Product` currency text, `OrganizationAddress` country text) surprise staff who typed them → Mitigation: both axes remain one click away via existing `list_filter`; `search_help_text` on heavy admins documents what the bar covers.
