from django.urls import reverse

from wikis.models import Wiki


class HelpWiki(Wiki):
    class Meta:
        verbose_name = "help wiki"
        verbose_name_plural = "help wiki"

    @property
    def name(self):
        return "Help"

    def __str__(self):
        return "Help Wiki"

    def get_absolute_url(self):
        return reverse("help", kwargs={"path": ""})
