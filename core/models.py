from django.conf import settings
from django.contrib.auth.models import User
from django.db import models

from core.validators import (
    validate_contrast_against_white,
    validate_hex_color,
    validate_image_size,
)


def brand_logo_upload_to(instance, filename):
    return f"brands/brand_{instance.pk}/{filename}"


# Backwards-compatible alias so that historical migrations (e.g.
# `core/migrations/0001_initial.py`) that reference `avatar_upload_to` keep
# loading after the rename. The actual storage path for new uploads is
# `brands/brand_<pk>/...` (set via `Brand.logo.upload_to`).
avatar_upload_to = brand_logo_upload_to


class Brand(models.Model):
    name = models.CharField(
        max_length=100,
        unique=True,
        default="Default Brand",
    )
    logo = models.ImageField(
        upload_to=brand_logo_upload_to,
        blank=True,
        validators=[validate_image_size],
    )
    primary_color = models.CharField(
        max_length=7,
        default="#C92FFF",
        validators=[validate_hex_color, validate_contrast_against_white],
    )

    DEFAULT_NAME = "Default Brand"
    DEFAULT_PRIMARY_COLOR = "#C92FFF"

    class Meta:
        verbose_name_plural = "Brands"

    def __str__(self):
        return self.name

    @property
    def has_logo(self):
        return bool(self.logo)

    @classmethod
    def get_or_create_default(cls):
        """
        Return the system's Default Brand row, creating it on first call.

        Idempotent: subsequent calls return the same row.
        """
        obj, _ = cls.objects.get_or_create(
            name=cls.DEFAULT_NAME,
            defaults={
                "primary_color": cls.DEFAULT_PRIMARY_COLOR,
            },
        )
        return obj


class Membership(models.Model):
    """
    One-to-one carrier for the user→brand link.

    A real model (not `User.add_to_class`) is used so Django's migration
    autodetector can manage the schema; `User.brand` is exposed as a
    settable property on `User` that reads/writes through this row.
    """

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="membership",
    )
    brand = models.ForeignKey(
        Brand,
        on_delete=models.PROTECT,
        related_name="memberships",
    )

    def __str__(self):
        return f"{self.user} → {self.brand}"


# Settable `User.brand` property backed by `Membership`.
def _get_brand(self):
    membership = getattr(self, "membership", None)
    return membership.brand if membership is not None else None


def _set_brand(self, brand):
    if brand is None:
        Membership.objects.filter(user=self).delete()
        return
    Membership.objects.update_or_create(user=self, defaults={"brand": brand})


User.brand = property(_get_brand, _set_brand)
