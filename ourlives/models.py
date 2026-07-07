import uuid

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
