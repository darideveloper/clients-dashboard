import logging
from io import BytesIO

from django.conf import settings
from django.contrib.auth.models import User
from django.core.files.base import ContentFile
from django.db import models
from PIL import Image

from core.validators import (
    validate_contrast_against_white,
    validate_hex_color,
    validate_image_size,
)

logger = logging.getLogger(__name__)


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
    FAVICON_SIZE = (32, 32)

    class Meta:
        verbose_name_plural = "Brands"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._original_logo_name = self.logo.name if self.logo else None

    def __str__(self):
        return self.name

    @property
    def has_logo(self):
        return bool(self.logo)

    @property
    def favicon_url(self):
        if not self.logo or not self.pk:
            return None
        return self.logo.storage.url(f"brands/brand_{self.pk}/favicon.png")

    def _favicon_storage_path(self):
        return f"brands/brand_{self.pk}/favicon.png"

    def _generate_favicon(self):
        try:
            img = Image.open(self.logo)
        except FileNotFoundError:
            logger.warning(
                "Logo file not found at %s; skipping favicon generation", self.logo.name
            )
            return
        size = min(img.size)
        left = (img.width - size) // 2
        top = (img.height - size) // 2
        img = img.crop((left, top, left + size, top + size))
        img = img.resize(self.FAVICON_SIZE, Image.Resampling.LANCZOS)
        buf = BytesIO()
        img.save(buf, format="PNG")
        buf.seek(0)
        storage = self.logo.storage
        path = self._favicon_storage_path()
        if storage.exists(path):
            storage.delete(path)
        storage.save(path, ContentFile(buf.getvalue()))

    def _delete_favicon_if_exists(self):
        path = self._favicon_storage_path()
        storage = Brand.logo.field.storage if self.pk else None
        if storage and storage.exists(path):
            try:
                storage.delete(path)
            except Exception:
                logger.warning("Failed to delete favicon at %s", path)

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        current_name = self.logo.name if self.logo else None
        if current_name != self._original_logo_name:
            if current_name:
                self._generate_favicon()
            else:
                self._delete_favicon_if_exists()
        self._original_logo_name = current_name

    def delete(self, *args, **kwargs):
        self._delete_favicon_if_exists()
        super().delete(*args, **kwargs)

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
