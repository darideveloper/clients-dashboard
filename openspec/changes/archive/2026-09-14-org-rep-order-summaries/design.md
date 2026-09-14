## Context

`Organization` (`ourlives/models.py:34-50`) has only `name`, `description`, `assigned_rep`; `Rep` (`models.py:349-360`) has only `first_name`, `last_name`, `email`. No calculated fields exist anywhere (verified by repo-wide grep). The raw material exists on `Order` — `organization`/`rep` FKs with `related_name="orders"`, `submitted_at`, `total_agreed_price` (`number_of_scans × cost_per_scan`, null→0) — and on `OrderItem` (`line_total = quantity × unit_price`). Admin precedent: `OrderAdmin` already uses `get_queryset` + `list_select_related` + readonly `@admin.display` methods; `AppSettingsAdmin` uses `fieldsets` sections with readonly displays.

Two money concepts come from two sections of the external Formidable order form: commercial terms (scans × price/scan → agreed) and product picker (qty × frozen unit price → items). Two currency FKs on `Order` (`currency` for non-pilot, `pilot_currency` for pilot) mirror two form pickers. `OrderItem` carries no currency of its own. `Currency.exchange_rate` exists but is never consumed in code.

## Goals / Non-Goals

**Goals:**
- Five read-only summaries per Organization and Rep, correct across mixed currencies.
- List view: sortable counts/dates, honest money display, no N+1.
- Detail view: self-explanatory "Order summary" section (labels + help texts).

**Non-Goals:**
- No currency conversion / USD estimates (rates unmaintained).
- No stored columns, signals, or migrations.
- No MXN fixture row (separate change); no Excel export integration.
- No change to Order/OrderItem write paths or to `total_agreed_price`/`line_total` semantics.

## Decisions

1. **Hybrid annotation + `@property` (over property-only or denormalized columns).**
   Model `@property`s return per-currency mappings for single-object use (detail view, shell, future reuse). Admin `get_queryset()` annotates `Count`/`Max` for the sortable columns, and each changelist page issues a constant number of supplementary grouped queries (by object × currency) for the money breakdowns — no per-row queries. Display methods read the precomputed data when present, fall back to the property otherwise. Rejected property-only (N+1 in list, unsortable) and stored columns (invalidation system for 5 numbers the DB computes on read).

2. **Per-currency breakdown strings (over raw single sum or converted total).**
   One `SUM` per org mixes currencies into a meaningless number; conversion depends on unmaintained 2dp rates. Breakdown (`USD 1,750.00 · EUR 800.00`, codes alphabetical) is always correct and needs no rate infrastructure. Consequence, accepted: money columns are not sortable; `order_count` and `last_order_date` are (via `admin_order_field`).

3. **Currency attribution: order currency first on both sides (over always-product / strictly-one-FK).**
   `OrderItem.unit_price` is a snapshot with no currency FK. The order is the transaction, so its currency wins; the line's `Product.currency` covers null-order-currency cases (e.g. after a `Currency` delete via `SET_NULL`). Agreed amounts mirror this: `Order.currency`, then `Order.pilot_currency`, then `Uncategorized`. Documented in help text.

4. **"Uncategorized" bucket for currency-less amounts (over blocking deletes).**
   Changing `SET_NULL` → `PROTECT` on currency FKs is a behavior change with its own migration; out of scope. Amounts with no resolvable currency render under an `Uncategorized` bucket rather than vanishing.

5. **Field names/descriptions as user-facing contract.**
   `order_count` / `agreed_scans_total` / `catalog_items_total` / `combined_total` (`= agreed + items`, per currency) / `last_order_date`, each with a help text stating formula + form origin + currency behavior. Money help texts explicitly note pilots-included and null→0.

6. **Unfold-native rendering, no template overrides.**
   `fieldsets` + `readonly_fields` (AppSettingsAdmin precedent); Unfold renders each fieldset as a section. List columns are `@admin.display` methods, same pattern as `total_agreed_price_display`.

## Risks / Trade-offs

- [Risk] `Sum` of `number_of_scans × cost_per_scan` needs an arithmetic expression inside the aggregate; null handling must reproduce the property's null→0 → Mitigation: dedicated tests comparing annotation vs property on identical fixtures, including all-null and mixed-null rows.
- [Risk] Money columns unsortable may surprise users → Mitigation: column help/label makes clear it's a breakdown; counts and dates remain sortable.
- [Risk] Product currency edited after orders exist shifts historical item attribution under the fallback path → Mitigation: fallback only triggers when order currency is null; documented; accepted as edge case.
- [Risk] Breakdown string grows with many currencies per org → Mitigation: compact `CODE amount` format, alphabetical; page sizes unchanged.
- [Risk] Excel export won't include summaries → Mitigation: explicitly out of scope, noted in proposal; export util reads concrete fields.

## Migration Plan

No migration. Deploy = code + tests. Rollback = revert; no data to clean (nothing stored).

## Open Questions

None — all gaps closed in exploration (item-currency rule, orphan bucket, no conversion, MXN later, Rep gets all five fields).
