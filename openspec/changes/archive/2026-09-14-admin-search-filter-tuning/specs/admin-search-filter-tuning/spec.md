## ADDED Requirements

### Requirement: Project admin search expansion
`ProjectAdmin` in `ourlives/admin.py` SHALL use `search_fields = ("name", "description")` with no `list_filter` (nothing categorical to filter on).

#### Scenario: Find project by description
- **WHEN** a staff user searches a description fragment in `/admin/ourlives/project/`
- **THEN** matching projects are returned alongside name matches

### Requirement: Organization admin search and rep filter
`OrganizationAdmin` SHALL use `search_fields = ("name", "description", "assigned_rep__first_name", "assigned_rep__last_name", "assigned_rep__email")` and `list_filter = ("assigned_rep",)`.

#### Scenario: Find org by rep or description
- **WHEN** a staff user searches a rep email fragment or description word in `/admin/ourlives/organization/`
- **THEN** organizations with matching rep or description are returned
- **WHEN** a staff user clicks an `assigned_rep` filter choice
- **THEN** only organizations of that rep are shown

### Requirement: StripeEvent admin becomes searchable
`StripeEventAdmin` SHALL use `search_fields = ("=stripe_event_id", "source", "presentment_currency")`, keep `list_filter = ("presentment_currency",)`, keep all read-only/no-add/no-change/no-delete permissions, and set `search_help_text` naming the three covered fields.

#### Scenario: Audit-log grep by event id
- **WHEN** a staff user pastes a full `stripe_event_id` into `/admin/ourlives/stripeevent/` search
- **THEN** the exact event row is returned
- **WHEN** a staff user searches a `source` or currency fragment
- **THEN** matching events are returned

### Requirement: Search conventions and skip rules
All ourlives admins SHALL follow: `^` prefix for unique codes/numbers (`code`, `order_number`, `po_number`, `iso2/iso3`, `order__order_number`), `=` for `stripe_event_id`, bare `icontains` for names/descriptions/phones; `search_help_text` on `Order`, `InvitationCode`, `StripeEvent`; zero M2M fields in any `search_fields` (use existing `list_filter` for `contact_type`, `order_types`, `countries`, `currency`, `country` axes); zero double-hop traversals (no `items__product__name`).

#### Scenario: Conventions hold across admins
- **WHEN** the test suite inspects every ourlives `ModelAdmin.search_fields`
- **THEN** no entry traverses a `ManyToManyField` or spans two `__` hops, and every `^`/`=`-prefixed entry resolves to a real field
