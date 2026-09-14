## Why

Staff can't find rows by the identifiers they actually type (order/contact details, invitation-code order linkage, Stripe audit IDs), while several categorical fields lack one-click filters. At hundreds of rows the admin is still fast, so this is the right moment to make the search bar maximally useful and push everything categorical to `list_filter` before scale makes wide `OR` scans painful.

## What Changes

- Expand `search_fields` only with same-table text and high-cardinality FK traversals (no M2M, no double-hop `items__product__name` — cut as nice-to-have).
- Apply `^` (`istartswith`) prefixes to unique codes/numbers (`code`, `order_number`, `po_number`, `iso2/iso3`) and keep bare `icontains` for human names/descriptions; add `search_help_text` on heavy admins (`Order`, `InvitationCode`, `StripeEvent`).
- Add three missing filters instead of search duplicates: `InvitationCodeAdmin.list_filter += code_type`, `OrderAdmin.list_filter += pilot_currency`, `OrganizationAdmin.list_filter = (assigned_rep,)`.
- Deliberately skip search duplicates where a filter already exists (`contact_type`, `order_types`, `countries`, `currency` on Product/Order, `country` on addresses).
- Fix gaps: `OrganizationAddress` gains `line2`; `StripeEventAdmin` gains its first `search_fields` (`stripe_event_id`, `source`, `presentment_currency`); `Order`/`InvitationCode` gain linkage traversals (`primary/invoice_contact`, `order__order_number`, `code_type__`); `Contact` gains same-table `phone`.
- No model/schema changes, no autocomplete changes (all targets already expose `search_fields`), no export/permission changes.

## Capabilities

### New Capabilities
- `admin-search-filter-tuning`: cross-cutting search/filter conventions for ourlives admin — exact per-admin `search_fields` with prefixes, `search_help_text`, the three new filters, and the skip-in-favor-of-filter rules.

### Modified Capabilities
- `ourlives-lookup-admin`: `Country`/`ContactType`/`CodeType`/`OrderType` search expansion (descriptions, `^` prefixes), `InvitationCode` search + `code_type` filter, `Organization` filter/search update (`Rep` unchanged — already optimal).
- `crm-admin-registration`: `Currency`/`Product`/`Contact`/`OrganizationAddress`/`Order`/`OrderItem` search expansion, `Order.pilot_currency` filter, skip-M2M rules.

## Impact

- Touched: `ourlives/admin.py` only (plus `ourlives/tests.py` admin assertions). No migrations, no API, no Stripe logic, no export logic.
- Risk: low — admin-only. Search widens `OR` clauses slightly; guideline ~5–8 fields/admin and ≤2 FK JOINs, zero M2M `DISTINCT`. Documented exception: `Order` uses 11 fields across 4 single-hop JOINs (org, rep, two contacts) — still cheap at hundreds of rows. Autocomplete backends unaffected.
