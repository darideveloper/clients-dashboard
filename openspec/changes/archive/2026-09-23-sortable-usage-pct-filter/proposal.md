## Why

The InvitationCode changelist shows a Python-computed "Usage %" column that can neither be sorted nor filtered, and Order/Organization admins have no usage aggregate at all — ops cannot answer "who is about to run out?" without exporting to Excel.

## What Changes

- Annotate `InvitationCode` queryset with sortable `_usage_pct` (`current_use*100.0/max_use`, NULL when `max_use=0`) and point `usage_percentage` at it via `admin_order_field`.
- Add `UsageBucketFilter` (Unused 0% / Low >0–<50% / Half 50–<80% / Warning 80–<100% / Full 100% / No quota) + numeric `≥ / ≤` threshold filter on usage %.
- Add shared token-weighted aggregate (`SUM(used)/SUM(max)`) to Order admin (direct codes) and Organization admin (direct + across-orders combined, dedup-safe), both sortable and filterable with the same buckets.
- Empty sets / zero quota render `—` and sort NULLS LAST. No schema migration.
- InvitationCode changelist shows 50 results per page (`list_per_page = 50`).

## Capabilities

### New Capabilities
- `usage-stats`: sortable/filterable token-weighted usage % on invitation codes, orders, and organizations (columns, bucket + threshold filters, empty-set semantics).

### Modified Capabilities
- None (existing specs describe display/validation behavior; this adds annotation-backed sort/filter without changing those requirements).

## Impact

- `ourlives/models.py`: shared queryset helper (annotation expressions only, no fields).
- `ourlives/admin.py`: `InvitationCodeAdmin`, `OrderAdmin`, `OrganizationAdmin` `get_queryset`/`list_display`/`list_filter`.
- `project/admin_base.py` if the shared mixin lives there (mirrors `OrderSummaryAdminMixin`).
- No migrations, no API changes, no Excel export format change.
