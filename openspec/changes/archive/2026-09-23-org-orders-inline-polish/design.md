## Context

`OrgOrderInline` (`ourlives/admin.py:49`) uses `show_change_link=True`, which Unfold renders in the inline title row (`tabular_title.html:20-28`, `colspan=cell_count`) — not as a column. Heading/row templates loop only `fields` + delete. `OrganizationAdmin.inlines` (`admin.py:69`) orders sections Contacts → Addresses → Orders as full-width stacked cards below all fieldsets (`unfold/templates/admin/change_form.html:60-84`; `tab=False` default, no tab bar). Decisions from explore: blank header, permission-aware label, Orders first, keep stock layout (no custom `change_form.html`).

## Goals / Non-Goals

**Goals:**
- Per-row Change/View action in a dedicated trailing column with blank header.
- Orders as the first inline section on the Organization detail page.

**Non-Goals:**
- Custom inline or change-form templates; interleaving inlines between fieldsets.
- Editable inline rows; changes to columns, totals, permissions, changelist.

## Decisions

1. **Readonly `order_link` display method as last entry of `fields`/`readonly_fields`, `show_change_link=False`.**
   Rationale: heading/row templates auto-render declared fields — ~8 lines, zero template fork to track on Unfold upgrades. Guard `obj.pk` keeps the empty-form row blank. Alternative (forked `tabular_heading.html`/`tabular_row.html` with `lg:w-px` column) rejected as higher maintenance for equal function.
2. **Permission-aware label via a request stashed on the inline itself (`get_formset` override), `inlinechangelink`/`inlineviewlink` classes.**
   Rationale: display methods receive only `(obj)`, and `ChangeRequestStashMixin._change_request` lives on `OrganizationAdmin` — invisible to the inline instance — so `OrgOrderInline.get_formset` stashes its own `_inline_request` (same overwrite-per-request pattern). Replicates Django's native title-link semantics (`"Change"` with change perm, `"View"` otherwise). Falls back to `"Change"` when no request is stashed.
3. **Reorder `inlines` tuple only: `(OrgOrderInline, ContactInline, OrganizationAddressInline)`.**
   Rationale: `change_form.html` iterates the tuple — one-line reorder, no fieldset interaction, no side effects while `tab=False`. True interleaving (`Scans total → Orders → Codes`) would need a custom template; explicitly out of scope per user choice.

## Risks / Trade-offs

- [Risk] Blank header is less explicit for assistive tech → Mitigation: link text (`Change`/`View`) carries meaning; revert to `description="Change"` is one word.
- [Risk] Tests pinning `fields` 3-tuple and title-row link → Mitigation: extend assertions in the same change.
- [Risk] Inline still renders all rows unpaginated → Unchanged from parent change; 4 narrow local-only columns stay flat.
