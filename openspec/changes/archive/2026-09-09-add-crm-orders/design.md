## Context

`ourlives/models.py` currently holds 14 models: the original 5 (`Project`, `Organization`, `InvitationCode`, `AppSettings`, `StripeEvent`) plus phase-2 lookups/parties (`Country`, `Rep`, `ContactType`, `CodeType`, `OrderType`, `Currency`, `Product`, `Contact`, `OrganizationAddress`). The ERD (`ourlives/docs/crm-erd.md`) describes a 14-table aspirational CRM whose final two tables — `orders` and `order_items` — have no Django models yet. `InvitationCode.order` / `Organization.assigned_rep` links are also missing, leaving rep assignment and code→order traceability unrepresentable.

Global conventions (enforced): calculated fields are `@property` (never DB columns, per `AppSettings.tokens_*` pattern); `Order↔OrderType` is M2M-only (drop the single-`order_type_id` FK from the ERD); PROTECT on business FKs; `unique=True` on natural keys; `related_name`s everywhere; no admin/views/serializers in this change; never touch `project/admin_base.py`.

Explore-phase decisions (locked): `order_number` gets an auto-default callable (`OL-XXXXXX`, overridable); `primary_contact`/`invoice_contact` are nullable PROTECT FKs; `total_agreed_price` returns `Decimal("0")` when inputs are missing; ERD is corrected in this change.

## Goals / Non-Goals

**Goals:**
- `Order` + `OrderItem` models covering every Formidable V2 order-form field, with M2M typing and derived-money properties.
- Four additive, nullable, backwards-compatible link fields (`Organization.assigned_rep`, `InvitationCode.order`, `InvitationCode.code_type`, `InvitationCode.sequence`).
- One migration; append-only model tests proving M2M behavior, both money properties, delete rules, and backwards compat.
- ERD `orders` block corrected to match M2M-only reality.

**Non-Goals:**
- Admin registration, views, serializers, checkout/business logic, queryset analytics (`Organization`/`Rep` totals stay future `@property` work).
- Fixture data for orders; timestamp fields (`created_at`/`updated_at` — no model in this codebase has them).
- Cross-organization contact validation; "at least one currency" constraint; single-primary-address-style constraints.

## Decisions

