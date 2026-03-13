from django.contrib import admin

from campaigns.models import Campaign, CampaignNotebook


@admin.register(Campaign)
class CampaignAdmin(admin.ModelAdmin):
    list_display = ["name", "owner", "slug"]
    list_filter = ["owner"]
    search_fields = ["name", "owner__username"]
    filter_horizontal = ["players"]


@admin.register(CampaignNotebook)
class CampaignNotebookAdmin(admin.ModelAdmin):
    list_display = ["notebook", "campaign", "linked_by", "order"]
    list_filter = ["campaign"]
    search_fields = ["notebook__name", "campaign__name"]
    autocomplete_fields = ["notebook", "campaign", "linked_by"]
