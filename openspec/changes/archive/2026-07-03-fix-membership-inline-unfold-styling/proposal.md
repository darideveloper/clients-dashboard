## Why

`MembershipInline` extends Django's vanilla `admin.StackedInline` instead of `unfold.admin.StackedInline`. This means the brand selector on the User change form renders with Django's native styling — mismatched borders, spacing, and structure — instead of Unfold's Tailwind-based design. The Unfold docs explicitly warn: "While Django's native inline classes will function correctly, they won't match Unfold's default design aesthetic."

## What Changes

- **`core/admin.py`**: Change `MembershipInline` base class from `admin.StackedInline` to `unfold.admin.StackedInline`. Add `from unfold.admin import StackedInline as UnfoldStackedInline` import.

## Capabilities

### New Capabilities

_None._

### Modified Capabilities

_None._ This is a pure styling fix — a one-line base class swap. No spec-level behavior changes. The inline still renders a brand dropdown, still gated to superusers, still backed by `Membership`. Only the HTML/CSS rendering changes.

## Impact

| Area | Change |
|---|---|
| `core/admin.py` | Line 57: `MembershipInline(admin.StackedInline)` → `MembershipInline(UnfoldStackedInline)`; add 1 import |
| No other files | Zero changes |
| No tests needed | CSS-only visual change; behavior/payload identical |
| No migrations | No schema changes |
