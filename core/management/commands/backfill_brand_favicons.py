"""
backfill_brand_favicons — generate favicon.png for every Brand that has a logo.

Idempotent: re-running re-generates all favicons. Safe to run after logo changes
that may have happened before the auto-generation was deployed.
"""

from django.core.management.base import BaseCommand

from core.models import Brand


class Command(BaseCommand):
    help = "Generate a 32x32 favicon.png for every Brand that has a logo."

    def handle(self, *args, **options):
        generated = 0
        skipped = 0
        errors = 0

        for brand in Brand.objects.all():
            if not brand.has_logo:
                skipped += 1
                continue
            try:
                brand._generate_favicon()
                generated += 1
            except Exception as e:
                self.stderr.write(
                    self.style.ERROR(
                        f"Error generating favicon for brand pk={brand.pk} "
                        f"({brand.name}): {e}"
                    )
                )
                errors += 1

        self.stdout.write(self.style.SUCCESS(f"Favicons generated: {generated}"))
        self.stdout.write(self.style.WARNING(f"Skipped (no logo): {skipped}"))
        if errors:
            self.stdout.write(self.style.ERROR(f"Errors: {errors}"))
