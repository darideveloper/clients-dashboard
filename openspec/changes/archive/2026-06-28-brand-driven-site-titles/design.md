## Context

`UNFOLD` config in `project/settings.py:210-250` currently hardcodes three site title strings:

```
SITE_TITLE:     "clients Admin"
SITE_HEADER:    "clients Admin"
SITE_SUBHEADER: "clients Dashboard"
```

These are injected into template context by `unfold/sites.py:UnfoldAdminSite.each_context()` which calls `_get_config()` → `_get_value()`. The latter already supports callables/lambdas — `SITE_ICON` already uses this pattern (`lambda request: site_icon(request)`).

Meanwhile, `Brand.name` exists on every user's brand (via `Membership`), is unique, max 100 chars, and already serves as the brand's display identity (`Brand.__str__` returns `self.name`). The `site_icon()` callback in `utils/callbacks.py:17-26` demonstrates the exact pattern for resolving brand data per-request.

The design follows Option C1 from the exploration: zero new fields, derive everything from `Brand.name`, no special-casing for the Default Brand.

## Goals / Non-Goals

**Goals:**
- `SITE_TITLE`, `SITE_HEADER`, `SITE_SUBHEADER` resolve per-request from `request.user.brand.name`
- Anonymous users (no brand) fall back to the current hardcoded strings
- Implementation follows the existing `site_icon()` callback pattern
- No schema changes, no migrations, no new fields

**Non-Goals:**
- Adding per-brand `site_title`, `site_header`, or `site_subheader` fields to the Brand model
- Filtering or special-casing the Default Brand name in callbacks
- Changing any template or CSS
- Adding admin form fields

## Decisions

### Decision 1: Derivation formula — title and header equal to brand, subheader always "Dashboard"

```python
# brand.name = "Acme Corp"
site_title     → "Acme Corp"
site_header    → "Acme Corp"
site_subheader → "Dashboard"
```

Matches the requested look where the brand name is shown directly, and the subheader is static.

**Alternatives considered:**
- *`brand.name` with Admin/Dashboard suffix* — discarded to keep titles cleaner and match exact brand identity.

### Decision 2: Three separate callbacks (not a single combined one)

```python
# utils/callbacks.py
def site_title(request):     ...
def site_header(request):    ...
def site_subheader(request): ...
```

Each maps 1:1 to its `UNFOLD` config key and mirrors `site_icon()`. A single combined callback returning all three would be more efficient (one DB query) but creates an awkward interface — you'd need three separate lambdas calling into one function three times anyway, or a single wrapper that splits. The three-callback approach is simpler, more testable, and consistent with existing code. Each callback calls `_resolve_brand_name(request)` which fetches the brand once.

**Gateway function pattern:**

A shared `_resolve_brand_name(request)` helper avoids repeating the user/brand extraction logic. It caches the result on the request object so three callbacks reuse the same value (preventing N+1 queries):

```python
_request_attr = "_brand_name_cache"

def _resolve_brand_name(request):
    if hasattr(request, _request_attr):
        return getattr(request, _request_attr)
    user = getattr(request, "user", None)
    brand = getattr(user, "brand", None) if user and user.is_authenticated else None
    name = brand.name or None  # or None catches empty string edge case
    setattr(request, _request_attr, name)
    return name
```

### Decision 3: Default Brand renders its name (Option C1 — no filtering)

The Default Brand row has `name="Default Brand"`. Under this design, it renders:

```
SITE_HEADER:    "Default Brand"
SITE_SUBHEADER: "Dashboard"
```

No special-case guard filters it out. Rationale:
- The Default Brand is a real `Brand` row intentionally created; its `name` field contains what it contains
- The first action a deployer takes is renaming the Default Brand to something meaningful (e.g., "Acme Corp")
- Adding a `DEFAULT_NAME` check in callbacks hardcodes a magic string and creates a confusing conditional path
- This is consistent with how `primary_color` works — no special-casing for the Default Brand's color

### Decision 4: Fallback strings live inside callbacks

```python
FALLBACK_TITLE = "clients"
FALLBACK_HEADER = "clients"
FALLBACK_SUBHEADER = "Dashboard"
```

Defined as module-level constants in `utils/callbacks.py`. The static strings move from `settings.py` to callbacks. This keeps the fallback logic co-located with the resolution logic.

## Risks / Trade-offs

- **[Cascade from rename]** If a brand is renamed, all its users immediately see the new title. This is intended, not a bug. → Mitigation: the Brand admin is superuser-only.
- **[Long brand names]** A 100-char brand name with " Admin" suffix could overflow the sidebar header. → Mitigation: Unfold's CSS already applies `truncate` via `*:truncate` class on the branding div. No action needed.
- **[Default Brand looks generic]** The default brand renders "Default Brand Admin" until renamed. → Mitigation: the `seed_brands` command or a post-provisioning step can rename the default brand. This is a setup concern, not a code concern.
- **[Empty brand.name edge case]** A brand created programmatically with `name=""` would produce `" Admin"` as the header. → Mitigation: `_resolve_brand_name` uses `brand.name or None`, collapsing empty strings to `None` so the fallback fires.
