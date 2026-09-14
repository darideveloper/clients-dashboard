from datetime import datetime
from io import BytesIO
from urllib.parse import quote

from django.contrib import admin, messages
from django.core.paginator import Paginator
from django.db.models import Count, Max
from django.http import HttpResponse, QueryDict
from django.shortcuts import redirect
from django.urls import reverse
from django.utils.html import format_html, format_html_join
from unfold.admin import ModelAdmin
from unfold.decorators import action


RELATED_PAGE_SIZE = 25


def plural(count, singular, plural_form=None):
    if count == 1:
        return f"{count} {singular}"
    return f"{count} {plural_form or singular + 's'}"


class ChangeRequestStashMixin:
    """Stash the change-view request so @admin.display methods can paginate.

    Display methods only receive `(obj)`; the stashed request exposes
    `request.GET` page keys and `request.user` for permission guards.
    Falls back to page 1 / unrestricted rendering when absent (add view).
    """

    def change_view(self, request, object_id, form_url="", extra_context=None):
        self._change_request = request
        return super().change_view(
            request, object_id, form_url=form_url, extra_context=extra_context
        )


def paginate_related(admin_instance, queryset, page_key, per_page=RELATED_PAGE_SIZE):
    """Return a page for a related list; invalid input degrades, never raises."""
    request = getattr(admin_instance, "_change_request", None)
    try:
        number = int((request.GET.get(page_key) if request is not None else 1) or 1)
    except (TypeError, ValueError):
        number = 1
    return Paginator(queryset, per_page).get_page(number)


def related_footer(admin_instance, parent, page, page_key, view_all_url, view_all_label):
    """Prev/next + "Page X of Y" + view-all footer for a related list."""
    request = getattr(admin_instance, "_change_request", None)

    def page_url(number):
        params = request.GET.copy() if request is not None else QueryDict(mutable=True)
        params[page_key] = number
        opts = parent._meta
        base = reverse(
            f"admin:{opts.app_label}_{opts.model_name}_change", args=[parent.pk]
        )
        return f"{base}?{params.urlencode()}"

    nav = ""
    if page.paginator.num_pages > 1:
        prev_link = (
            format_html('<a href="{}">← previous</a>', page_url(page.previous_page_number()))
            if page.has_previous()
            else "← previous"
        )
        next_link = (
            format_html('<a href="{}">next →</a>', page_url(page.next_page_number()))
            if page.has_next()
            else "next →"
        )
        nav = format_html(
            "Page {} of {} &nbsp; {} &nbsp; {} &nbsp; ",
            page.number,
            page.paginator.num_pages,
            prev_link,
            next_link,
        )
    return format_html(
        '<p class="paginator">{nav}<a href="{url}">{label} →</a></p>',
        nav=nav,
        url=view_all_url,
        label=view_all_label,
    )


def related_list(rows_html, footer_html):
    return format_html("<ul>{}</ul>{}", rows_html, footer_html)


def related_rows(items_html):
    return format_html_join("", "<li>{}</li>", ((item,) for item in items_html))


