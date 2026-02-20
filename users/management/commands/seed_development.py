from django.core.management.base import BaseCommand

from notebooks.models import Notebook, NotebookPermission
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
        index_page = Page.objects.create(wiki=notebook)
        index_page.update(
            filename="index.md",
            mime_type="text/markdown",
            data=b"# Campaign Notes\n\nWelcome to our campaign wiki.",
            created_by=norm,
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

        NotebookPermission.objects.create(
            notebook=notebook,
            user=wendy,
            role=NotebookPermission.Role.EDITOR,
        )

        session_page = Page.objects.create(wiki=notebook)
        session_page.update(
            filename="sessions/session-01.md",
            mime_type="text/markdown",
            data=b"# Session 1\n\nThe party met in a tavern.",
            created_by=norm,
        )

        wendys_notebook = Notebook.objects.create(
            name="World Building",
            owner=wendy,
        )
        places_page = Page.objects.create(wiki=wendys_notebook)
        places_page.update(
            filename="places/index.md",
            mime_type="text/markdown",
            data=b"# Places\n\nLocations in the world.",
            created_by=wendy,
        )
        places_page.update(
            filename="places/index.md",
            mime_type="text/markdown",
            data=b"# Places\n\nLocations in the world.\n\n- The Capital\n- The Wilds",
            created_by=wendy,
        )
        capital_page = Page.objects.create(wiki=wendys_notebook)
        capital_page.update(
            filename="places/the-capital.md",
            mime_type="text/markdown",
            data=b"# The Capital\n\nA bustling city of commerce and intrigue.",
            created_by=wendy,
        )
