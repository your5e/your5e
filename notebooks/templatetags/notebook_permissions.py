from django import template

from notebooks.permissions import NotebookPermissions

register = template.Library()


@register.filter
def can_edit(notebook, user):
    return NotebookPermissions.can_edit(notebook, user)


@register.filter
def can_manage(notebook, user):
    return user.is_authenticated and user == notebook.owner


@register.filter
def is_wiki_and_player_in_that_campaign(notebook, user):
    wiki_link = notebook.campaign_notebooks.filter(is_wiki=True).first()
    if not wiki_link:
        return False
    return wiki_link.campaign.players.filter(pk=user.pk).exists()
