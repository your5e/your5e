from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from users.models import AuthToken, ProfileLink, User


class ProfileLinkInline(admin.TabularInline):
    model = ProfileLink
    extra = 1


class AuthTokenInline(admin.TabularInline):
    model = AuthToken
    extra = 0
    readonly_fields = ("token_key", "created", "expiry")
    fields = ("name", "token_key", "created", "expiry")


@admin.register(AuthToken)
class AuthTokenAdmin(admin.ModelAdmin):
    list_display = ("user", "name", "token_key", "created", "expiry")
    list_filter = ("user",)
    search_fields = ("user__username", "name")
    readonly_fields = ("token_key", "digest", "created", "expiry")


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    inlines = [ProfileLinkInline, AuthTokenInline]
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
