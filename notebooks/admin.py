from django.contrib import admin

from notebooks.models import Notebook, NotebookPermission
from wikis.admin import PageInline


@admin.register(Notebook)
class NotebookAdmin(admin.ModelAdmin):
    list_display = ["name", "slug", "owner", "visibility"]
    list_filter = ["visibility", "owner"]
    search_fields = ["name", "slug", "owner__username"]
    autocomplete_fields = ["owner", "copied_from"]
    inlines = [PageInline]


@admin.register(NotebookPermission)
class NotebookPermissionAdmin(admin.ModelAdmin):
    list_display = ["notebook", "user", "role"]
    list_filter = ["role"]
