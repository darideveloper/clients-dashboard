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

from project.admin_base import ChangeRequestStashMixin, ModelAdminUnfoldBase, OrderSummaryAdminMixin, OurlivesExportMixin, OurlivesModelAdminBase, paginate_related, plural, related_footer, related_list, related_rows
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
class OrganizationAdmin(ChangeRequestStashMixin, OrderSummaryAdminMixin, OurlivesModelAdminBase):
    sidebar_icon = "business"
    list_display = ("name", "description") + OrderSummaryAdminMixin.order_summary_displays
    list_display_links = ("name",)
    list_filter = ("assigned_rep",)
    search_fields = ("name", "description", "assigned_rep__first_name", "assigned_rep__last_name", "assigned_rep__email")
    inlines = (ContactInline, OrganizationAddressInline)
    fieldsets = (
        (None, {"fields": ("name", "description", "assigned_rep")}),
        ("Order summary", {"fields": OrderSummaryAdminMixin.order_summary_displays}),
        ("Orders", {"fields": ("orders_list",)}),
        ("Codes across orders", {"fields": ("codes_across_orders_list",)}),
        ("Codes (direct)", {"fields": ("codes_direct_list",)}),
    )
    readonly_fields = OrderSummaryAdminMixin.order_summary_displays + ("orders_list", "codes_across_orders_list", "codes_direct_list")

    @admin.display(description="Orders")
    def orders_list(self, obj):
        if obj is None or obj.pk is None:
            return "—"
        request = getattr(self, "_change_request", None)
        total = obj.orders.count()
        if total == 0:
            return "No orders yet"
        if request is not None and not request.user.has_perm("ourlives.view_order"):
            return f"{plural(total, 'order')}"
        page = paginate_related(
            self, obj.orders.order_by("order_number"), "org_orders_page"
        )
        rows = related_rows(
            format_html(
                '<a href="{}">{} — {} — {}</a>',
                reverse("admin:ourlives_order_change", args=[o.pk]),
                o.order_number,
                o.po_number,
                o.total_agreed_price,
            )
            for o in page.object_list
        )
        view_all = (
            reverse("admin:ourlives_order_changelist")
            + f"?organization__id__exact={obj.pk}"
        )
        return related_list(rows, related_footer(self, obj, page, "org_orders_page", view_all, f"View all {plural(total, 'order')}"))

    def _org_codes_list(self, obj, queryset, page_key, view_all_query):
        if obj is None or obj.pk is None:
            return "—"
        request = getattr(self, "_change_request", None)
        qs = queryset.select_related("project", "code_type").order_by("code")
        total = qs.count()
        if total == 0:
            return "No codes yet"
        if request is not None and not request.user.has_perm("ourlives.view_invitationcode"):
            return f"{plural(total, 'code')}"
        page = paginate_related(self, qs, page_key)
        rows = related_rows(
            format_html(
                '<a href="{}">{}</a> — {} — {} — {}/{}',
                reverse("admin:ourlives_invitationcode_change", args=[c.pk]),
                c.code,
                c.project.name,
                c.code_type.name if c.code_type is not None else "—",
                c.current_use, c.max_use,
            )
            for c in page.object_list
        )
        view_all = (
            reverse("admin:ourlives_invitationcode_changelist") + view_all_query
        )
        return related_list(rows, related_footer(self, obj, page, page_key, view_all, f"View all {plural(total, 'code')}"))

    @admin.display(description="Codes across orders")
    def codes_across_orders_list(self, obj):
        if obj is None or obj.pk is None:
            return "—"
        return self._org_codes_list(
            obj,
            InvitationCode.objects.filter(order__organization=obj),
            "org_order_codes_page",
            f"?order__organization__id__exact={obj.pk}",
        )

    @admin.display(description="Codes (direct)")
    def codes_direct_list(self, obj):
        if obj is None or obj.pk is None:
            return "—"
        return self._org_codes_list(
            obj,
            InvitationCode.objects.filter(organization=obj),
            "org_codes_page",
            f"?organization__id__exact={obj.pk}",
        )


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
class RepAdmin(ChangeRequestStashMixin, OrderSummaryAdminMixin, OurlivesModelAdminBase):
    sidebar_icon = "badge"
    list_display = ("first_name", "last_name", "email") + OrderSummaryAdminMixin.order_summary_displays
    list_display_links = ("first_name",)
    search_fields = ("first_name", "last_name", "email")
    fieldsets = (
        (None, {"fields": ("first_name", "last_name", "email")}),
        ("Order summary", {"fields": OrderSummaryAdminMixin.order_summary_displays}),
        ("Companies", {"fields": ("companies_list",)}),
        ("Orders", {"fields": ("orders_list",)}),
    )
    readonly_fields = OrderSummaryAdminMixin.order_summary_displays + ("companies_list", "orders_list")

    def get_queryset(self, request):
        return super().get_queryset(request).prefetch_related("organizations", "orders")

    @admin.display(description="Companies")
    def companies_list(self, obj):
        if obj is None or obj.pk is None:
            return "—"
        request = getattr(self, "_change_request", None)
        total = obj.organizations.count()
        if total == 0:
            return "No companies yet"
        if request is not None and not request.user.has_perm("ourlives.view_organization"):
            return f"{plural(total, 'company', 'companies')}"
        page = paginate_related(
            self, obj.organizations.order_by("name"), "rep_companies_page"
        )
        rows = related_rows(
            format_html(
                '<a href="{}">{}</a>',
                reverse("admin:ourlives_organization_change", args=[o.pk]),
                o.name,
            )
            for o in page.object_list
        )
        view_all = (
            reverse("admin:ourlives_organization_changelist")
            + f"?assigned_rep__id__exact={obj.pk}"
        )
        return related_list(rows, related_footer(self, obj, page, "rep_companies_page", view_all, f"View all {plural(total, 'company', 'companies')}"))

    @admin.display(description="Orders")
    def orders_list(self, obj):
        if obj is None or obj.pk is None:
            return "—"
        request = getattr(self, "_change_request", None)
        total = obj.orders.count()
        if total == 0:
            return "No orders yet"
        if request is not None and not request.user.has_perm("ourlives.view_order"):
            return f"{plural(total, 'order')}"
        page = paginate_related(
            self,
            obj.orders.select_related("organization").order_by("order_number"),
            "rep_orders_page",
        )
        rows = related_rows(
            format_html(
                '<a href="{}">{} — {}</a>',
                reverse("admin:ourlives_order_change", args=[o.pk]),
                o.order_number,
                o.organization.name,
            )
            for o in page.object_list
        )
        view_all = (
            reverse("admin:ourlives_order_changelist") + f"?rep__id__exact={obj.pk}"
        )
        return related_list(rows, related_footer(self, obj, page, "rep_orders_page", view_all, f"View all {plural(total, 'order')}"))


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
class OrderAdmin(ChangeRequestStashMixin, OurlivesModelAdminBase):
    sidebar_icon = "receipt"
    list_display = ("order_number", "organization", "rep", "po_number", "total_agreed_price_display", "submitted_at")
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
    fieldsets = (
        ("Order", {
            "fields": (
                "order_number", "organization", "rep", "primary_contact",
                "invoice_contact", "order_types", "currency", "pilot_currency",
                "po_number", "number_of_scans", "cost_per_scan",
            ),
        }),
        ("Terms", {
            "fields": (
                "is_upgrade_from_pilot", "is_referral_order", "referral_organisation",
                "hcaptcha_verified", "is_pilot_order_display",
                "total_agreed_price_display", "submitted_at",
            ),
        }),
        ("Billing", {
            "fields": (
                ("invoice_sent", "invoice_sent_on"),
                ("invoice_paid", "invoice_paid_on"),
                ("commission_paid", "commission_paid_on"),
                "rep_commission_note",
            ),
        }),
        ("Details", {
            "fields": ("additional_information", "ip_address", "form_entry_key"),
        }),
        ("Related", {
            "fields": ("organization_card", "rep_card", "contacts_list", "codes_list"),
        }),
    )
    readonly_fields = (
        "total_agreed_price_display", "is_pilot_order_display", "submitted_at",
        "organization_card", "rep_card", "contacts_list", "codes_list",
    )

    def get_queryset(self, request):
        return (
            super().get_queryset(request)
            .select_related(
                "organization", "rep", "primary_contact", "invoice_contact",
                "currency", "pilot_currency",
            )
            .prefetch_related("order_types")
        )

    @admin.display(description="Total agreed")
    def total_agreed_price_display(self, obj):
        return obj.total_agreed_price

    @admin.display(description="Pilot", boolean=True)
    def is_pilot_order_display(self, obj):
        return obj.is_pilot_order

    @admin.display(description="Company")
    def organization_card(self, obj):
        if obj is None or obj.pk is None or obj.organization_id is None:
            return "—"
        org = obj.organization
        request = getattr(self, "_change_request", None)
        if request is not None and not request.user.has_perm("ourlives.view_organization"):
            return format_html("{} (details restricted)", str(org))
        change_url = reverse("admin:ourlives_organization_change", args=[org.pk])
        address = org.addresses.filter(is_primary=True).first() or org.addresses.order_by("pk").first()
        counts = (
            f"{org.contacts.count()} contacts · "
            f"{org.orders.count()} orders · "
            f"{InvitationCode.objects.filter(organization=org).count()} codes"
        )
        if address is None:
            return format_html(
                '<a href="{}">{}</a><br>{}<br><a href="{}">Open company →</a>',
                change_url, str(org), counts, change_url,
            )
        return format_html(
            '<a href="{}">{}</a><br>{}, {}<br>{}<br><a href="{}">Open company →</a>',
            change_url, str(org), address.line1, address.city,
            counts, change_url,
        )

    @admin.display(description="Rep")
    def rep_card(self, obj):
        if obj is None or obj.pk is None or obj.rep is None:
            return "—"
        rep = obj.rep
        request = getattr(self, "_change_request", None)
        if request is not None and not request.user.has_perm("ourlives.view_rep"):
            return format_html("{} (details restricted)", str(rep))
        change_url = reverse("admin:ourlives_rep_change", args=[rep.pk])
        return format_html(
            '<a href="{}">{}</a><br><a href="mailto:{}">{}</a>'
            "<br>{} companies · {} orders<br>"
            '<a href="{}">Open rep →</a>',
            change_url, str(rep), rep.email, rep.email,
            rep.organizations.count(), rep.orders.count(), change_url,
        )

    @admin.display(description="All organization contacts")
    def contacts_list(self, obj):
        if obj is None or obj.pk is None or obj.organization_id is None:
            return "—"
        request = getattr(self, "_change_request", None)
        qs = (
            obj.organization.contacts.select_related("contact_type")
            .order_by("last_name", "first_name")
        )
        total = qs.count()
        if total == 0:
            return "No contacts yet"
        if request is not None and not request.user.has_perm("ourlives.view_contact"):
            return f"{plural(total, 'contact')}"
        page = paginate_related(self, qs, "order_contacts_page")
        rows = related_rows(
            format_html(
                '<a href="{}">{} {}</a> — {} — {} — {}{}',
                reverse("admin:ourlives_contact_change", args=[c.pk]),
                c.first_name, c.last_name,
                c.contact_type.name, c.email, c.phone,
                format_html(
                    "{}{}",
                    " (primary)" if c.pk == obj.primary_contact_id else "",
                    " (invoice)" if c.pk == obj.invoice_contact_id else "",
                ),
            )
            for c in page.object_list
        )
        view_all = (
            reverse("admin:ourlives_contact_changelist")
            + f"?organization__id__exact={obj.organization_id}"
        )
        return related_list(rows, related_footer(self, obj, page, "order_contacts_page", view_all, f"View all {plural(total, 'contact')}"))

    @admin.display(description="Codes")
    def codes_list(self, obj):
        if obj is None or obj.pk is None:
            return "—"
        request = getattr(self, "_change_request", None)
        qs = obj.invitation_codes.select_related("project", "code_type").order_by("code")
        total = qs.count()
        if total == 0:
            return "No codes yet"
        if request is not None and not request.user.has_perm("ourlives.view_invitationcode"):
            return f"{plural(total, 'code')}"
        page = paginate_related(self, qs, "order_codes_page")
        rows = related_rows(
            format_html(
                '<a href="{}">{}</a> — {} — {} — {}/{}',
                reverse("admin:ourlives_invitationcode_change", args=[c.pk]),
                c.code,
                c.project.name,
                c.code_type.name if c.code_type is not None else "—",
                c.current_use, c.max_use,
            )
            for c in page.object_list
        )
        view_all = (
            reverse("admin:ourlives_invitationcode_changelist")
            + f"?order__id__exact={obj.pk}"
        )
        return related_list(rows, related_footer(self, obj, page, "order_codes_page", view_all, f"View all {plural(total, 'code')}"))


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
