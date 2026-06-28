from django.contrib import admin

DEFAULT_SIDEBAR_ICON = "database"


def build_sidebar_icon_map() -> dict[str, str]:
    return {
        model._meta.label_lower: getattr(
            model_admin, "sidebar_icon", DEFAULT_SIDEBAR_ICON
        )
        for model, model_admin in admin.site._registry.items()
        if hasattr(model, "_meta")
    }
