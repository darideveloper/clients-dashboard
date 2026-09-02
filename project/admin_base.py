from datetime import datetime
from io import BytesIO
from urllib.parse import quote

from django.contrib import messages
from django.http import HttpResponse
from django.shortcuts import redirect
from django.urls import reverse
from unfold.admin import ModelAdmin
from unfold.decorators import action


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
