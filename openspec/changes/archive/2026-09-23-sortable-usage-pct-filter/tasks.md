## 1. Shared annotation helper

- [x] 1.1 Add `annotate_usage` helper (next to `OrderSummaryAdminMixin` in `project/admin_base.py` or as `ourlives` queryset mixin) emitting `_codes_used`, `_codes_max`, `_usage_pct` with NULL-on-zero semantics
- [x] 1.2 Unit-test the expression: zero quota → NULL, normal → exact pct, empty set → NULL

## 2. InvitationCode changelist

- [x] 2.1 Annotate `_usage_pct` in `InvitationCodeAdmin.get_queryset`, set `admin_order_field` on `usage_percentage`
- [x] 2.2 Add `UsageBucketFilter` (6 buckets incl. 80% warning band + No quota) to `list_filter`
- [x] 2.3 Add numeric threshold filter (`gte`/`lte` on `_usage_pct`)
- [x] 2.4 Admin tests: sort asc/desc with NULLS LAST, each bucket, threshold combo
- [x] 2.5 Set `list_per_page = 50` on `InvitationCodeAdmin`

## 3. Order aggregate

- [x] 3.1 Annotate Order queryset (single reverse-FK sums), add sortable usage column + both filters
- [x] 3.2 Tests: codeless order → `—` last; weighted math (e.g. 4/10 + 6/10 = 50%)

## 4. Organization aggregate (dedup-safe)

- [x] 4.1 Annotate Organization via two disjoint subqueries — (a) direct: `organization=org AND (order IS NULL OR order__org != org)`, (b) via-orders: `order__organization=org` — combined `_usage_pct`, sortable column + both filters
- [x] 4.2 Tests: direct-only, order-only, combined math, dually-linked code counted once, empty org → `—`

## 5. Verification

- [x] 5.1 Run `ourlives` test suite + changelist smoke test (sort/filter on all three admins)
- [x] 5.2 Confirm no migration generated (`makemigrations --check`)
