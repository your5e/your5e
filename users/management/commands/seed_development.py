from django.core.management.base import BaseCommand

from notebooks.models import Notebook
from users.models import ProfileLink, User
from wikis.models import Page


class Command(BaseCommand):
    help = "Create default users for development"

    def handle(self, *args, **options):
        User.objects.create_user(
            username="admin",
            email="admin@localhost",
            password="admin",
            is_staff=True,
            is_superuser=True,
        )
        norm = User.objects.create_user(
            username="norm",
            email="norm@localhost",
            password="norm",
            name="Mark Norman Francis",
            short_name="Norm",
            description="Developer and tabletop enthusiast.",
            is_public=True,
        )
        ProfileLink.objects.create(
            user=norm,
            url="https://marknormanfrancis.com",
            label="Website",
        )
        wendy = User.objects.create_user(
            username="wendy",
            email="wendy@localhost",
            password="wendy",
            name="Wendy Testaburger",
            short_name="Wendy",
        )

        notebook = Notebook.objects.create(
            name="Campaign Notes",
            owner=norm,
            visibility=Notebook.Visibility.PUBLIC,
        )
        page = Page.objects.create(wiki=notebook)
        page.update(
            filename="Welcome.md",
            mime_type="text/markdown",
            data=b"# Welcome\n\nThis is a sample wiki page.",
            created_by=norm,
        )
        page.update(
            filename="Home.md",
            mime_type="text/markdown",
            data=b"# Home\n\nThis is the home page.\n\nRenamed and updated.",
            created_by=wendy,
        )

        Notebook.objects.create(
            name="World Building",
            owner=wendy,
        )
