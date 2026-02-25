from django.contrib import admin

from help.models import HelpWiki


@admin.register(HelpWiki)
class HelpWikiAdmin(admin.ModelAdmin):
    pass
