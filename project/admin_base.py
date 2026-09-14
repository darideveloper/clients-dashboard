from datetime import datetime
from io import BytesIO
from urllib.parse import quote

from django.contrib import messages
from django.core.paginator import Paginator
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
