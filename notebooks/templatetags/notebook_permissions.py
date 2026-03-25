from django import template

from notebooks.permissions import NotebookPermissions

register = template.Library()


@register.filter
def can_edit(notebook, user):
    return NotebookPermissions.can_edit(notebook, user)


@register.filter
def can_manage(notebook, user):
    return user.is_authenticated and user == notebook.owner
