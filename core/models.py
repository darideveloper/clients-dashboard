from django.conf import settings
from django.contrib.auth.models import User
from django.db import models

from core.validators import (
    validate_contrast_against_white,
    validate_hex_color,
    validate_image_size,
)


def avatar_upload_to(instance, filename):
    return f"avatars/user_{instance.user_id}/{filename}"


class Profile(models.Model):
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="profile",
    )
    avatar = models.ImageField(
        upload_to=avatar_upload_to,
        blank=True,
        validators=[validate_image_size],
    )
    primary_color = models.CharField(
        max_length=7,
        default="#C92FFF",
        validators=[validate_hex_color, validate_contrast_against_white],
    )

    def __str__(self):
        return f"Profile({self.user_id})"

    @property
    def has_avatar(self):
        return bool(self.avatar)


if not hasattr(User, "avatar_url"):

    def _avatar_url(self):
        try:
            profile = self.profile
        except Exception:
            return ""
        avatar = getattr(profile, "avatar", None)
        if not avatar:
            return ""
        try:
            return avatar.url
        except (ValueError, AttributeError):
            return ""

    User.avatar_url = property(_avatar_url)
    del _avatar_url
