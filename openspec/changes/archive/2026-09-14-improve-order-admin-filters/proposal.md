## Why

Support/ops staff cannot triage `Order` rows by the axes they actually think in (company, rep, either contact, product, date window, referral org). The current `OrderAdmin.list_filter` exposes type/rep/currencies/boolean flags only, forcing broad `search_fields` text queries for work that belongs in structured filters.

## What Changes

- `OrderAdmin.list_filter` rebuilt in this exact sidebar order: Company (`organization`), Rep, Primary contact, Invoice contact, Product (via items), Submitted date range, Referral organisation text, then existing flags (`order_types`, `hcaptcha_verified`, `is_upgrade_from_pilot`, `is_referral_order`), then `currency` + `pilot_currency` dead last.
- FK filters (`organization`, `rep`, `primary_contact`, `invoice_contact`) use autocomplete-backed select filters so they scale with client growth.
- Currency filters become explicit dropdowns (only ~12 active rows) and move to the bottom as requested.
- New custom single-select Product filter over `items__product` (all products, active + inactive) with `distinct()` applied only when active.
- New submitted-at range filter (`RangeDateTimeFilter`) alongside the kept `date_hierarchy`; `list_filter_submit = True` enabled on `OrderAdmin` for range/text widgets.
- New free-text referral-organisation filter (`FieldTextFilter`-style contains search); existing `is_referral_order` boolean flag kept (they compose).
- No model changes. No new dependencies (`unfold.contrib.filters` is already installed). Search behavior unchanged — `^order_number` already covers order-ID lookup (verify only).

## Capabilities

### New Capabilities

- `order-admin-filters`: structured changelist filters for `Order` — autocomplete FK filters (company/rep/both contacts), custom single-select product filter via order items, submitted-at datetime range, free-text referral filter, bottom-placed currency dropdowns, and the exact sidebar ordering above.

### Modified Capabilities

- `crm-admin-registration`: the `Order admin registration with inline items` requirement's `list_filter` value changes (old tuple replaced by the new ordered filter set); everything else in that requirement (list_display, search, autocomplete form fields, inline, computed columns) is unchanged.

## Impact

- Touched code: `ourlives/admin.py` (`OrderAdmin` only, plus ~2 small custom filter classes inline — no new module; extract only if a second admin reuses them); no migrations; no API/stripe/export changes.
- Risk: product JOIN duplication (handled via conditional `distinct()`); free-text referral data stays messy by nature (contains-search degrades gracefully, no cleanup attempted).
- Test surface: admin changelist filter queries per axis + sidebar order assertion + no-duplicate product-filter check.
