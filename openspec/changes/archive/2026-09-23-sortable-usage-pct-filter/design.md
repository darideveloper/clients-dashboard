## Context

`InvitationCodeAdmin.usage_percentage` (`ourlives/admin.py:155-159`) is pure Python (`current_use/max_use*100`), so the DB cannot ORDER BY it. `Order`/`Organization` have no usage aggregate. The codebase precedent for sortable calculated columns is `OrderSummaryAdminMixin.get_queryset` annotating `_order_count`/`_last_order_date` (`project/admin_base.py:184-207`). Unfold filter primitives (`DropdownFilter`, `RelatedDropdownFilter`) are already imported in `ourlives/admin.py:11-17`.

Key relation facts: `InvitationCode.organization` FK has **no** `related_name` (reverse = `invitationcode_set`); `project`/`order`/`code_type` FKs use `related_name="invitation_codes"`. Every code has a required `organization`, plus optional `order` whose org may differ — so the org aggregate must OR both paths over the same rows (no double-count of a single row).

## Goals / Non-Goals

**Goals:**
- Sortable usage % on all three changelists via annotation (no migration).
- One bucket filter + one numeric threshold filter, reusable across the three admins.
- Token-weighted org aggregate combining direct + order codes, dedup-safe.

**Non-Goals:**
- Stored/materialized `%` column; per-code-average aggregate; Excel format changes; API changes.

## Decisions

1. **Annotation over stored field.** `Case(When(max_use=0 → NULL), default=ExpressionWrapper(F(current_use)*100.0/F(max_use), FloatField))` as `_usage_pct`; column sets `admin_order_field="_usage_pct"`. Rationale: per-row arithmetic, zero JOINs, always fresh despite external `current_use` bumps; no migration/sync code. Alternative (generated/stored column) rejected: sync burden + stale-read risk at current scale.
2. **Shared helper mirroring `OrderSummaryAdminMixin`.** Single `annotate_usage(qs, ...)` (location: `project/admin_base.py` next to the existing mixin, or `ourlives/models.py` queryset — decide at implement time) emitting `_codes_used`, `_codes_max`, `_usage_pct`. InvitationCode uses prefix `""`; Order uses `invitation_codes__`; Organization combines two subqueries. Rationale: one formula, three consumers.
3. **Subqueries for Organization, plain aggregate for Order.** Order needs one reverse-FK `Sum` (no fan-out). Organization joining `invitationcode_set` AND `orders__invitation_codes` in a single `annotate(Sum)` would cartesian-product and inflate sums → use two disjoint `Subquery(OuterRef)` sums then add them: (a) direct = codes with `organization=OuterRef(pk)` AND (`order IS NULL` OR `order__organization != OuterRef(pk)`); (b) via-orders = codes with `order__organization=OuterRef(pk)` (all of them, regardless of their own `organization` FK). Every code linked to the org through either path falls in exactly one subquery, so dually-linked rows count once. Then compute `_usage_pct` from the added sums. Rationale: correctness over cleverness.
4. **Filters:** `UsageBucketFilter(SimpleListFilter)` with 6 buckets (Unused/Low/Half/Warning/Full/No quota) filtering on `_usage_pct` ranges + NULL; plus threshold filter (`usage__gte`/`usage__lte` query params or Unfold numeric range) for arbitrary X%. Rationale: buckets answer "about to run out" in one click; threshold covers ad-hoc ops queries.

## Risks / Trade-offs

- [Risk] JOIN fan-out inflating org sums → Mitigation: subqueries only; regression test with code linked to both org paths counts once.
- [Risk] Division by zero / NULL sort position differences across DBs → Mitigation: `Case→NULL`, explicit `NULLS LAST`, tests on Postgres (shared dev DB) + SQLite escape hatch.
- [Risk] Filter on annotation forces GROUP BY cost on large changelists → Mitigation: pagination bounds it; revisit materialization only if measured >200ms.
