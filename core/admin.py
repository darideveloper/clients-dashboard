from django.contrib import admin
from django.contrib.auth.admin import GroupAdmin as BaseGroupAdmin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import Group, User
from django.db import models
from django.utils.html import format_html

from core.models import Profile
from project.admin_base import ModelAdminUnfoldBase
from unfold.forms import AdminPasswordChangeForm, UserChangeForm, UserCreationForm
from unfold.widgets import UnfoldAdminColorInputWidget

admin.site.unregister(User)
admin.site.unregister(Group)


@admin.register(Profile)
class ProfileAdmin(ModelAdminUnfoldBase):
    list_display = ("user", "has_avatar", "primary_color")
    list_display_links = ("user",)
    formfield_overrides = {
        models.CharField: {"widget": UnfoldAdminColorInputWidget},
    }

    @admin.display(boolean=True, description="Has avatar")
    def has_avatar(self, obj):
        return bool(obj.avatar)


class ProfileInline(admin.StackedInline):
    model = Profile
    can_delete = False
    verbose_name_plural = "Profile"
    fields = ("avatar", "primary_color")
    formfield_overrides = {
        models.CharField: {"widget": UnfoldAdminColorInputWidget},
    }


@admin.register(User)
class UserAdmin(BaseUserAdmin, ModelAdminUnfoldBase):
    form = UserChangeForm
    add_form = UserCreationForm
    change_password_form = AdminPasswordChangeForm
    inlines = [ProfileInline]
    list_display = ("username", "email", "first_name", "is_staff", "avatar_thumb")
    list_display_links = ("username", "email")

    @admin.display(description="Avatar")
    def avatar_thumb(self, obj):
        url = obj.avatar_url
        if not url:
            return "—"
        return format_html(
            '<img src="{}" style="height:32px;width:32px;border-radius:50%;object-fit:cover;">',
            url,
        )


@admin.register(Group)
class GroupAdmin(BaseGroupAdmin, ModelAdminUnfoldBase):
    pass
