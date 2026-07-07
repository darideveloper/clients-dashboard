from .admin_icons import build_sidebar_icon_map
from .callbacks import _resolve_brand, primary_palette_css


def user_palette(request):
    brand = _resolve_brand(request)
    return {
        "user_palette_css": primary_palette_css(request),
        "sidebar_icons": build_sidebar_icon_map(),
        "current_brand_slug": brand.slug if brand else "",
    }
