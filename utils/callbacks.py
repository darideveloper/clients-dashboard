import os

from django.templatetags.static import static


def environment_callback(request):
    env = os.getenv("ENV", "dev")
    env_mapping = {
        "prod": ["Production", "danger"],
        "staging": ["Staging", "warning"],
        "dev": ["Development", "info"],
        "local": ["Local", "success"],
    }
    return env_mapping.get(env, ["Unknown", "info"])


def site_icon(request):
    user = getattr(request, "user", None)
    brand = getattr(user, "brand", None) if user and user.is_authenticated else None
    logo = getattr(brand, "logo", None) if brand else None
    if logo:
        try:
            return logo.url
        except (ValueError, AttributeError):
            pass
    return static("favicon.png")


def site_favicon(request):
    user = getattr(request, "user", None)
    brand = getattr(user, "brand", None) if user and user.is_authenticated else None
    if brand and brand.has_logo:
        url = brand.favicon_url
        if url:
            return url
    return static("favicon.png")


# (shade, L, C) mirrors UNFOLD["COLORS"]["primary"] in project/settings.py.
# 50..950 in steps of 100 (and 950). H is preserved from the source color
# via `oklch(from <color> L C h)` at render time.
PRIMARY_PALETTE_ANCHORS = [
    (50,  0.97, 0.02),
    (100, 0.92, 0.04),
    (200, 0.85, 0.08),
    (300, 0.75, 0.15),
    (400, 0.70, 0.22),
    (500, 0.68, 0.28),
    (600, 0.60, 0.25),
    (700, 0.50, 0.20),
    (800, 0.40, 0.16),
    (900, 0.30, 0.12),
    (950, 0.20, 0.08),
]


def primary_palette_css(request):
    user = getattr(request, "user", None)
    color = None
    if user and user.is_authenticated:
        brand = getattr(user, "brand", None)
        color = getattr(brand, "primary_color", None) if brand else None
    if not color:
        return ""

    r = int(color[1:3], 16)
    g = int(color[3:5], 16)
    b = int(color[5:7], 16)
    is_achromatic = (max(r, g, b) - min(r, g, b)) < 5

    if is_achromatic:
        rules = "\n".join(
            f"  --color-primary-{shade}: oklch({L} 0 0);"
            for shade, L, C in PRIMARY_PALETTE_ANCHORS
        )
    else:
        rules = "\n".join(
            f"  --color-primary-{shade}: oklch(from {color} {L} {C} h);"
            for shade, L, C in PRIMARY_PALETTE_ANCHORS
        )
    return f":root {{\n{rules}\n}}"
