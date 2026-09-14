## Context

`ourlives/admin.py` registers 16 `ModelAdmin`s (all on `OurlivesModelAdminBase`), with a single inline: `OrderItemInline(admin.TabularInline)` inside `OrderAdmin`. `core/admin.py` already uses `unfold.admin.StackedInline`, and `INSTALLED_APPS` includes `unfold.contrib.inlines`. FK facts driving the design: `Contact.organization` and `OrganizationAddress.organization` are `CASCADE` (true children); `OrderItem.order` is `CASCADE`; `Rep`/`Country`/type tables are parent-side or shared lookups (wrong inline direction — explored, rejected). `Order.primary_contact`/`invoice_contact` autocomplete targets `Contact`. A prior spec (`unfold-permission-sidebar`) mandates an auto-rendered `available_apps` sidebar via a `navigation.html` template override; current `settings.py` already diverges (Credits group present). Verified against installed `django-unfold 0.97.0` source: main sidebar renders only `SIDEBAR.navigation` groups; the auto app list lives behind the "All applications" drawer; item `permission` defaults to visible when absent; groups have no permission filtering.

## Goals / Non-Goals

**Goals:**
- Edit contacts/addresses on the Organization page and line items on the Order page, fully editable, Unfold-styled.
- Sidebar shows 13 ourlives entries in two groups (operational + collapsible Reference data) plus Credits and Core, each link permission-gated.
- Permission isolation unchanged: no ourlives perms → no ourlives links/data; cross-app users unaffected.

**Non-Goals:**
- Merging lookup tables into a singleton or `TextChoices` (destroys FK integrity, fixtures, M2M).
- Hiding empty group headers for perm-less users (accepted cosmetic limitation; headers only, no data).
- Read-only/history inlines, nested inlines, inline pagination (`per_page`), `show_change_link` (no target pages exist post-unregister).
- Touching `core` admins, `AppSettings`, `StripeEvent`, or the Excel export engine.

## Decisions

- **Unfold inline classes over Django natives.** Unfold docs: natives function but break the design system. Migrate `OrderItemInline` to `unfold.admin.TabularInline`; new inlines use `unfold.admin.StackedInline` (6–7 fields each — Tabular would be unreadable). Alternative (keep Django classes): rejected on visual consistency; precedent exists in `core/admin.py:59`.
- **Stacked + `tab=True` for the two Organization inlines; Tabular (no tab) for OrderItem.** Two stacked inlines make the org page long — Unfold's `tab=True` groups them into tabs. Single inline on Order needs no tab. Alternative (all Tabular): rejected on column count.
- **`extra=0`, no `show_change_link`, `min_num=0`.** No empty-row noise; links would 404 post-unregister. In-inline `autocomplete_fields` kept where targets stay registered (`contact_type`, `country`, `product`).
- **Unregister children (no `@admin.register` for `Contact`/`OrganizationAddress`/`OrderItem`).** Zero-config hiding from sidebar/index/URLs vs curated-nav hiding (keeps URLs/autocomplete but needs `show_all_applications=False` anyway for grouping — no extra benefit). Full-app Excel export unaffected (`apps.get_models()` discovery).
- **Drop `primary_contact`/`invoice_contact` from `OrderAdmin.autocomplete_fields`** (plain selects). Django autocomplete requires a registered target admin. Alternative (keep Contact registered but sidebar-hidden): contradicts the unregister decision and the user's explicit vote; revisit only if contact dropdowns become unwieldy (custom autocomplete view).
- **Full-manual sidebar (`show_all_applications=False`) with four groups** (Our Lives operational, collapsible Reference data, Credits unchanged, Core explicit). Only mechanism producing a collapsible group in Unfold's main sidebar; `get_app_list` pseudo-app tricks only affect the drawer/index. `show_search` stays `True`. Icons reused from each `ModelAdmin.sidebar_icon`. Links use `reverse_lazy("admin:<app>_<model>_changelist")` (docs pattern); settings already uses plain-string links for custom views.
- **Per-item `permission` mandatory for every nav entry** (`has_perm("<app>.view_<model>")` lambdas, same shape as existing `ourlives.admin.can_purchase`). Unfold defaults missing callbacks to visible — without this, perm-less staff see dead links that 403.
- **Retire the `navigation.html` auto-sidebar override** (it exists at `project/templates/unfold/helpers/navigation.html` per the old spec) and return to Unfold's bundled sidebar, since manual `navigation` is non-empty. Admin index page and command search keep working (both driven by `get_app_list`, untouched).

## Risks / Trade-offs

- [Risk] New `ModelAdmin` without a nav entry is sidebar-invisible → Mitigation: registry-coverage test (every registered model ↔ exactly one nav entry) fails loudly.
- [Risk] `Order` contact selects degrade with hundreds of contacts → Mitigation: plain `<select>` now; custom autocomplete view later if painful.
- [Risk] `InvitationCode` pool validation under bulk inline adds (not in scope — no code inline planned) → Mitigation: none needed; noted so a future codes-inline proposal handles atomicity.
- [Risk] `requirements.txt` pins `django-unfold==0.77.1` but installed is `0.97.0` → Mitigation: implementation verifies sidebar/inline APIs against the venv's actual version before coding.
- [Trade-off] Per-model Excel row actions for the three children disappear; parent + full-app exports still cover the data.
- [Trade-off] `LookupAdminTests` changelist loop unaffected (covers country/rep/contacttype/codetype/ordertype only), but admin-behavior tests must be extended for inlines/404s/coverage.

## Migration Plan

No migrations (no model changes). Deploy: code + settings only. Rollback: revert commit; standalone changelists reappear, manual sidebar replaced by previous config. Staff comms: one line — contacts/addresses/items now edited on parent pages; lookups under Reference data.

## Open Questions

- None blocking. Micro-choices at implementation: `tab=True` exact placement, `fields`/`fieldsets` subset per inline, Core group title/icons.
