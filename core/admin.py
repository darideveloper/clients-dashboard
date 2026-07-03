from django.contrib import admin
from django.contrib.auth.admin import GroupAdmin as BaseGroupAdmin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import Group, User
from django.utils.html import format_html
from rest_framework.authtoken.admin import TokenAdmin as BaseTokenAdmin
from rest_framework.authtoken.models import TokenProxy

from core.models import Brand, Membership
from project.admin_base import ModelAdminUnfoldBase
from unfold.admin import StackedInline as UnfoldStackedInline
from unfold.forms import AdminPasswordChangeForm, UserChangeForm, UserCreationForm
from unfold.widgets import UnfoldAdminColorInputWidget

admin.site.unregister(User)
admin.site.unregister(Group)
admin.site.unregister(TokenProxy)


@admin.register(Brand)
class BrandAdmin(ModelAdminUnfoldBase):
    sidebar_icon = "brand_family"
    list_display = ("logo_thumb", "name", "primary_color", "is_default", "user_count")
    list_display_links = ("name",)
    fields = ("name", "slug", "logo", "primary_color", "is_default")

    def formfield_for_dbfield(self, db_field, **kwargs):
        if db_field.name == "primary_color":
            kwargs["widget"] = UnfoldAdminColorInputWidget
        return super().formfield_for_dbfield(db_field, **kwargs)

    @admin.display(description="Logo")
    def logo_thumb(self, obj):
        try:
            url = obj.logo.url if obj.logo else None
        except (ValueError, AttributeError):
            url = None
        if not url:
            return "—"
        return format_html(
            '<img src="{}" style="height:32px;width:32px;border-radius:4px;object-fit:cover;">',
            url,
        )

    @admin.display(description="Users")
    def user_count(self, obj):
        return obj.memberships.count()

    def has_add_permission(self, request):
        return request.user.is_superuser

    def has_change_permission(self, request, obj=None):
        return request.user.is_superuser

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser


class MembershipInline(UnfoldStackedInline):
    model = Membership
    can_delete = False
    verbose_name_plural = "Brand"
    fields = ("brand",)

    def has_add_permission(self, request, obj=None):
        return request.user.is_superuser

    def has_change_permission(self, request, obj=None):
        return request.user.is_superuser

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser


@admin.register(User)
class UserAdmin(BaseUserAdmin, ModelAdminUnfoldBase):
    sidebar_icon = "person"
    form = UserChangeForm
    add_form = UserCreationForm
    change_password_form = AdminPasswordChangeForm
    list_display = ("username", "email", "first_name", "is_staff", "brand_display")
    list_display_links = ("username", "email")

    def get_inlines(self, request, obj):
        if request.user.is_superuser:
            return [MembershipInline]
        return []

    @admin.display(description="Brand")
    def brand_display(self, obj):
        brand = getattr(obj, "brand", None)
        return brand.name if brand else "—"

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        if not change and getattr(obj, "brand", None) is None:
            obj.brand = Brand.get_or_create_default()


@admin.register(Group)
class GroupAdmin(BaseGroupAdmin, ModelAdminUnfoldBase):
    sidebar_icon = "group"


@admin.register(TokenProxy)
class TokenAdmin(BaseTokenAdmin):
    sidebar_icon = "key"
