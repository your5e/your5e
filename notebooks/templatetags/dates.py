from django import template
from django.template.defaultfilters import pluralize
from django.utils import timezone

register = template.Library()


@register.filter
def smart_date(dt):
    now = timezone.now()
    delta = now - dt

    minutes = int(delta.total_seconds() // 60)
    hours = int(delta.total_seconds() // 3600)
    days = delta.days

    if minutes < 1:
        return "just now"
    if minutes < 60:
        return f"{minutes} minute{pluralize(minutes)} ago"
    if hours < 24:
        return f"{hours} hour{pluralize(hours)} ago"
    if days < 7:
        return f"{days} day{pluralize(days)} ago"
    if dt.year == now.year:
        return dt.strftime("%-d %b")
    return dt.strftime("%-d %b %Y")
