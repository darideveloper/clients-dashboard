## Requirements

### Requirement: User has an admin primary color

The system SHALL store a 7-character hex color (`#RRGGBB`) on `core.Brand` as `primary_color`. The field SHALL default to `#C92FFF` (matching the project's `UNFOLD["COLORS"]["primary"][500]`). The field SHALL be validated to (a) match the regex `^#[0-9A-Fa-f]{6}$` and (b) pass a contrast check computed against the **raw hex value** (not the OKLCH-derived primary-500): the relative luminance of the candidate hex against `#ffffff` MUST be `< 0.4` so that the implied WCAG contrast ratio is ≥ 4.5:1. This threshold is calibrated so that any OKLCH derivation of the value at the project's primary-500 L/C anchors (`L=0.68, C=0.28`) also fails WCAG AA against white when the raw check fails, so no false positives slip through to the browser.

#### Scenario: Default color is the project brand
- **WHEN** a user has no explicit `primary_color` set
- **THEN** the admin renders the static `UNFOLD["COLORS"]["primary"]` palette from settings (no override is injected)

#### Scenario: User picks a contrasting color
- **WHEN** staff sets `primary_color` to a hex that passes the WCAG AA contrast check (for example `#0066FF`)
- **THEN** the color is saved and the next admin page render reflects the new palette

#### Scenario: Low-contrast color is rejected
- **WHEN** staff sets `primary_color` to a value whose relative luminance against white is ≥ 0.4 (for example `#F0F0F0`)
- **THEN** the change form is invalid, the field shows a `ValidationError`, and the value is not persisted

#### Scenario: Borderline dark color is accepted
- **WHEN** staff sets `primary_color` to a value whose relative luminance against white is < 0.4 (for example `#A0A0A0` or `#0066FF`)
- **THEN** the color is saved

#### Scenario: Non-hex string is rejected
- **WHEN** staff sets `primary_color` to a value that does not match `^#[0-9A-Fa-f]{6}$` (for example `red` or `#XYZ123`)
- **THEN** the change form is invalid and the value is not persisted

### Requirement: Per-user primary palette in admin CSS

The system SHALL inject a per-request `<style>` block via the `utils.context_processors.user_palette` template context processor that overrides the 11 `--color-primary-{50,100,200,300,400,500,600,700,800,900,950}` CSS custom properties with an `oklch(from <brand primary_color> L C h)` palette. The `(L, C)` anchor pairs SHALL be the same as the project's static `UNFOLD["COLORS"]["primary"]` palette. The primary color is resolved through the unified `_resolve_brand(request)` 4-tier priority chain (URL override → user.brand → default brand → None). When the resolved brand is `None` or `primary_color` is empty, the callback SHALL return an empty string and the static `UNFOLD["COLORS"]["primary"]` palette SHALL apply unchanged.

The CSS selector SHALL be `:root:root` (specificity 0,2,0) rather than `:root` (0,1,0). This ensures the brand palette wins against Unfold's `unfold-theme-colors` style tag (which uses `:root`, specificity 0,1,0) regardless of DOM order. The login page injects the palette via `{% block extrastyle %}` inside `<head>`, while Unfold's skeleton template renders `unfold-theme-colors` inside `<body>` — without the higher-specificity selector, Unfold's colors would win in the cascade.

#### Scenario: User with custom color
- **WHEN** an authenticated user with `primary_color = "#0066FF"` loads any admin page
- **THEN** the rendered page includes a `<style>` block setting `--color-primary-600: oklch(from #0066FF 0.60 0.25 h);` and the primary-600 button background reflects the new color

#### Scenario: User with default color
- **WHEN** an authenticated user with `primary_color = "#C92FFF"` (the project default) loads any admin page
- **THEN** the rendered page may include a redundant override (no visible change), or the callback MAY return an empty string; either outcome is acceptable

#### Scenario: Anonymous request
- **WHEN** an unauthenticated request (for example `GET /admin/login/`) is rendered
- **THEN** `utils.callbacks.primary_palette_css` resolves the brand via the unified `_resolve_brand(request)` helper:
  - If a `Brand` with `is_default=True` exists, its `primary_color` palette SHALL be injected
  - If no default brand exists, the callback SHALL return an empty string and the static `UNFOLD["COLORS"]["primary"]` palette from settings SHALL apply
- **AND** the palette SHALL be injected into the template context as `user_palette_css` by `utils.context_processors.user_palette`
- **AND** the login page template (`project/templates/admin/login.html`) SHALL render `{{ user_palette_css|safe }}` inside `{% block extrastyle %}`, outputting `<style id="user-palette">` with the `:root:root` selector

#### Scenario: Browser without `oklch(from)` support
- **WHEN** a browser predates 2024 (no `oklch(from)` support) loads an admin page for a user with a non-default `primary_color`
- **THEN** the invalid `oklch()` value is ignored, the custom property falls back to the static settings value (or `initial`), and the admin renders with the project brand palette

#### Scenario: Achromatic color produces grayscale palette
- **WHEN** staff sets `primary_color` to an achromatic value where R≈G≈B (for example `#000000` black)
- **THEN** the 11 primary shades are rendered as `oklch(L 0 0)` (grayscale using the anchor L values, no chroma, no hue), not as `oklch(from #000000 L C h)` (which would default to red hue and produce a pink palette)

#### Scenario: Context processor injects the palette
- **WHEN** `project/settings.py` is inspected
- **THEN** `TEMPLATES[0]["OPTIONS"]["context_processors"]` includes `utils.context_processors.user_palette`
- **AND** `utils/context_processors.py` calls `primary_palette_css(request)` and injects the result as `user_palette_css` into the template context
