from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from users.models import ProfileLink, User


class ProfileLinkInline(admin.TabularInline):
    model = ProfileLink
    extra = 1


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    inlines = [ProfileLinkInline]
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
                "fields": ("email", "name", "short_name", "description"),
            },
        ),
        (
            "Profile", {
                "fields": ("is_public",),
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
