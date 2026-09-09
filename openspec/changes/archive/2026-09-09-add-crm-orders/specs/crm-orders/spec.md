## ADDED Requirements

### Requirement: Order model core identity and party links

The system SHALL provide an `Order` model with `order_number` (CharField max_length=50, unique=True, default=`generate_order_number` producing `OL-XXXXXX` uppercase alphanumerics, overridable), `organization` (ForeignKey to `Organization`, on_delete=PROTECT, related_name="orders"), `rep` (ForeignKey to `Rep`, on_delete=PROTECT, related_name="orders"), `primary_contact` (ForeignKey to `Contact`, on_delete=PROTECT, null=True, blank=True, related_name="primary_orders"), `invoice_contact` (ForeignKey to `Contact`, on_delete=PROTECT, null=True, blank=True, related_name="invoice_orders"), `__str__` returning `order_number`, and `Meta` ordering by `order_number` with `verbose_name`/`verbose_name_plural` matching existing model style.

#### Scenario: Create order with auto-generated number

- **WHEN** an Order is created with organization, rep, required `po_number`, and no explicit `order_number`
- **THEN** it persists with a unique `order_number` starting with `OL-` and `str()` returns that number

#### Scenario: Explicit order number respected

- **WHEN** an Order is created with `order_number="OL-82"`
- **THEN** it persists verbatim and a second Order with `order_number="OL-82"` is rejected with an integrity error

#### Scenario: Organization is protected

- **WHEN** an Organization with linked Orders is deleted
- **THEN** the database raises ProtectedError and the Organization survives

#### Scenario: Rep is protected

- **WHEN** a Rep with linked Orders is deleted
- **THEN** the database raises ProtectedError and the Rep survives

#### Scenario: Contacts are nullable and protected

- **WHEN** an Order is created with required organization/rep/`po_number` but no contacts
- **THEN** it persists with `primary_contact` and `invoice_contact` None
- **WHEN** a Contact linked as `primary_contact` is deleted
- **THEN** the database raises ProtectedError and the Contact survives

### Requirement: Order typing via M2M only

The system SHALL link `Order` to `OrderType` via `order_types` (ManyToManyField to `OrderType`, related_name="orders", blank=True) with NO single-`order_type` ForeignKey column, and SHALL expose `is_pilot_order` as a `@property` returning False when `self.pk is None`, otherwise `self.order_types.filter(code="pilot").exists()` (False for unsaved or untyped orders).

#### Scenario: M2M add marks pilot

- **WHEN** the `pilot` OrderType is added to an Order's `order_types`
- **THEN** `is_pilot_order` returns True

#### Scenario: M2M remove clears pilot

- **WHEN** the `pilot` OrderType is removed from an Order's `order_types`
- **THEN** `is_pilot_order` returns False

#### Scenario: Multiple types coexist

- **WHEN** both `pilot` and `standard` OrderTypes are added to one Order
- **THEN** the Order has two types and `is_pilot_order` returns True

#### Scenario: No single-FK column exists

- **WHEN** the Order model fields are inspected
- **THEN** no `order_type` / `order_type_id` concrete field exists

### Requirement: Order currencies and commercial fields

The system SHALL provide on `Order`: `currency` (ForeignKey to `Currency`, on_delete=SET_NULL, null=True, blank=True, related_name="orders"), `pilot_currency` (ForeignKey to `Currency`, on_delete=SET_NULL, null=True, blank=True, related_name="pilot_orders"), `is_upgrade_from_pilot` (BooleanField default False), `is_referral_order` (BooleanField default False), `referral_organisation` (CharField max_length=255, null=True, blank=True), `po_number` (CharField max_length=100), `number_of_scans` (PositiveIntegerField null=True, blank=True), `cost_per_scan` (DecimalField max_digits=10, decimal_places=2, null=True, blank=True), `additional_information` (TextField blank=True), `ip_address` (GenericIPAddressField null=True, blank=True), `form_entry_key` (CharField max_length=100, null=True, blank=True), `submitted_at` (DateTimeField auto_now_add=True), `hcaptcha_verified` (BooleanField default False), and `total_agreed_price` as a `@property` returning `number_of_scans * cost_per_scan`, or `Decimal("0")` when either is None. No `total_agreed_price` database column SHALL exist.

