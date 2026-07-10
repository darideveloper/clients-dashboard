import stripe
from django.conf import settings
from django.core.management.base import BaseCommand

from ourlives.models import AppSettings


class Command(BaseCommand):
    help = "Create or update Stripe Product + Price from AppSettings.price_per_token"

    def handle(self, *args, **options):
        stripe.api_key = settings.STRIPE_SECRET_KEY

        app_settings = AppSettings.get_solo()

        if app_settings.price_per_token is None or app_settings.price_per_token <= 0:
            self.stdout.write(self.style.WARNING(
                "Skipping: price_per_token must be positive (purchases disabled)"
            ))
            return

        cents = int(app_settings.price_per_token * 100)

        product_id = None
        if app_settings.stripe_product_id:
            product_id = app_settings.stripe_product_id
        elif hasattr(settings, "STRIPE_PRODUCT_ID") and settings.STRIPE_PRODUCT_ID:
            product_id = settings.STRIPE_PRODUCT_ID

        if product_id:
            self.stdout.write(f"Reusing product: {product_id}")
        else:
            product = stripe.Product.create(name="Invitation Code Tokens")
            app_settings.stripe_product_id = product.id
            product_id = product.id
            self.stdout.write(f"Created product: {product_id}")

        if app_settings.stripe_price_id:
            try:
                stripe.Price.modify(app_settings.stripe_price_id, active=False)
                self.stdout.write(f"Archived old price: {app_settings.stripe_price_id}")
            except stripe.error.StripeError:
                self.stdout.write("Old price not found or already archived, proceeding")

        price = stripe.Price.create(
            product=product_id,
            unit_amount=cents,
            currency="usd",
        )
        app_settings.stripe_price_id = price.id
        app_settings.save()

        self.stdout.write(self.style.SUCCESS(
            f"Price created: {price.id} (${app_settings.price_per_token} per token)"
        ))
