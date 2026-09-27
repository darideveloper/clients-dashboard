## MODIFIED Requirements

### Requirement: Order currencies and commercial fields
The system SHALL provide on `Order`: `currency` (ForeignKey to `Currency`, on_delete=SET_NULL, null=True, blank=True, related_name="orders"), `pilot_currency` (ForeignKey to `Currency`, on_delete=SET_NULL, null=True, blank=True, related_name="pilot_orders"), `is_upgrade_from_pilot` (BooleanField default False), `is_referral_order` (BooleanField default False), `referral_organisation` (CharField max_length=255, null=True, blank=True), `po_number` (CharField max_length=100), `number_of_scans` (PositiveIntegerField null=True, blank=True), `cost_per_scan` (DecimalField max_digits=10, decimal_places=2, null=True, blank=True), `additional_information` (TextField blank=True), `ip_address` (GenericIPAddressField null=True, blank=True), `form_entry_key` (CharField max_length=100, null=True, blank=True), `submitted_at` (DateTimeField auto_now_add=True), `hcaptcha_verified` (BooleanField default False), `tokens_used` (PositiveIntegerField default 0, tracking invitation codes created via webhook submissions), and `total_agreed_price` as a `@property` returning `number_of_scans * cost_per_scan`, or `Decimal("0")` when either is None. No `total_agreed_price` database column SHALL exist.

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

#### Scenario: tokens_used defaults to zero

- **WHEN** an Order is created without specifying `tokens_used`
- **THEN** `tokens_used` is `0`

#### Scenario: tokens_used accumulates webhook-created codes

- **WHEN** a webhook submission creates invitation codes for the order
- **THEN** `tokens_used` increases by the number of codes created