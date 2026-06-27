import re

from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

MAX_AVATAR_SIZE = 2 * 1024 * 1024

HEX_COLOR_RE = re.compile(r"^#[0-9A-Fa-f]{6}$")

# Threshold calibrated so that any OKLCH derivation at the project's
# primary-500 L/C anchors (L=0.68, C=0.28) also fails WCAG AA against white
# when the raw check fails. See specs/per-user-primary-color/spec.md.
_LUMINANCE_THRESHOLD = 0.4


def validate_image_size(file):
    if file and file.size and file.size > MAX_AVATAR_SIZE:
        raise ValidationError(
            _("Image file too large. Maximum size is 2 MB."),
            code="file_too_large",
        )


def validate_hex_color(value):
    if not value or not HEX_COLOR_RE.match(value):
        raise ValidationError(
            _("Enter a valid hex color in the form '#RRGGBB'."),
            code="invalid_hex_color",
        )


def _srgb_to_linear(channel):
    channel = channel / 255.0
    return channel / 12.92 if channel <= 0.03928 else ((channel + 0.055) / 1.055) ** 2.4


def _relative_luminance(hex_color):
    hex_color = hex_color.lstrip("#")
    r = int(hex_color[0:2], 16)
    g = int(hex_color[2:4], 16)
    b = int(hex_color[4:6], 16)
    return 0.2126 * _srgb_to_linear(r) + 0.7152 * _srgb_to_linear(g) + 0.0722 * _srgb_to_linear(b)


def validate_contrast_against_white(value):
    if not HEX_COLOR_RE.match(value or ""):
        return
    luminance = _relative_luminance(value)
    if luminance >= _LUMINANCE_THRESHOLD:
        raise ValidationError(
            _(
                "Color must contrast with white at WCAG AA (4.5:1). "
                "Pick a darker color."
            ),
            code="contrast_too_low",
        )
