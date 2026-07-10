import uuid

from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import models
from solo.models import SingletonModel


def generate_invitation_code():
    return uuid.uuid4().hex[:12].upper()


class Project(models.Model):
    name = models.CharField(
        max_length=100,
        unique=True,
        help_text="Project name",
    )
    description = models.TextField(blank=True)

    class Meta:
        verbose_name = "Project"
        verbose_name_plural = "Projects"

    def __str__(self):
        return self.name


class InvitationCode(models.Model):
    project = models.ForeignKey(
        Project,
        on_delete=models.PROTECT,
        related_name="invitation_codes",
    )
    code = models.CharField(
        max_length=50,
        unique=True,
        default=generate_invitation_code,
        help_text="Auto-generated unique code. May be overridden.",
    )
    is_active = models.BooleanField(default=True)
    max_use = models.PositiveIntegerField(
        help_text="Number of tokens this code consumes from the pool",
    )
    current_use = models.PositiveIntegerField(
        default=0,
        help_text="Incremented by external service. Read-only in admin.",
    )

    class Meta:
        verbose_name = "Invitation Code"
        verbose_name_plural = "Invitation Codes"
        constraints = [
            models.CheckConstraint(
                name="current_use_lte_max_use",
                condition=models.Q(current_use__lte=models.F("max_use")),
            ),
        ]

    def __str__(self):
        return self.code

    def clean(self):
        app_settings = AppSettings.get_solo()

        if self.pk is not None:
            old = InvitationCode.objects.get(pk=self.pk)
            if self.max_use < old.current_use:
                raise ValidationError({
                    "max_use": (
                        f"max_use ({self.max_use}) cannot be less than "
                        f"current_use ({old.current_use})"
                    ),
                })

        qs = InvitationCode.objects.all()
        if self.pk:
            qs = qs.exclude(pk=self.pk)
        assigned = qs.aggregate(total=models.Sum("max_use"))["total"] or 0

        if assigned + self.max_use > app_settings.total_tokens:
            raise ValidationError({
                "max_use": (
                    f"Not enough tokens. Available: "
                    f"{app_settings.total_tokens - assigned}, "
                    f"Requested: {self.max_use}"
                ),
            })

    def save(self, *args, **kwargs):
        from django.db import transaction

        self.full_clean(exclude={"current_use"})

        with transaction.atomic():
            app_settings = AppSettings.get_solo()
            app_settings = (
                AppSettings.objects.select_for_update().get(pk=app_settings.pk)
            )

            if self.pk is not None:
                old = InvitationCode.objects.select_for_update().get(pk=self.pk)
                if self.max_use < old.current_use:
                    raise ValidationError(
                        f"max_use ({self.max_use}) cannot be less than "
                        f"current_use ({old.current_use})"
                    )

            qs = InvitationCode.objects.all()
            if self.pk:
                qs = qs.exclude(pk=self.pk)

            assigned = qs.aggregate(total=models.Sum("max_use"))["total"] or 0

            if assigned + self.max_use > app_settings.total_tokens:
                raise ValidationError(
                    f"Not enough tokens. Available: "
                    f"{app_settings.total_tokens - assigned}, "
                    f"Requested: {self.max_use}"
                )

        super().save(*args, **kwargs)


