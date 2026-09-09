## Why

The CRM has all lookup and party models (Country, Currency, Product, Contact, Rep, OrderType, CodeType) but no way to record a customer order — the core sales-ingestion record from the Formidable Ourlens Order Form V2. Without `Order`/`OrderItem`, orders live outside the database and `InvitationCode.order` / rep assignment have nothing to point at.

## What Changes

- New `Order` model: `order_number` (UK, auto-generated `OL-XXXXXX`, overridable), `organization`/`rep`/`primary_contact`/`invoice_contact` FKs (PROTECT; contacts nullable), `order_types` M2M to `OrderType` (only link, no single-FK column), `currency`/`pilot_currency` FKs (SET_NULL, nullable), `is_pilot_order` + `total_agreed_price` as `@property` (never DB columns), `is_upgrade_from_pilot`/`is_referral_order`/`hcaptcha_verified` bools (default False), `referral_organisation`/`po_number`/`additional_information`/`ip_address`/`form_entry_key`/`submitted_at` form-ingestion fields, `number_of_scans`/`cost_per_scan` (nullable; property returns `Decimal("0")` when either is None).
- New `OrderItem` model: `order` FK (CASCADE), `product` FK (PROTECT), `quantity`/`unit_price`, `line_total` as `@property`.
- Additive nullable alterations (backwards-compatible, no existing test changes): `Organization.assigned_rep` FK→Rep (SET_NULL), `InvitationCode.order` FK→Order (PROTECT), `InvitationCode.code_type` FK→CodeType (PROTECT), `InvitationCode.sequence` PositiveIntegerField (null/blank, no range validators).
- One migration + model tests (M2M add/remove, both properties, nullable-alteration backwards-compat).
- Doc fix: `ourlives/docs/crm-erd.md` `orders` block updated to M2M-only (drop `order_type_id` FK + `is_pilot_order` bool column, mark money fields `@property`).

## Capabilities

### New Capabilities

- `crm-orders`: Order and OrderItem models, the four additive CRM link fields, and their DB-behavior contract (delete rules, uniqueness, derived properties, backwards compatibility).

### Modified Capabilities

(none — all alterations are additive-nullable; no existing spec requirement changes)

## Impact

- Touches: `ourlives/models.py` (append 2 models + 4 fields), one new migration, `ourlives/tests.py` (append-only), `ourlives/docs/crm-erd.md` (doc-only correction).
- Does NOT touch: `project/admin_base.py`, admin, views, serializers, business logic, fixtures, existing tests.
- Backwards-compatible: existing rows unaffected (new columns all nullable); `InvitationCode.save()/clean()` token-pool behavior unchanged.
