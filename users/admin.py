from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from users.models import User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = (
        "username",
        "email",
        "name",
        "short_name",
        "is_staff",
    )
    search_fields = (
        "username",
        "email",
        "name",
        "short_name",
    )
    ordering = ("username",)

    fieldsets = (
        (
            None, {
                "fields": ("username", "password"),
            },
        ),
        (
            "Personal info", {
                "fields": ("email", "name", "short_name"),
            },
        ),
        (
            "Permissions", {
                "fields": (
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                ),
            },
        ),
        (
            "Important dates", {
                "fields": ("last_login", "date_joined"),
            },
        ),
    )

    add_fieldsets = (
        (
            None, {
                "classes": ("wide",),
                "fields": ("username", "email", "password1", "password2"),
            },
        ),
    )
