from .callbacks import primary_palette_css


def user_palette(request):
    return {"user_palette_css": primary_palette_css(request)}
