## Context

`MembershipInline` at `core/admin.py:57` extends Django's vanilla `admin.StackedInline`. The project uses Django Unfold for the admin interface (`ModelAdminUnfoldBase` extends `unfold.admin.ModelAdmin` with `compressed_fields = True`). However, inlines are rendered independently of the main form — a vanilla `StackedInline` renders with Django's native templates rather than Unfold's Tailwind-based design. This creates a visual mismatch: the brand selector appears as a plain Django card-within-a-card, with different borders, spacing, and typography than the surrounding Unfold-styled form.

The fix is a one-line base class swap: `admin.StackedInline` → `unfold.admin.StackedInline`. Unfold's `StackedInline` extends Django's `InlineModelAdmin` with Tailwind-aware templates, matching the project's visual language.

## Goals / Non-Goals

**Goals:**
- `MembershipInline` renders with Unfold-native Tailwind styling (consistent borders, spacing, typography)
- Zero behavioral changes — same field, same permissions, same data flow
- Minimal change surface — one import, one base class change

**Non-Goals:**
- Removing the inline in favor of a form field (deferred to separate change)
- Adding/removing fields on the inline
- Changing permission gates
- Migrations or schema changes

## Decisions

### D1: `unfold.admin.StackedInline` over `unfold.admin.TabularInline`

**Chosen: `unfold.admin.StackedInline`**

`TabularInline` would render the single `brand` dropdown as a compact table row — arguably more appropriate for one field. However, `StackedInline` is chosen to keep the change minimal: swapping the base class without also changing the layout semantics. A tabular inline for one field is also unconventional and may look out of place. If the stacked layout still feels too heavy after this fix, a separate change can explore removing the inline entirely.

No alternatives considered — this is a one-line styling fix with a clear correct answer.

## Risks / Trade-offs

| Risk | Mitigation |
|---|---|
| Visual change surprises users | The change only affects styling, not layout structure. The inline still renders as a bordered card — just with Unfold-consistent Tailwind classes now. |
| Unfold's `StackedInline` diverges from Django's in future | Unlikely; Unfold extends Django's classes. If it does, this project's dependency version pins prevent breakage. |
