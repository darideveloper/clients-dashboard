## 1. Template Creation

- [x] 1.0 Create directory `project/templates/registration/` (`mkdir -p`)
- [x] 1.1 Write `project/templates/registration/logged_out.html` with exact content:

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

## 2. Verification

- [x] 2.1 Visit `/admin/logout/` and confirm `<style id="user-palette">` renders with brand CSS vars
- [x] 2.2 Open DevTools → Elements and verify `#user-palette` appears after `unfold/css/styles.css` but its `:root:root` values override `#unfold-theme-colors` `:root` values in Computed styles
- [x] 2.3 Confirm logout page content (message + "Log in again" button) is unchanged from Unfold's default
- [x] 2.4 Run test suite to confirm no regressions

## 3. Test Coverage

- [x] 3.1 Add test: brand palette renders `<style id="user-palette">` on logout
- [x] 3.2 Add test: graceful fallback when no default brand exists (no palette)
