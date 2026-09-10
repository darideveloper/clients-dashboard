## Context

`ourlives/admin.py` registers 10 of 16 models as `OurlivesModelAdminBase` (Unfold + `OurlivesExportMixin`). The six Phase-2/3 models (`Currency`, `Product`, `Contact`, `OrganizationAddress`, `Order`, `OrderItem`) exist in `models.py` with migrations `0009–0012` and model tests, but are invisible in admin. Existing patterns to mirror: lookup admins (`ContactType`/`CodeType`/`OrderType`/`Country`) and FK-heavy `InvitationCodeAdmin` (filters + autocomplete + `list_editable`). `AGENTS.md` fixes the base class — no alternative allowed.

## Goals / Non-Goals

**Goals:**
- All six models browsable/searchable/filterable/exportable in Unfold admin with zero migrations.
- `Order` as the CRM hub: M2M `order_types` editable via `filter_horizontal`, items visible inline, computed `total_agreed_price` / `is_pilot_order` shown readonly.
- Autocomplete everywhere an FK/M2M to Org/Rep/Contact/Currency/Product/OrderType appears, so changelists stay fast.

**Non-Goals:**
- No model/field/queryset logic changes; no new permissions; no `Country`-style add/delete lockdown (all six stay fully editable).
- No admin dashboard widgets, custom actions, or CSV import — export already inherited.

## Decisions

- **One admin class per model + `OrderItemInline(TabularInline)` inside `Order`, AND standalone `OrderItemAdmin`.** Rationale: inline covers order entry; standalone covers audit + per-model Excel export (every other model has one). Alternative (inline-only) rejected — breaks the one-admin-per-model export convention.
- **Readonly computed displays via `@admin.display`, not model methods.** `Order.total_agreed_price` / `is_pilot_order`, `OrderItem.line_total` mirror `InvitationCodeAdmin.usage_percentage` / `AppSettingsAdmin.tokens_*_display`. Keeps formatting in admin layer.
- **All `Order` concrete fields editable; only computed displays readonly.** Per user decision: `order_number`, `submitted_at`, `ip_address`, `form_entry_key` stay editable. `total_agreed_price_display` / `is_pilot_order_display` are readonly `@admin.display` columns (properties cannot be edited).
- **Icons:** `Currency=payments`, `Product=inventory_2`, `Contact=contact_mail`, `OrganizationAddress=location_on`, `Order=receipt`, `OrderItem=list_alt` (Material symbols, matching existing `globe/person/contacts/sell/shopping_bag` style).
- **`Currency.countries` M2M shown with `filter_horizontal` + `list_filter`.** Cheapest usable M2M widget; no through model exists so no inline needed.
- **Autocomplete dependency order:** define `search_fields` on `Currency/Product/Contact/Order` first — they back `autocomplete_fields` on `Product/Contact/OrganizationAddress/Order/OrderItem`. No circularity (all point backwards).

## Risks / Trade-offs

- [Risk] `Order` changelist N+1 over 6 FKs + M2M → Mitigation: `list_select_related` plus a `get_queryset` override with `prefetch_related("order_types")`; autocomplete avoids dropdown blowup.
- [Risk] `list_editable(active)` + `list_display_links` conflict → Mitigation: links on `code`/`name` only, never on the editable `active` column (existing lookup pattern).
- [Risk] Inline + `PROTECT` on `OrderItem.product` confusing on delete → Mitigation: default Django PROTECT message; no custom handling.

## Migration Plan

Admin-only: edit `ourlives/admin.py`, extend `ourlives/tests.py`. No migration. Rollback = revert commit. Verify with `python manage.py check`, `runtests ourlives`, manual `/admin/ourlives/<model>/` smoke per model.
