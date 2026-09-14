## Context

`OrderAdmin` (`ourlives/admin.py:185`) currently filters by `order_types`, `rep`, `currency`, `pilot_currency` and three boolean flags. Ops triage needs company/rep/both contacts/product/date-window/referral-org axes. The model already has every field (`organization`, `rep`, `primary_contact`, `invoice_contact`, `currency`, `pilot_currency`, `referral_organisation` CharField, `submitted_at`, reverse `items → product`). `unfold.contrib.filters` is installed (`project/settings.py:45`, Unfold 0.77.1) with `RelatedDropdownFilter`, `AutocompleteSelectFilter`, `RangeDateTimeFilter`, `FieldTextFilter` available. Related admins (`Organization`, `Rep`, `Contact`) already define `search_fields`, satisfying the autocomplete-filter precondition. `list_select_related` already covers all direct FKs; `get_queryset` prefetches `order_types`. Base `ModelAdminUnfoldBase` sets `list_filter_sheet = False` (sidebar rendering) and does not set `list_filter_submit`.

## Goals / Non-Goals

**Goals:**
- One ordered `OrderAdmin.list_filter` tuple implementing the agreed sidebar: company → rep → both contacts → product → date range → referral text → existing flags → both currencies last.
- Autocomplete-backed FK filters for unbounded relations; plain dropdowns for the ~12-row currency tables.
- Custom single-select product filter over the `items → product` reverse join (all products), `distinct()` only when active.
- Range-datetime filtering on `submitted_at` with submit button; `date_hierarchy` retained.

**Non-Goals:**
- No model/serializer/API/stripe/export changes; no migrations.
- No referral-data cleanup (typos/case variants stay; contains-search tolerates them).
- No generic filter framework in `project/admin_base.py`; no changes to other admins.
- No multi-select product filter; no pilot-currency removal.

## Decisions

**1. Autocomplete filters for `organization`, `rep`, `primary_contact`, `invoice_contact` — over plain `RelatedDropdownFilter`.**
Plain dropdowns render every option on page load and degrade as clients/contacts grow; autocomplete queries on type. Precondition (related admin `search_fields`) is already met for all three models, so this is config-only. Alternative (plain dropdowns) rejected on scale grounds.

**2. Two separate contact filters — over one combined `Q(primary) | Q(invoice)` filter.**
User decision. Separate filters are zero-custom-code (two tuple entries), semantics are unambiguous ("primary is X" vs "invoice is Y"), and they compose via AND. A combined OR filter would need a custom class for marginal UX gain. Revisit only if staff complain about two-step contact lookup.

**3. Custom `SimpleListFilter`/`DropdownFilter` subclass for product — no stock option fits.**
`AutocompleteSelectFilter` requires a direct FK/M2M on `Order`; product is reachable only via reverse `items__product`, so a small custom class with `lookups()` over all `Product` rows (ordered by name) and `queryset()` filtering `items__product__id` is the only path. Single-select per user decision; all products (not just `active`) per user decision — history lookup beats list tidiness. Alternative (adding a direct M2M `Order.products`) rejected: schema change for an admin nicety.

**4. `RangeDateTimeFilter` on `submitted_at` + `list_filter_submit = True` on `OrderAdmin` (not the base class).**
Submit button is required for range/text widgets to apply cleanly. Scoped to `OrderAdmin` so no other admin's sidebar behavior changes. `date_hierarchy` kept — drill-down and precise range serve different tasks.

**5. `FieldTextFilter`-style contains search for `referral_organisation` — over distinct-value dropdown.**
Free-text column with inevitable variants; a distinct dropdown amplifies noise and needs maintenance. Contains-search degrades gracefully. Existing `is_referral_order` boolean stays; the two compose ("is referral" AND "name contains").

**6. Both currency dropdowns last, plain `RelatedDropdownFilter`, active-only.**
~12 rows: dropdown is cheap and scannable, autocomplete is pointless overhead. Position is just tuple order — currencies occupy the final two entries (`currency`, then `pilot_currency`). `pilot_currency` kept per user decision. Active-only per user decision (unlike products, where history lookup matters, currency history lookup was deemed unneeded — keeps the tiny list tidy).

**7. Custom filter classes live in `ourlives/admin.py` next to `OrderAdmin` — over a new `admin_filters.py` module.**
Only two small classes (product dropdown; referral text only if `FieldTextFilter` needs a thin subclass for the parameter name). One new file for ~30 lines fails YAGNI; extract only if a second admin reuses them.

## Risks / Trade-offs

- [Product JOIN duplicates] → `queryset()` returns `.distinct()` **only when the product parameter is active**; unconditional `distinct()` would tax every changelist load. Test asserts correct total count with the filter on.
- [Unfold 0.77.1 vs latest-docs drift] → verify each imported filter name exists in `venv` (`RangeDateTimeFilter`, `AutocompleteSelectFilter`, `FieldTextFilter` confirmed present) at implementation start; pin to what ships, not what docs describe.
- [`list_filter` tuple order IS the UI order] → any future edit must preserve the agreed sequence; the spec's order scenario guards regressions.
- [Referral text can never be exhaustive] → documented as accepted limitation; no dedup/migration attempted.
- [Filter count vs sidebar length] → 12 entries in a sidebar is long but `list_filter_sheet = False` keeps it scrollable; flags stay collapsed under their headers. If staff complain, a follow-up can demote `hcaptcha_verified` — not this change.
- [Existing tests pin the old `list_filter`] → current tests may assert the old tuple; implementation must update them alongside the admin change (covered by tasks 4.3).
