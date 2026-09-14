from django.contrib import admin, messages
from django.core.exceptions import ValidationError
from django.core.validators import EMPTY_VALUES
from django.shortcuts import redirect, render
from django.urls import path, reverse
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _
from solo.admin import SingletonModelAdmin
from unfold.admin import StackedInline as UnfoldStackedInline
from unfold.admin import TabularInline as UnfoldTabularInline
from unfold.contrib.filters.admin import (
    AutocompleteSelectFilter,
    DropdownFilter,
    FieldTextFilter,
    RangeDateTimeFilter,
    RelatedDropdownFilter,
)

from project.admin_base import ModelAdminUnfoldBase, OurlivesExportMixin, OurlivesModelAdminBase
from ourlives.models import AppSettings, CodeType, Contact, ContactType, Country, Currency, InvitationCode, Order, OrderItem, OrderType, Organization, OrganizationAddress, Product, Project, Rep, StripeEvent


def can_purchase(request):
    return request.user.is_staff and request.user.has_module_perms("ourlives")


@admin.register(Project)
class ProjectAdmin(OurlivesModelAdminBase):
    sidebar_icon = "folder"
    list_display = ("name", "description")
    list_display_links = ("name",)
    search_fields = ("name", "description")


class ContactInline(UnfoldStackedInline):
    model = Contact
    extra = 0
    autocomplete_fields = ("contact_type",)


class OrganizationAddressInline(UnfoldStackedInline):
    model = OrganizationAddress
    extra = 0
    autocomplete_fields = ("country",)


@admin.register(Organization)
class OrganizationAdmin(OurlivesModelAdminBase):
    sidebar_icon = "business"
    list_display = ("name", "description")
    list_display_links = ("name",)
    list_filter = ("assigned_rep",)
    search_fields = ("name", "description", "assigned_rep__first_name", "assigned_rep__last_name", "assigned_rep__email")
    inlines = (ContactInline, OrganizationAddressInline)


@admin.register(InvitationCode)
class InvitationCodeAdmin(OurlivesModelAdminBase):
    sidebar_icon = "key"
    list_display = ("code", "project", "organization", "is_active", "max_use", "current_use", "usage_percentage")
    list_display_links = ("code",)
    list_filter = ("is_active", "project", "organization", "code_type")
    search_fields = ("^code", "project__name", "organization__name", "order__order_number", "code_type__code", "code_type__name")
    search_help_text = "Search by code, project, organization, order number, or code type."
    readonly_fields = ("current_use",)
    autocomplete_fields = ("project", "organization")
    list_editable = ("is_active",)

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


@admin.register(Country)
class CountryAdmin(OurlivesModelAdminBase):
    sidebar_icon = "globe"
    list_display = ("iso2", "iso3", "name", "active")
    list_display_links = ("iso2",)
    list_filter = ("active",)
    search_fields = ("^iso2", "^iso3", "name")
    list_editable = ("active",)

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Rep)
class RepAdmin(OurlivesModelAdminBase):
    sidebar_icon = "badge"
    list_display = ("first_name", "last_name", "email")
    list_display_links = ("first_name",)
    search_fields = ("first_name", "last_name", "email")


@admin.register(ContactType)
class ContactTypeAdmin(OurlivesModelAdminBase):
    sidebar_icon = "contacts"
    list_display = ("code", "name", "active")
    list_display_links = ("code",)
    list_filter = ("active",)
    search_fields = ("^code", "name", "description")
    list_editable = ("active",)


@admin.register(CodeType)
class CodeTypeAdmin(OurlivesModelAdminBase):
    sidebar_icon = "sell"
    list_display = ("code", "name", "max_codes", "active")
    list_display_links = ("code",)
    list_filter = ("active",)
    search_fields = ("^code", "name", "description")
    list_editable = ("active",)


@admin.register(OrderType)
class OrderTypeAdmin(OurlivesModelAdminBase):
    sidebar_icon = "shopping_bag"
    list_display = ("code", "name", "active")
    list_display_links = ("code",)
    list_filter = ("active",)
    search_fields = ("^code", "name", "description")
    list_editable = ("active",)


@admin.register(Currency)
class CurrencyAdmin(OurlivesModelAdminBase):
    sidebar_icon = "payments"
    list_display = ("code", "name", "exchange_rate", "active")
    list_display_links = ("code",)
    list_filter = ("active", "countries")
    search_fields = ("^code", "name")
    list_editable = ("active",)
    filter_horizontal = ("countries",)


@admin.register(Product)
class ProductAdmin(OurlivesModelAdminBase):
    sidebar_icon = "inventory_2"
    list_display = ("name", "tier", "currency", "unit_price", "active")
    list_display_links = ("name",)
    list_filter = ("active", "tier", "currency")
    search_fields = ("name", "tier", "description")
    autocomplete_fields = ("currency",)
    list_editable = ("active",)


@admin.register(Contact)
class ContactAdmin(OurlivesModelAdminBase):
    sidebar_icon = "contact_mail"
    list_display = ("first_name", "last_name", "email", "organization", "contact_type")
    list_display_links = ("first_name",)
    list_filter = ("contact_type", "organization")
    search_fields = ("first_name", "last_name", "email", "phone", "organization__name")
    autocomplete_fields = ("organization", "contact_type")


