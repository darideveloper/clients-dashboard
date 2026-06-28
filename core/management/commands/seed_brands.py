"""
seed_brands — one-shot data + file back-fill for the `profile-to-brand` change.

Run ONCE after `python manage.py migrate core` (which applies the auto-generated
schema migration) and BEFORE the schema enforces `User.brand` `NOT NULL`.

Forward (`./manage.py seed_brands`):
    1. Get-or-create the system Default Brand (`Brand.DEFAULT_NAME`).
    2. For every user, ensure `User.brand` is set:
       - Users created via the admin get the Default Brand via `UserAdmin.save_model`.
       - Users created programmatically (or before the signal-removal commit) are
         assigned the Default Brand here.
    3. Relocate logo files:
       - Forward: `MEDIA_ROOT/avatars/user_<id>/<filename>` → `MEDIA_ROOT/brands/brand_<pk>/<filename>`
       - Update `Brand.logo.name` to the new relative path.
       - Missing source files are silently skipped.

Reverse (`./manage.py seed_brands --reverse`):
    - Move files back from `brands/brand_<pk>/` to `avatars/user_<id>/` (best-effort).
    - Reassign `User.brand` only if a snapshot is available; otherwise no-op
      with a warning (the one-to-one relationship is no longer represented).

Idempotent: running forward twice is a no-op the second time.
"""
import os
import re
import shutil
import warnings

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from core.models import Brand, Membership


LEGACY_AVATAR_DIR = "avatars"
NEW_BRAND_DIR = "brands"


class Command(BaseCommand):
    help = (
        "One-shot data + file back-fill for the profile-to-brand change. "
        "Idempotent; supports --reverse to best-effort restore legacy paths."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--reverse",
            action="store_true",
            help="Reverse mode: best-effort restore files back to legacy avatar paths.",
        )

    def handle(self, *args, **options):
        reverse = options.get("reverse", False)

        if reverse:
            self._handle_reverse()
        else:
            self._handle_forward()

    # -- forward --------------------------------------------------------------

    def _handle_forward(self):
        media_root = settings.MEDIA_ROOT
        default_brand = Brand.get_or_create_default()
        self.stdout.write(f"Default brand: {default_brand!r} (pk={default_brand.pk})")

        User = get_user_model()

        users_with_brand_ids = set(
            Membership.objects.values_list("user_id", flat=True)
        )
        all_user_ids = set(User.objects.values_list("id", flat=True))
        users_without_brand_ids = sorted(all_user_ids - users_with_brand_ids)
        for uid in users_without_brand_ids:
            user = User.objects.get(pk=uid)
            user.brand = default_brand
            user.save(update_fields=[])
        self.stdout.write(
            self.style.SUCCESS(
                f"Users reassigned to Default Brand: {len(users_without_brand_ids)}"
            )
        )

        brands_processed = 0
        files_moved = 0
        files_skipped = 0

        for brand in Brand.objects.all():
            brands_processed += 1
            logo = brand.logo
            if not logo:
                continue
            old_name = logo.name
            if not old_name.startswith(f"{LEGACY_AVATAR_DIR}/"):
                continue
            new_name = re.sub(
                rf"^{re.escape(LEGACY_AVATAR_DIR)}/user_[^/]+/",
                f"{NEW_BRAND_DIR}/brand_{brand.pk}/",
                old_name,
            )
            old_abs = os.path.join(media_root, old_name)
            new_abs = os.path.join(media_root, new_name)
            if not os.path.exists(old_abs):
                files_skipped += 1
                continue
            os.makedirs(os.path.dirname(new_abs), exist_ok=True)
            try:
                shutil.move(old_abs, new_abs)
            except FileNotFoundError:
                files_skipped += 1
                continue
            brand.logo.name = new_name
            brand.save(update_fields=["logo"])
            files_moved += 1

        self.stdout.write(self.style.SUCCESS(f"Brands processed: {brands_processed}"))
        self.stdout.write(self.style.SUCCESS(f"Files moved: {files_moved}"))
        self.stdout.write(
            self.style.WARNING(f"Files skipped (missing source): {files_skipped}")
        )

    # -- reverse --------------------------------------------------------------

    def _handle_reverse(self):
        media_root = settings.MEDIA_ROOT
        brands_processed = 0
        files_moved = 0
        files_skipped = 0

        for brand in Brand.objects.all():
            brands_processed += 1
            logo = brand.logo
            if not logo:
                continue
            new_name = logo.name
            if not new_name.startswith(f"{NEW_BRAND_DIR}/brand_{brand.pk}/"):
                continue
            # Recover the user_id from the brand's membership (best-effort).
            membership = brand.memberships.first()
            if membership is None:
                files_skipped += 1
                continue
            user_id = membership.user_id
            old_name = re.sub(
                rf"^{re.escape(NEW_BRAND_DIR)}/brand_{brand.pk}/",
                f"{LEGACY_AVATAR_DIR}/user_{user_id}/",
                new_name,
            )
            old_abs = os.path.join(media_root, old_name)
            new_abs = os.path.join(media_root, new_name)
            if not os.path.exists(new_abs):
                files_skipped += 1
                continue
            try:
                os.makedirs(os.path.dirname(old_abs), exist_ok=True)
                shutil.move(new_abs, old_abs)
            except FileNotFoundError:
                files_skipped += 1
                continue
            brand.logo.name = old_name
            brand.save(update_fields=["logo"])
            files_moved += 1

        warnings.warn(
            "Reverse mode could not restore User→brand links because the legacy "
            "OneToOne has been removed by the schema migration. Re-run the "
            "schema migration in reverse to restore the OneToOne model "
            "('Profile') and re-populate manually if needed."
        )

        self.stdout.write(self.style.SUCCESS(f"Brands processed: {brands_processed}"))
        self.stdout.write(self.style.SUCCESS(f"Files moved: {files_moved}"))
        self.stdout.write(
            self.style.WARNING(f"Files skipped (missing source): {files_skipped}")
        )
