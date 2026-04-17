{% autoescape off %}---
cssclass: roadmap
---
# Your5e Roadmap

New features and capabilities for this site being planned for the short to medium term.

_Usual caveats:_ Nothing here is a promise to complete and deliver anything,
and nothing has a specific deadline. Things get done when they get done.


{% for entry in entries %}
## {{ entry.title }}

{{ entry.description }}

| New Feature | Status | Progress |
|------|--------|----------|
{% for task in entry.tasks %}| {{ task.text }} | {{ task.status }} | {% if task.url %}[{{ task.completed }} of {{ task.total }} tasks]({{ task.url }}){% else %}{{ task.completed }} of {{ task.total }} tasks{% endif %} |
{% endfor %}
{% endfor %}{% endautoescape %}