1. **M2M-only `Order.order_types`, no `order_type_id` column.** Rationale: orders can be Pilot+Referral simultaneously (frmrules-driven junction); a single FK cannot represent upgrades/referrals. Alternative (FK + junction, as ERD draws) rejected — dual sources of truth for "what type is this order". Django auto through table `ourlives_order_order_types`; `related_name="orders"` on the M2M.
2. **`is_pilot_order` as `@property` := False if `self.pk is None` else `self.order_types.filter(code="pilot").exists()`.** Rationale: global derived-field rule; keys on the stable fixture code (`OrderType` pk 1 = `pilot`). The pk guard is mandatory — touching any M2M manager on an unsaved instance raises `ValueError` (no id yet), so the property must short-circuit before the filter. Alternative (DB bool + signal sync) rejected — sync drift.
3. **Money as `@property`, `Decimal("0")` fallback.** `total_agreed_price` = `number_of_scans * cost_per_scan`, `line_total` = `quantity * unit_price`; when either scan input is None → `Decimal("0")` (explore decision: always numeric). `unit_price`/`quantity` on OrderItem are required so `line_total` needs no fallback. DecimalField spec `(max_digits=10, decimal_places=2)` matches `Product.unit_price`/`AppSettings` pricing.
4. **Delete-rule matrix.** `organization`/`rep`/`primary_contact`/`invoice_contact`/`product` → PROTECT (business records must not vanish under an order; mirrors `InvitationCode` pattern). `currency`/`pilot_currency` → SET_NULL nullable (currency list is mutable reference data). `OrderItem.order` → CASCADE, `Contact.organization` precedent (line items have no life without their order). `Organization.assigned_rep` → SET_NULL nullable (rep leaves ≠ org deleted). `InvitationCode.order`/`code_type` → PROTECT nullable (code must not dangle, but old codes predate orders).
5. **`order_number`: `CharField(max_length=50, unique=True, default=generate_order_number)`.** Rationale: explore decision for auto-default; `OL-` + 6 uppercase alphanumerics mirrors `OL-82`-style readability while staying collision-safe; overridable for Formidable `field_be8ml` imports. Alternative (required manual, no default) rejected — ingestion path has no number at submit time.
6. **Nullable contacts.** Rationale: explore decision — orders can arrive before contacts are keyed. PROTECT still guards deletion once linked. No cross-org validation in this phase (YAGNI; form guarantees it today).
7. **No `(order, product)` uniqueness.** Rationale: same product may legitimately appear on two lines (e.g. different negotiated `unit_price` snapshots); constraint would block real data for zero benefit.
8. **`InvitationCode.sequence`: plain `PositiveIntegerField(null=True, blank=True)`, no validators.** Rationale: ERD explicitly says "no DB constraint"; range 1–20 is a frontend concern.
9. **Forward reference `'Order'` (string FK) on `InvitationCode.order`.** Rationale: `Order` is appended after `InvitationCode` in `models.py`; string ref avoids reordering the file and keeps the diff append-only.
10. **`related_name` map (all FKs/M2M covered):** `organization.orders`, `rep.orders`, `contact.primary_orders` / `contact.invoice_orders`, `currency.orders` / `currency.pilot_orders`, `ordertype.orders` (M2M reverse), `order.items`, `product.order_items`, `rep.organizations`, `order.invitation_codes`, `codetype.invitation_codes`. Rationale: distinct reverses are mandatory for the dual FK pairs; names follow existing plural style (`contacts`, `addresses`, `products`, `currencies`).
11. **Single migration, append-only edits.** Rationale: `Order` deps all exist; `InvitationCode` alter depends on `Order` — one `makemigrations` emits correct ordering. `models.py`/`tests.py` edited by append only; existing `InvitationCode.organization` missing-`related_name` wart left untouched (out of scope).
12. **Field-type specifics:** `po_number` required `CharField(max_length=100)` (ERD: required); `referral_organisation` nullable `CharField(max_length=255)` (British spelling kept — matches Formidable `field_t6li52` label); `additional_information` `TextField(blank=True)`; `ip_address` `GenericIPAddressField(null=True, blank=True)`; `form_entry_key` `CharField(max_length=100, null=True, blank=True)` non-unique (Formidable keys are unique in practice but unenforced — YAGNI); `submitted_at` `DateTimeField(auto_now_add=True)`; `number_of_scans` nullable `PositiveIntegerField`; `cost_per_scan` nullable `DecimalField(10,2)`; `quantity` required `PositiveIntegerField`; `__str__`: `Order` → `order_number`, `OrderItem` → `f"{quantity}× {product} on {order}"`.

## Risks / Trade-offs

- [Risk] `is_pilot_order` keys on `code="pilot"`; a fixture rename silently flips all pilot flags → Mitigation: `OrderType.code` is a unique natural key treated as immutable; phase-1 fixture test already pins `pk 1 = pilot`.
- [Risk] `total_agreed_price == Decimal("0")` is ambiguous with a genuine zero-value order → Mitigation: accepted in explore; callers needing the distinction check `number_of_scans`/`cost_per_scan` directly.
- [Risk] Auto `order_number` collision under concurrency → Mitigation: `unique=True` raises IntegrityError on the astronomically unlikely collision; retry-at-submit is a later concern, not this change.
- [Risk] Nullable contacts allow contactless orders permanently → Mitigation: follow-up form/admin validation can enforce later; DB stays permissive by design.
- [Risk] String FK `'Order'` breaks if model renamed → Mitigation: rename would touch the whole file anyway; tests fail loudly.

## Open Questions

None — all explore-phase questions resolved. Remaining judgments above are documented assumptions for review.