#### Scenario: Total agreed price computed

- **WHEN** an Order has `number_of_scans=500` and `cost_per_scan="2.50"`
- **THEN** `total_agreed_price` equals `Decimal("1250.00")`

#### Scenario: Total agreed price missing inputs returns zero

- **WHEN** an Order has `number_of_scans` None (or `cost_per_scan` None)
- **THEN** `total_agreed_price` equals `Decimal("0")`

#### Scenario: Currency delete sets null

- **WHEN** a Currency linked as `Order.currency` (or `pilot_currency`) is deleted
- **THEN** the Order survives with that field None (SET_NULL, no ProtectedError)

#### Scenario: No total column exists

- **WHEN** the Order model fields are inspected
- **THEN** no `total_agreed_price` concrete field exists

### Requirement: OrderItem model

The system SHALL provide an `OrderItem` model with `order` (ForeignKey to `Order`, on_delete=CASCADE, related_name="items"), `product` (ForeignKey to `Product`, on_delete=PROTECT, related_name="order_items"), `quantity` (PositiveIntegerField), `unit_price` (DecimalField max_digits=10, decimal_places=2), `line_total` as a `@property` returning `quantity * unit_price`, `__str__` mentioning quantity, product and order, and `Meta` with `verbose_name`/`verbose_name_plural` matching existing model style and no `ordering` (matching the `InvitationCode`/`StripeEvent` precedent for models without a natural sort key). No uniqueness constraint SHALL span (`order`, `product`); no `line_total` database column SHALL exist.

#### Scenario: Create order item and line total

- **WHEN** an OrderItem is created with quantity=2 and unit_price="3995.00"
- **THEN** it persists and `line_total` equals `Decimal("7990.00")`

#### Scenario: Order delete cascades to items

- **WHEN** an Order with items is deleted (with no PROTECT-blocking InvitationCodes)
- **THEN** its OrderItems are deleted too (CASCADE)

#### Scenario: Product is protected

- **WHEN** a Product with linked OrderItems is deleted
- **THEN** the database raises ProtectedError and the Product survives

#### Scenario: Duplicate product lines allowed

- **WHEN** two OrderItems with the same order and product are created
- **THEN** both persist (no integrity error)

### Requirement: Additive CRM link alterations

The system SHALL add four nullable, backwards-compatible fields: `Organization.assigned_rep` (ForeignKey to `Rep`, on_delete=SET_NULL, null=True, blank=True, related_name="organizations"), `InvitationCode.order` (ForeignKey to `Order`, on_delete=PROTECT, null=True, blank=True, related_name="invitation_codes"), `InvitationCode.code_type` (ForeignKey to `CodeType`, on_delete=PROTECT, null=True, blank=True, related_name="invitation_codes"), `InvitationCode.sequence` (PositiveIntegerField null=True, blank=True, no validators). All existing creation patterns (Organization without rep; InvitationCode without order/code_type/sequence) SHALL keep working unchanged, and existing `InvitationCode` token-pool `save()`/`clean()` behavior SHALL be unaffected.

#### Scenario: Backwards-compatible creation

- **WHEN** an Organization is created with only a name, and an InvitationCode with only project/organization/max_use
- **THEN** both persist with `assigned_rep`, `order`, `code_type`, `sequence` all None

#### Scenario: Rep delete sets null on organization

- **WHEN** a Rep assigned to an Organization is deleted (with no PROTECT-blocking Orders)
- **THEN** the Organization survives with `assigned_rep` None

#### Scenario: Order and CodeType are protected from InvitationCode side

- **WHEN** an Order (or CodeType) linked from an InvitationCode is deleted
- **THEN** the database raises ProtectedError and the linked row survives

#### Scenario: Link fields are settable

- **WHEN** an InvitationCode is created with an order, a code_type and sequence=3
- **THEN** all three persist and round-trip
