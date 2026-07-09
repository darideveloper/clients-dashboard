from django.contrib import admin, messages
from django.core.exceptions import ValidationError
from django.shortcuts import render
from django.urls import path
from solo.admin import SingletonModelAdmin

from project.admin_base import ModelAdminUnfoldBase
from ourlives.models import AppSettings, InvitationCode, Project, StripeEvent


def can_purchase(request):
    return request.user.is_staff and request.user.has_module_perms("ourlives")


@admin.register(Project)
class ProjectAdmin(ModelAdminUnfoldBase):
    sidebar_icon = "folder"
    list_display = ("name", "description")
    list_display_links = ("name",)
    search_fields = ("name",)


@admin.register(InvitationCode)
class InvitationCodeAdmin(ModelAdminUnfoldBase):
    sidebar_icon = "key"
    list_display = ("code", "project", "is_active", "max_use", "current_use", "usage_percentage")
    list_display_links = ("code",)
    list_filter = ("is_active", "project")
    search_fields = ("code", "project__name")
    readonly_fields = ("current_use",)

    @admin.display(description="Usage %")
    def usage_percentage(self, obj):
        if obj.max_use == 0:
            return "\u2014"
        return f"{obj.current_use / obj.max_use * 100:.0f}%"

    def save_model(self, request, obj, form, change):
        try:
            super().save_model(request, obj, form, change)
        except ValidationError as e:
            self.message_user(request, str(e), messages.ERROR)


@admin.register(AppSettings)
class AppSettingsAdmin(SingletonModelAdmin, ModelAdminUnfoldBase):
    sidebar_icon = "settings"
    fieldsets = (
        ("Token Pool", {
            "fields": ("total_tokens",),
        }),
        ("Pricing", {
            "fields": ("price_per_token", "min_purchase_amount"),
        }),
        ("Status", {
            "fields": (
                "tokens_assigned_display",
                "tokens_used_display",
                "tokens_available_display",
            ),
        }),
    )
    readonly_fields = (
        "tokens_assigned_display",
        "tokens_used_display",
        "tokens_available_display",
    )

    @admin.display(description="Tokens Assigned")
    def tokens_assigned_display(self, obj):
        return obj.tokens_assigned

    @admin.display(description="Tokens Used")
    def tokens_used_display(self, obj):
        return obj.tokens_used

    @admin.display(description="Tokens Available")
    def tokens_available_display(self, obj):
        return obj.tokens_available

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path("purchase/", self.admin_site.admin_view(self.purchase_view), name="ourlives_appsettings_purchase"),
        ]
        return custom_urls + urls

    def purchase_view(self, request):
        if not request.user.has_module_perms("ourlives"):
            from django.http import HttpResponseForbidden
            return HttpResponseForbidden("Access denied")

        settings = AppSettings.get_solo()

        context = {
            "opts": self.model._meta,
            "settings": settings,
            "price_per_token": float(settings.price_per_token) if settings.price_per_token else 0,
            "min_purchase_amount": float(settings.min_purchase_amount) if settings.min_purchase_amount else 0,
            "total_tokens": settings.total_tokens,
            "tokens_available": settings.tokens_available,
            "is_configured": settings.price_per_token and settings.price_per_token > 0,
        }
        return render(request, "admin/ourlives/purchase.html", context)


@admin.register(StripeEvent)
class StripeEventAdmin(ModelAdminUnfoldBase):
    sidebar_icon = "receipt_long"
    list_display = ("stripe_event_id", "source", "token_count", "amount_cents", "handled_at")
    readonly_fields = ("stripe_event_id", "source", "token_count", "amount_cents", "handled_at")

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
