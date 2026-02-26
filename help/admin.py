from django.contrib import admin

from help.models import HelpWiki
from wikis.admin import PageInline


@admin.register(HelpWiki)
class HelpWikiAdmin(admin.ModelAdmin):
    inlines = [PageInline]
