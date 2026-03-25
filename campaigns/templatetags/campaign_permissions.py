from django import template

from campaigns.permissions import CampaignPermissions

register = template.Library()


@register.filter
def is_member(campaign, user):
    return CampaignPermissions.can_view(campaign, user)


@register.filter
def is_owner(campaign, user):
    return CampaignPermissions.is_owner(campaign, user)
