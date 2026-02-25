from django.conf import settings
from django.core.management.base import BaseCommand

from help.models import HelpWiki
from users.models import User
from wikis.models import Page


class Command(BaseCommand):
    help = "Sync help documentation from source files to help wiki"

    def handle(self, *args, **options):
        wiki = HelpWiki.objects.get()
        user = User.objects.get(username="help")

        for docs_dir in settings.BASE_DIR.glob("*/docs"):
            if not docs_dir.is_dir():
                continue

            app_name = docs_dir.parent.name
            if app_name == "help":
                prefix = None
            else:
                prefix = app_name

            self.sync_directory(wiki, user, docs_dir, prefix)

    def sync_directory(self, wiki, user, docs_dir, prefix):
        for md_file in docs_dir.glob("*.md"):
            if prefix:
                filename = f"{prefix}/{md_file.stem.replace('_', ' ').title()}.md"
                path = f"{prefix}/{md_file.stem}"
            else:
                filename = f"{md_file.stem.replace('_', ' ').title()}.md"
                path = md_file.stem

            data = md_file.read_bytes()

            try:
                page = wiki.get_page(path=path)
            except Page.DoesNotExist:
                page = Page.objects.create(wiki=wiki)

            page.update(
                filename=filename,
                mime_type="text/markdown",
                data=data,
                created_by=user,
            )
