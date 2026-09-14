## Context

`project/settings.py` holds a manual 4-group `UNFOLD["SIDEBAR"]["navigation"]` (Our Lives: 10 items; collapsible Reference data: 6; Credits; Core), each model item carrying a `reverse_lazy` changelist link, its `ModelAdmin.sidebar_icon`, and a `view_<model>` permission lambda. Unfold 0.77 renders exactly two levels (groups → flat items); per-item `has_permission` is evaluated per request, and Django's own `ModelAdmin` perms enforce the real access control (403s covered by `SidebarPermissionTests`). FK analysis (`ourlives/models.py`) shows `Order` ← (`OrderItem`, `OrderType`-qualified) and `Organization` ← (`Contact`, `OrganizationAddress`, `Contact`-only `ContactType`) parent/children clusters; reference fixtures are tiny and static (2–12 rows; Country 249 locked rows). Sidebar search covers all entries by title regardless of grouping.

## Goals / Non-Goals

**Goals:**
- Our Lives lists only the 7 main models; children + exclusive catalogs live in two collapsible domain groups directly below it.
- Every sidebar icon unique across the whole navigation.
- Zero change to permissions, URLs, admin behavior, or the 1:1 registry-coverage invariant.

**Non-Goals:**
- Stripe Events placement (explicitly out of scope).
- 3-level nesting (unsupported by bundled Unfold template; would need a custom override this project deleted).
- Moving shared catalogs (`Country`, `CodeType`, `Currency`, `Product`) — Reference data stays their home per the domain-exclusivity rule.

## Decisions

- **Two new groups, not one "Children" group.** Domain affinity (Order vs Organization) beats a generic bucket; matches how staff think ("order stuff" vs "org stuff") and mirrors the FK graph. Rejected single-group alternative: mixes unrelated domains in one drawer.
- **Order: Our Lives → Order Data → Organization Data → Reference data → Credits → Core.** Domain groups sit adjacent to their parents (which stay in Our Lives); Reference data keeps its relative slot. Rejected placing after Reference data: splits parents from children.
- **`collapsible=True` + `separator=True` on both new groups (Reference-data shape).** Collapsible groups auto-open when the active page is inside (Unfold `has_nav_item_active`), so daily flows pay no extra click; separator matches every other group boundary.
- **Move `ContactType` but not `CodeType`.** Rule: a catalog moves iff exactly one model references it AND that model's domain got a group (`ContactType`→Contact only; `OrderType`→Order only). `CodeType`'s parent (`InvitationCode`) has no group, so it stays — this is also the documented stopping rule against dissolving Reference data.
- **Icon swaps: Reps `person`→`badge`, Tokens `key`→`vpn_key`.** Keeps the more prominent concept on the familiar glyph (Users keeps `person`, Invitation Codes keeps `key`); both replacements are valid Material Symbols in Unfold's supported set. Rejected renaming Users instead: far more staff recognize the user glyph.
- **No test-code changes anticipated.** `SidebarCoverageTests` walks groups generically (relocation-safe); permission tests assert URLs, not groups. Suite re-run is the verification gate; any icon-pinning assertion found failing gets updated, not the design.

## Risks / Trade-offs

- [Staff muscle memory: Contacts/Order Items move] → Mitigation: sidebar search finds entries by title in any group; collapsible auto-opens on active page.
- [Empty group headers for users with zero permitted items in a group] → Accepted cosmetic limitation, already documented in `manual-admin-sidebar` spec.
- [Replacement Material Symbol missing from the deployed Unfold/font version] → Mitigation: verify glyphs render on the dev admin before merge; fallback glyphs (`assignment_ind`, `password`) noted in tasks.
- [Future catalogs re-fragmenting groups] → Mitigation: domain-exclusivity rule written into the spec delta.

## Migration Plan

Settings-only deploy: no migrations, no data changes. Rollback = revert `settings.py` (+ 2 one-line icon edits). Order: implement → full suite green → visual check of all six groups + permission-filtered view as a limited user.

## Open Questions

- None blocking. Gap check requested from stakeholder: confirm no other model is missing from the target layout (see task 1 verification step against `admin.site._registry`).