class AppSettings(SingletonModel):
    total_tokens = models.PositiveIntegerField(
        default=0,
        help_text="Maximum number of tokens available across all invitation codes",
    )
    price_per_token = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        help_text="Price per token in USD. Set to 0 to disable purchasing.",
    )
    min_purchase_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        help_text="Minimum purchase amount in USD. Set to 0 for no minimum.",
    )
    stripe_product_id = models.CharField(
        max_length=255,
        blank=True,
        help_text="Stripe Product ID (e.g., 'prod_xxxxx'). Auto-populated by sync_stripe_price command.",
    )
    stripe_price_id = models.CharField(
        max_length=255,
        blank=True,
        help_text="Stripe Price ID (e.g., 'price_xxxxx'). Auto-populated by sync_stripe_price command.",
    )

    class Meta:
        verbose_name = "App Settings"

    def __str__(self):
        return "App Settings"

    def clean(self):
        if self.total_tokens < self.tokens_assigned:
            raise ValidationError({
                "total_tokens": (
                    f"Cannot set total tokens ({self.total_tokens}) "
                    f"below currently assigned tokens "
                    f"({self.tokens_assigned})"
                ),
            })
        if self.price_per_token is not None and self.price_per_token < Decimal("0"):
            raise ValidationError({
                "price_per_token": "Price per token cannot be negative.",
            })
        if self.min_purchase_amount is not None and self.min_purchase_amount < Decimal("0"):
            raise ValidationError({
                "min_purchase_amount": "Minimum purchase amount cannot be negative.",
            })

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    @property
    def tokens_assigned(self):
        return InvitationCode.objects.aggregate(
            total=models.Sum("max_use"),
        )["total"] or 0

    @property
    def tokens_used(self):
        return InvitationCode.objects.aggregate(
            total=models.Sum("current_use"),
        )["total"] or 0

    @property
    def tokens_available(self):
        return self.total_tokens - self.tokens_assigned


class StripeEvent(models.Model):
    stripe_event_id = models.CharField(max_length=255, unique=True)
    source = models.CharField(max_length=50)
    token_count = models.PositiveIntegerField()
    amount_cents = models.PositiveIntegerField(
        help_text="Settlement amount in smallest currency units (cents for USD) from Stripe event payload",
    )
    presentment_currency = models.CharField(
        max_length=3,
        blank=True,
        help_text="ISO 4217 currency code (e.g., 'eur', 'gbp') that the customer saw at checkout",
    )
    presentment_amount = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Amount in customer's currency smallest unit (e.g., cents for EUR) from presentment_details",
    )
    handled_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Stripe Event"
        verbose_name_plural = "Stripe Events"

    def __str__(self):
        return f"{self.source}:{self.stripe_event_id}"


def calculate_token_count(amount, price_per_token):
    from decimal import Decimal
    if price_per_token == Decimal("0"):
        return 0
    return int(amount // price_per_token)


def process_ourlives_checkout_completion(stripe_event_data):
    import logging

    from django.db import transaction

    logger = logging.getLogger(__name__)

    session = stripe_event_data["data"]["object"]
    metadata = session.get("metadata", {})
    presentment_details = session.get("presentment_details", {}) or {}

    if not metadata or "source" not in metadata:
        logger.warning("Webhook event missing 'source' metadata, skipping")
        return False

    source = metadata.get("source")
    token_count = int(metadata.get("token_count", 0))
    app_settings_id = metadata.get("app_settings_id")
    stripe_event_id = stripe_event_data.get("id")
    amount_cents = session.get("amount_total", 0)

    if source != "ourlives":
        logger.warning("Unknown source '%s', skipping", source)
        return False

    if StripeEvent.objects.filter(stripe_event_id=stripe_event_id).exists():
        logger.info("Duplicate webhook event %s, skipping", stripe_event_id)
        return False

    with transaction.atomic():
        settings = AppSettings.get_solo()

        if app_settings_id and str(settings.pk) != str(app_settings_id):
            logger.warning(
                "app_settings_id mismatch: metadata=%s, current=%s. Using metadata token_count.",
                app_settings_id, settings.pk,
            )

        locked = AppSettings.objects.select_for_update().get(pk=settings.pk)
        locked.total_tokens += token_count
        locked.save()

        StripeEvent.objects.create(
            stripe_event_id=stripe_event_id,
            source=source,
            token_count=token_count,
            amount_cents=amount_cents,
            presentment_currency=presentment_details.get("presentment_currency", ""),
            presentment_amount=presentment_details.get("presentment_amount"),
        )

    return True
