## Why

The logout screen (`/admin/logout/`) renders without custom brand colors because of a template chain gap. Unfold's `registration/logged_out.html` extends `unfold/layouts/unauthenticated.html`, which does NOT extend `admin/base.html`. Therefore neither the `base.html` override (injects palette via `{% block base %}`) nor the `login.html` override (injects palette via `{% block extrastyle %}`) covers the logout page. Since login already has brand-aware palette injection, logout is inconsistent and breaks the branded experience.

## What Changes

- Create directory `project/templates/registration/` (if not exists)
- Create `project/templates/registration/logged_out.html` extending Unfold's `registration/logged_out.html` by name
- Inject `user_palette_css` in `{% block extrastyle %}` — same injection pattern as `admin/login.html`
- Exact template content:

```django
{% extends "registration/logged_out.html" %}
{% block extrastyle %}
    {{ block.super }}
    {% if user_palette_css %}
    <style id="user-palette">
        {{ user_palette_css|safe }}
    </style>
    {% endif %}
{% endblock %}
```

## Capabilities

### New Capabilities
- `branded-logout`: Brand colors applied to the Unfold logout screen via palette CSS injection

### Modified Capabilities

<!-- No existing specs have requirement changes -->

## Impact

- **New directory**: `project/templates/registration/`
- **New file**: `project/templates/registration/logged_out.html` (9 lines, extends Unfold's template)
- No changes to models, views, middleware, or settings
- No new dependencies