def _excel_response(workbook, filename):
    buf = BytesIO()
    workbook.save(buf)
    buf.seek(0)
    response = HttpResponse(
        buf.getvalue(),
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
    quoted = quote(filename)
    response["Content-Disposition"] = f'attachment; filename="{filename}"; filename*=utf-8\'\'{quoted}'
    return response


class ModelAdminUnfoldBase(ModelAdmin):
    sidebar_icon = "database"
    compressed_fields = True
    warn_unsaved_form = True
    list_filter_sheet = False
    change_form_show_cancel_button = True

    actions_row = ["edit"]
    actions = ["export_selected", "export_selected_with_related"]

    @action(description="Edit", permissions=["change"])
    def edit(self, request, object_id):
        return redirect(
            reverse(
                f"admin:{self.model._meta.app_label}_{self.model._meta.model_name}_change",
                args=[object_id],
            )
        )

    @action(description="Export to Excel", icon="download", permissions=["view"])
    def export_selected(self, request, queryset):
        if not queryset.exists():
            self.message_user(request, "Select at least one row to export.", messages.WARNING)
            return None
        from utils.excel_export import build_workbook_for_queryset

        wb = build_workbook_for_queryset(self.model, queryset, include_related=False)
        ts = datetime.now().strftime("%Y%m%d_%H%M")
        filename = f"{self.model._meta.model_name}_{ts}.xlsx"
        return _excel_response(wb, filename)

    def has_export_selected_permission(self, request, obj=None):
        return self.has_view_permission(request, obj)

    @action(description="Export to Excel (with related)", icon="download", permissions=["view"])
    def export_selected_with_related(self, request, queryset):
        if not queryset.exists():
            self.message_user(request, "Select at least one row to export.", messages.WARNING)
            return None
        from utils.excel_export import build_workbook_for_queryset

        wb = build_workbook_for_queryset(self.model, queryset, include_related=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M")
        filename = f"{self.model._meta.model_name}_with_related_{ts}.xlsx"
        return _excel_response(wb, filename)

    def has_export_selected_with_related_permission(self, request, obj=None):
        return self.has_view_permission(request, obj)


class OurlivesExportMixin:
    @action(description="Export all app data", icon="download", permissions=["export_all"])
    def export_all(self, request, object_id=None, *args, **kwargs):
        from utils.excel_export import build_full_app_workbook

        wb = build_full_app_workbook()
        ts = datetime.now().strftime("%Y%m%d_%H%M")
        filename = f"ourlives_full_export_{ts}.xlsx"
        return _excel_response(wb, filename)

    def has_export_all_permission(self, request, obj=None, *args, **kwargs):
        user = getattr(request, "user", None)
        if not user or not getattr(user, "is_staff", False):
            return False
        return user.has_module_perms("ourlives")


class OurlivesModelAdminBase(OurlivesExportMixin, ModelAdminUnfoldBase):
    actions_list = ["export_all"]
    # Also expose on detail view for singletons (AppSettings)
    actions_detail = ["export_all"]


class OrderSummaryAdminMixin:
    """Per-currency order summaries for Organization/Rep admins.

    - `get_queryset` annotates sortable `_order_count` / `_last_order_date`.
    - `changelist_view` bulk-attaches money breakdowns (constant queries).
    - Display methods prefer precomputed data, fall back to model properties
      (detail view, unsaved instances).
    - `get_form` injects per-field help texts so they render under readonly
      summary fields (Django only shows help for readonly via form Meta).
    """

    order_summary_displays = (
        "order_count_display",
        "agreed_scans_total_display",
        "catalog_items_total_display",
        "combined_total_display",
        "last_order_date_display",
    )

    def get_queryset(self, request):
        return (
            super()
            .get_queryset(request)
            .annotate(_order_count=Count("orders", distinct=True), _last_order_date=Max("orders__submitted_at"))
        )

    def changelist_view(self, request, extra_context=None):
        response = super().changelist_view(request, extra_context)
        try:
            result_list = list(response.context_data["cl"].result_list)
        except (AttributeError, KeyError, TypeError):
            return response
        from ourlives.models import attach_money_breakdowns

        attach_money_breakdowns(result_list)
        return response

    def get_form(self, request, obj=None, change=False, **kwargs):
        form = super().get_form(request, obj, change=change, **kwargs)
        from ourlives.models import ORDER_SUMMARY_HELP_TEXTS

        form._meta.help_texts = {
            **(getattr(form._meta, "help_texts", None) or {}),
            **{f"{name}_display": text for name, text in ORDER_SUMMARY_HELP_TEXTS.items()},
        }
        return form

    @admin.display(description="Orders", ordering="_order_count")
    def order_count_display(self, obj):
        if obj is None:
            return 0
        value = getattr(obj, "_order_count", None)
        return obj.order_count if value is None else value

    def _breakdown_display(self, obj, annotated_name, prop_name):
        from ourlives.models import format_currency_breakdown

        if obj is None:
            return format_currency_breakdown({})
        breakdown = getattr(obj, annotated_name, None)
        if breakdown is None:
            breakdown = getattr(obj, prop_name)
        return format_currency_breakdown(breakdown)

    @admin.display(description="Agreed scans total")
    def agreed_scans_total_display(self, obj):
        return self._breakdown_display(obj, "_agreed_scans_total", "agreed_scans_total")

    @admin.display(description="Catalog items total")
    def catalog_items_total_display(self, obj):
        return self._breakdown_display(obj, "_catalog_items_total", "catalog_items_total")

    @admin.display(description="Combined total")
    def combined_total_display(self, obj):
        return self._breakdown_display(obj, "_combined_total", "combined_total")

    @admin.display(description="Last order", ordering="_last_order_date")
    def last_order_date_display(self, obj):
        if obj is None:
            return None
        value = getattr(obj, "_last_order_date", None)
        return obj.last_order_date if value is None else value