@admin.register(OrganizationAddress)
class OrganizationAddressAdmin(OurlivesModelAdminBase):
    sidebar_icon = "location_on"
    list_display = ("organization", "line1", "city", "country", "is_primary")
    list_display_links = ("line1",)
    list_filter = ("is_primary", "country", "organization")
    search_fields = ("line1", "line2", "city", "state", "zip", "organization__name")
    autocomplete_fields = ("organization", "country")
    list_editable = ("is_primary",)


class OrderItemInline(UnfoldTabularInline):
    model = OrderItem
    extra = 0
    autocomplete_fields = ("product",)
    readonly_fields = ("line_total_display",)

    @admin.display(description="Line total")
    def line_total_display(self, obj):
        if obj.pk is None:
            return "—"
        return obj.line_total


@admin.register(OrderItem)
class OrderItemAdmin(OurlivesModelAdminBase):
    sidebar_icon = "list_alt"
    list_display = ("order", "product", "quantity", "unit_price", "line_total_display")
    list_display_links = ("order",)
    list_filter = ("product",)
    search_fields = ("^order__order_number", "product__name")
    autocomplete_fields = ("order", "product")
    readonly_fields = ("line_total_display",)

    @admin.display(description="Line total")
    def line_total_display(self, obj):
        if obj.pk is None:
            return "—"
        return obj.line_total


class OrderProductFilter(DropdownFilter):
    title = _("product")
    parameter_name = "product"

    def lookups(self, request, model_admin):
        return [(p.pk, str(p)) for p in Product.objects.order_by("name")]

    def queryset(self, request, queryset):
        if self.value() not in EMPTY_VALUES:
            return queryset.filter(items__product__id=self.value()).distinct()
        return queryset


class ActiveCurrencyDropdownFilter(RelatedDropdownFilter):
    def field_choices(self, field, request, model_admin):
        return [
            (c.pk, str(c))
            for c in field.related_model.objects.filter(active=True).order_by("code")
        ]


@admin.register(Order)
class OrderAdmin(OurlivesModelAdminBase):
    sidebar_icon = "receipt"
    list_display = ("order_number", "organization", "rep", "po_number", "total_agreed_price_display", "is_pilot_order_display", "hcaptcha_verified", "submitted_at")
    list_display_links = ("order_number",)
    list_filter = (
        ("organization", AutocompleteSelectFilter),
        ("rep", AutocompleteSelectFilter),
        ("primary_contact", AutocompleteSelectFilter),
        ("invoice_contact", AutocompleteSelectFilter),
        OrderProductFilter,
        ("submitted_at", RangeDateTimeFilter),
        ("referral_organisation", FieldTextFilter),
        "order_types",
        "hcaptcha_verified",
        "is_upgrade_from_pilot",
        "is_referral_order",
        ("currency", ActiveCurrencyDropdownFilter),
        ("pilot_currency", ActiveCurrencyDropdownFilter),
    )
    list_filter_submit = True
    search_fields = ("^order_number", "^po_number", "organization__name", "rep__first_name", "rep__last_name", "rep__email", "primary_contact__last_name", "primary_contact__email", "invoice_contact__last_name", "invoice_contact__email", "referral_organisation")
    search_help_text = "Search by order/PO number, organization, rep, billing contact, or referral."
    autocomplete_fields = ("organization", "rep", "primary_contact", "invoice_contact", "currency", "pilot_currency")
    filter_horizontal = ("order_types",)
    date_hierarchy = "submitted_at"
    list_select_related = ("organization", "rep", "primary_contact", "invoice_contact", "currency", "pilot_currency")
    inlines = (OrderItemInline,)
    readonly_fields = ("total_agreed_price_display", "is_pilot_order_display")

    def get_queryset(self, request):
        return super().get_queryset(request).prefetch_related("order_types")

    @admin.display(description="Total agreed")
    def total_agreed_price_display(self, obj):
        return obj.total_agreed_price

    @admin.display(description="Pilot", boolean=True)
    def is_pilot_order_display(self, obj):
        return obj.is_pilot_order


@admin.register(AppSettings)
class AppSettingsAdmin(SingletonModelAdmin, OurlivesExportMixin, ModelAdminUnfoldBase):
    actions_list = ["export_all"]
    actions_detail = ["export_all"]
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
        ("API Configuration", {
            "fields": ("storage_base_url",),
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

    def get_readonly_fields(self, request, obj=None):
        readonly = super().get_readonly_fields(request, obj)
        if not request.user.is_superuser:
            readonly += ("storage_base_url",)
        return readonly

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
class StripeEventAdmin(OurlivesModelAdminBase):
    sidebar_icon = "receipt_long"
    list_display = ("stripe_event_id", "source", "token_count", "amount_cents", "presentment_currency", "presentment_amount", "handled_at")
    list_filter = ("presentment_currency",)
    search_fields = ("=stripe_event_id", "source", "presentment_currency")
    search_help_text = "Search by event ID, source, or presentment currency."
    readonly_fields = ("stripe_event_id", "source", "token_count", "amount_cents", "presentment_currency", "presentment_amount", "handled_at")

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
