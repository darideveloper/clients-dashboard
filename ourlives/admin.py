from django.contrib import admin, messages
from django.core.exceptions import ValidationError
from solo.admin import SingletonModelAdmin

from project.admin_base import ModelAdminUnfoldBase
from ourlives.models import AppSettings, InvitationCode, Project


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
