## Why

Six implemented CRM models (`Currency`, `Product`, `Contact`, `OrganizationAddress`, `Order`, `OrderItem`) have migrations and model tests but no Django admin registration, so staff cannot browse, search, or export them while the other 10 `ourlives` models can.

## What Changes

- Register `Currency`, `Product`, `Contact`, `OrganizationAddress`, `Order`, `OrderItem` in `ourlives/admin.py`, each as `OurlivesModelAdminBase` (Unfold + Excel export inherited, per `AGENTS.md` convention).
- Mirror existing admin patterns: lookup-style (`Currency`, `Product`) with `active` toggle; FK-heavy (`Contact`, `OrganizationAddress`, `Order`, `OrderItem`) with `list_filter` / `autocomplete_fields` / `search_fields` over related names.
- `Order` gets `OrderItem` tabular inline, `filter_horizontal` for `order_types` M2M, `date_hierarchy=submitted_at`, readonly computed `total_agreed_price` / `is_pilot_order` displays; all concrete fields stay editable.
- `OrderItem` gets readonly computed `line_total`.
- Extend admin tests in the existing `LookupAdminTests` style; no migrations, no model changes.

## Capabilities

### New Capabilities
- `crm-admin-registration`: admin changelist/form behavior (list_display, filters, search, autocomplete, inlines, readonly computed fields) for the six missing CRM models.

### Modified Capabilities
- None (no spec-level requirement changes to existing models; `ourlives-lookup-admin`, `crm-orders`, `crm-phase2-core-models` stay untouched).

## Impact

- Touched: `ourlives/admin.py`, `ourlives/tests.py` (admin tests only).
- Not touched: `ourlives/models.py`, migrations, views, Stripe logic, `project/admin_base.py`.
- Risk: low — admin-only, no schema change. Autocomplete targets require `search_fields` on related admins (already present except new ones, which this change adds).
