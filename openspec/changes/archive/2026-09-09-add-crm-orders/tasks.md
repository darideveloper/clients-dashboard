## 1. Models (`ourlives/models.py`, append-only)

- [x] 1.1 Add `generate_order_number()` helper (`OL-` + 6 uppercase alphanumerics) next to `generate_invitation_code`
- [x] 1.2 Add 4 alteration fields: `Organization.assigned_rep` (FK→Rep SET_NULL null/blank `organizations`), `InvitationCode.order` (string FK→`'Order'` PROTECT null/blank `invitation_codes`), `InvitationCode.code_type` (FK→CodeType PROTECT null/blank `invitation_codes`), `InvitationCode.sequence` (PositiveIntegerField null/blank, no validators)
- [x] 1.3 Add `Order` model per spec (order_number UK auto-default, organization/rep PROTECT, contacts PROTECT nullable, `order_types` M2M blank, currencies SET_NULL nullable, bools default False, scan/price Decimal(10,2) nullable, ingestion fields, `is_pilot_order` + `total_agreed_price` properties, `__str__`/`Meta`)
- [x] 1.4 Add `OrderItem` model per spec (order CASCADE `items`, product PROTECT `order_items`, quantity + unit_price required, `line_total` property, `__str__`/`Meta`, no unique-together, no line_total column)

## 2. Migration

- [x] 2.1 Run `makemigrations ourlives` (single migration: Order + OrderItem + 4 alters, auto M2M table) and inspect field/deletion ops
- [x] 2.2 Run `migrate` locally and confirm clean apply

## 3. Tests (`ourlives/tests.py`, append-only)

- [x] 3.1 Add `OrderTests`: auto number + explicit UK + org/rep PROTECT + contacts nullable/PROTECT + M2M add/remove/multi-type + unsaved-instance `is_pilot_order` False (pk guard) + no single-FK field + total price computed/None→0 + currency SET_NULL + no total column
- [x] 3.2 Add `OrderItemTests`: create + line_total + CASCADE + product PROTECT + duplicate lines allowed
- [x] 3.3 Add alteration tests: backwards-compat creation (all new fields None), rep-delete SET_NULL, order/codetype PROTECT, link round-trip
- [x] 3.4 Run full suite (`test ourlives`) + `makemigrations --check` (no missing migration); existing tests untouched and green

## 4. ERD doc fix (`ourlives/docs/crm-erd.md`, doc-only)

- [x] 4.1 Update `orders` block: remove `order_type_id` FK + `is_pilot_order` bool lines, keep junction; annotate `is_pilot_order`/`total_agreed_price`/`line_total` as `@property`; remove `order_types ||--o orders : types` relationship line
