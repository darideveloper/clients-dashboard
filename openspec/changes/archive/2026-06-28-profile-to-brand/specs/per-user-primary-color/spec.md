## REMOVED Requirements

The capability `per-user-primary-color` is fully retired by the `brand-management` capability introduced in this change. Each requirement below is removed; the per-user concept is replaced by a per-brand concept on the new `Brand` model.

### Requirement: User has an admin primary color
**Reason**: The `primary_color` field moves from `Profile` to `Brand`. Every requirement about format (`#RRGGBB`), default (`#C92FFF`), `validate_hex_color`, and `validate_contrast_against_white` is re-stated on `Brand.primary_color` inside the `Brand entity` requirement in `brand-management`.

#### Scenario: Default color is the project brand
- **WHEN** a `Brand` has no explicit `primary_color` set (uses the default `#C92FFF`)
- **THEN** the admin renders the static `UNFOLD["COLORS"]["primary"]` palette from settings
- **AND** this scenario is subsumed by `brand-management` requirement `Primary color palette reflects the user's brand` (empty-string branch when no brand/color is set)

#### Scenario: User picks a contrasting color
- **WHEN** staff sets `Brand.primary_color` to a hex that passes the WCAG AA contrast check
- **THEN** the color is saved and the next admin page render reflects the new palette
- **AND** the contrast-check contract is preserved (see `Brand entity` in `brand-management`)

#### Scenario: Low-contrast color is rejected
- **WHEN** staff sets `primary_color` to a value whose relative luminance against white is ≥ 0.4
- **THEN** the change form is invalid and the value is not persisted
- **AND** the validator (`validate_contrast_against_white`) is preserved on `Brand.primary_color`

#### Scenario: Borderline dark color is accepted
- **WHEN** staff sets `primary_color` to a value whose relative luminance against white is < 0.4
- **THEN** the color is saved
- **AND** the validator behavior is preserved

#### Scenario: Non-hex string is rejected
- **WHEN** staff sets `primary_color` to a non-hex string
- **THEN** the change form is invalid and the value is not persisted
- **AND** the validator (`validate_hex_color`) is preserved on `Brand.primary_color`

### Requirement: Per-user primary palette in admin CSS
**Reason**: The per-user `oklch(from <color> L C h)` palette injection is repurposed to be **per-brand** rather than per-user. The mechanism (`utils.callbacks.primary_palette_css` registered in `UNFOLD["STYLES"]`, the 11 `--color-primary-{50..950}` custom properties, the achromatic-vs-color branch, and the favicon-fallback for anonymous requests) is preserved. The data source shifts from `user.profile.primary_color` to `user.brand.primary_color`. Replacement requirement: `Primary color palette reflects the user's brand` in `brand-management`.

#### Scenario: User with custom color
- **WHEN** an authenticated user with `user.brand.primary_color = "#0066FF"` loads any admin page
- **THEN** the rendered page includes a `<style>` block setting the `--color-primary-600` custom property
- **AND** this scenario now lives in `brand-management` requirement `Primary color palette reflects the user's brand`

#### Scenario: User with default color
- **WHEN** an authenticated user with `user.brand.primary_color = "#C92FFF"` loads any admin page
- **THEN** the callback MAY return an empty string
- **AND** this scenario now lives in `brand-management` requirement `Primary color palette reflects the user's brand`

#### Scenario: Anonymous request
- **WHEN** an unauthenticated request reaches the palette callback
- **THEN** `utils.callbacks.primary_palette_css` returns an empty string
- **AND** the static `UNFOLD["COLORS"]["primary"]` palette from settings applies
- **AND** this scenario now lives in `brand-management` requirement `Primary color palette reflects the user's brand`

#### Scenario: Browser without `oklch(from)` support
- **WHEN** a browser predates 2024 loads an admin page for a user with a non-default `Brand.primary_color`
- **THEN** the invalid `oklch()` value is ignored and the admin renders with the project brand palette
- **AND** this scenario now lives in `brand-management` requirement `Primary color palette reflects the user's brand`

#### Scenario: Achromatic color produces grayscale palette
- **WHEN** `Brand.primary_color` is an achromatic value
- **THEN** the 11 primary shades are rendered as `oklch(L 0 0)` (grayscale), not as `oklch(from <color> L C h)` (which would default to red hue)
- **AND** this scenario now lives in `brand-management` requirement `Primary color palette reflects the user's brand`

#### Scenario: STYLES registers the callback
- **WHEN** `project/settings.py` is inspected
- **THEN** `UNFOLD["STYLES"]` includes an entry pointing at `utils.callbacks.primary_palette_css`
- **AND** this contract is preserved
