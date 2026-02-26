from wikis.models import Wiki


class HelpWiki(Wiki):
    class Meta:
        verbose_name = "help wiki"
        verbose_name_plural = "help wiki"

    def __str__(self):
        return "Help Wiki"
