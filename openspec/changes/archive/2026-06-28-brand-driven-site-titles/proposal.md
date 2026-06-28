## Why

`UNFOLD` config in `settings.py` hardcodes `SITE_TITLE`, `SITE_HEADER`, and `SITE_SUBHEADER` as static strings. Every other brand-driven visual element — the logo via `site_icon()` callback, the primary color palette via `primary_palette_css()` — already resolves per-user from `Brand`. The site titles are the last hardcoded piece, producing a mismatch: "clients Admin" in the sidebar while the logo and colors belong to "Acme Corp."

Deriving titles from `Brand.name` closes the gap without schema changes.

## What Changes

- `utils/callbacks.py`: add three callbacks — `site_title`, `site_header`, `site_subheader` — that resolve from `request.user.brand.name`
- `project/settings.py`: replace three static strings with lambdas pointing at the new callbacks
- `openspec/specs/unfold-admin-theme/spec.md`: update requirements to reflect dynamic (not static) titles
- `openspec/specs/brand-management/spec.md`: update to reflect that `Brand.name` also drives admin chrome titles
- No schema changes — zero new fields, zero migrations
- The Default Brand row (`name="Default Brand"`) renders "Default Brand" / "Dashboard" until renamed; no special-case filtering

## Capabilities

### Modified Capabilities

- `unfold-admin-theme`: `SITE_TITLE`, `SITE_HEADER`, `SITE_SUBHEADER` SHALL be dynamic per-request callbacks resolving from `Brand.name`, not static strings. The config contract changes from "SHALL set these strings" to "SHALL set these as lambdas resolving from callbacks."
- `brand-management`: `Brand.name` SHALL serve dual purpose — brand identifier AND source of admin chrome titles. The default brand name "Default Brand" produces generic titles until renamed.

## Impact

- `utils/callbacks.py` — +3 small functions
- `project/settings.py` — 3 lines changed (strings → lambdas)
- `openspec/specs/unfold-admin-theme/spec.md` — update scenario assertions to refer to dynamic resolution
- `openspec/specs/brand-management/spec.md` — document that `name` drives titles
- No migration, no model changes, no template changes, no admin form changes
- Anonymous users (login page) continue to see fallback strings defined inside callbacks
- Default Brand users see "Default Brand" in the sidebar until an admin renames the brand
