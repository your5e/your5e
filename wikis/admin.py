from django.contrib import admin

from wikis.models import Content, Page, Version, Wiki


class PageInline(admin.TabularInline):
    model = Page
    extra = 0
    show_change_link = True
    fields = ("name", "deleted_at")
    readonly_fields = ("name",)

    @admin.display(description="Page")
    def name(self, obj):
        return str(obj)


class VersionInline(admin.TabularInline):
    model = Version
    extra = 0
    show_change_link = True
    can_delete = False
    max_num = 0
    fields = ("filename", "path", "number", "created_by", "created_at")
    readonly_fields = ("filename", "path", "number", "created_by", "created_at")


@admin.register(Wiki)
class WikiAdmin(admin.ModelAdmin):
    inlines = [PageInline]


@admin.register(Page)
class PageAdmin(admin.ModelAdmin):
    list_display = ("__str__", "wiki", "deleted_at")
    list_filter = ("wiki", "deleted_at")
    inlines = [VersionInline]


@admin.register(Version)
class VersionAdmin(admin.ModelAdmin):
    list_display = ("filename", "number", "page", "wiki", "created_at")
    list_filter = ("page__wiki",)
    search_fields = ("filename", "path")
    readonly_fields = ("number", "path", "created_at")

    @admin.display(description="Wiki")
    def wiki(self, obj):
        return obj.page.wiki


@admin.register(Content)
class ContentAdmin(admin.ModelAdmin):
    list_display = ("hash",)
    search_fields = ("hash",)
