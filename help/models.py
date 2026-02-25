from wikis.models import Wiki


class HelpWiki(Wiki):
    class Meta:
        verbose_name = "help wiki"

    def __str__(self):
        return "Help Wiki"
