from django.contrib import admin, messages
from django.core.exceptions import ValidationError
from django.shortcuts import redirect, render
from django.urls import path, reverse
from django.utils.html import format_html
from solo.admin import SingletonModelAdmin

from project.admin_base import ModelAdminUnfoldBase
from ourlives.models import AppSettings, InvitationCode, Organization, Project, StripeEvent


def can_purchase(request):
    return request.user.is_staff and request.user.has_module_perms("ourlives")


@admin.register(Project)
class ProjectAdmin(ModelAdminUnfoldBase):
    sidebar_icon = "folder"
    list_display = ("name", "description")
    list_display_links = ("name",)
    search_fields = ("name",)


@admin.register(Organization)
class OrganizationAdmin(ModelAdminUnfoldBase):
    sidebar_icon = "business"
    list_display = ("name", "description")
    list_display_links = ("name",)
    search_fields = ("name",)


@admin.register(InvitationCode)
class InvitationCodeAdmin(ModelAdminUnfoldBase):
    sidebar_icon = "key"
    list_display = ("code", "project", "organization", "is_active", "max_use", "current_use", "usage_percentage")
    list_display_links = ("code",)
    list_filter = ("is_active", "project", "organization")
    search_fields = ("code", "project__name", "organization__name")
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
        ("Stripe", {
            "fields": ("stripe_product_id", "stripe_price_id", "sync_stripe_price_link"),
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
        "stripe_product_id",
        "stripe_price_id",
        "sync_stripe_price_link",
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

    @admin.display(description="Stripe Price Sync")
    def sync_stripe_price_link(self, obj):
        if not self.request.user.is_superuser:
            return "-"
        url = reverse("admin:sync-stripe-price")
        return format_html('<a href="{}" class="bg-primary-600 border border-transparent cursor-pointer font-medium inline-flex items-center px-3 py-2 rounded-default text-white hover:bg-primary-600/80">Run Sync Stripe Price</a>', url)

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path("purchase/", self.admin_site.admin_view(self.purchase_view), name="ourlives_appsettings_purchase"),
            path("sync-stripe-price/", self.admin_site.admin_view(self.sync_stripe_price_view), name="sync-stripe-price"),
        ]
        return custom_urls + urls

    def sync_stripe_price_view(self, request):
        if not request.user.is_superuser:
            from django.http import HttpResponseForbidden
            return HttpResponseForbidden("Access denied")

        from django.core.management import call_command
        from io import StringIO

        out = StringIO()
        call_command("sync_stripe_price", stdout=out)
        messages.success(request, out.getvalue())
        return redirect("admin:ourlives_appsettings_change")

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
            "is_configured": settings.price_per_token is not None and settings.price_per_token > 0,
        }
        return render(request, "admin/ourlives/purchase.html", context)


@admin.register(StripeEvent)
class StripeEventAdmin(ModelAdminUnfoldBase):
    sidebar_icon = "receipt_long"
    list_display = ("stripe_event_id", "source", "token_count", "amount_cents", "presentment_currency", "presentment_amount", "handled_at")
    list_filter = ("presentment_currency",)
    readonly_fields = ("stripe_event_id", "source", "token_count", "amount_cents", "presentment_currency", "presentment_amount", "handled_at")

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
