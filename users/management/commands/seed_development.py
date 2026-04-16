from pathlib import Path
from textwrap import dedent

from django.conf import settings
from django.core.management import call_command
from django.core.management.base import BaseCommand

from campaigns.models import Campaign, CampaignNotebook
from notebooks.models import Notebook, NotebookPermission
from users.models import AuthToken, ProfileLink, User
from wikis.models import Page


class Command(BaseCommand):
    help = "Create default users for development"

    def handle(self, *args, **options):
        db_name = settings.DATABASES["default"]["NAME"]
        if db_name == "your5e_test":
            token_dir = Path("tests")
        else:
            token_dir = Path(".")
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
        _, token = AuthToken.objects.create(user=norm, name="Development")
        (token_dir / "norm.token").write_text(token)

        wendy = User.objects.create_user(
            username="wendy",
            email="wendy@localhost",
            password="wendy",
            name="Wendy Testaburger",
            short_name="Wendy",
        )
        _, wendy_token = AuthToken.objects.create(user=wendy, name="Development")
        (token_dir / "wendy.token").write_text(wendy_token)

        susan = User.objects.create_user(
            username="susan",
            email="susan@localhost",
            password="susan",
            name="Susan Test",
            short_name="Susan",
        )
        _, susan_token = AuthToken.objects.create(user=susan, name="Development")
        (token_dir / "susan.token").write_text(susan_token)

        hugh = User.objects.create_user(
            username="hugh",
            email="hugh@localhost",
            password="hugh",
            name="Hugh Test",
            short_name="Hugh",
        )
        _, hugh_token = AuthToken.objects.create(user=hugh, name="Development")
        (token_dir / "hugh.token").write_text(hugh_token)

        notebook = Notebook.objects.create(
            name="Campaign Notes",
            owner=norm,
            visibility=Notebook.Visibility.PUBLIC,
        )
        commands_dir = Path(__file__).resolve().parent
        map_data = (commands_dir / "random-hexmap-7.png").read_bytes()

        map_page = Page.objects.create(wiki=notebook)
        map_page.update(
            filename="random-hexmap-7.png",
            mime_type="image/png",
            data=map_data,
            created_by=norm,
        )

        index_page = Page.objects.create(wiki=notebook)
        index_page.update(
            filename="index.md",
            mime_type="text/markdown",
            data=dedent("""\
                ---
                notebook: A public notebook for sharing campaign information
                ---

                # Campaign Notes

                Welcome to our campaign wiki.

                ![Map](random-hexmap-7.png)
            """).encode(),
            created_by=norm,
        )
        page = Page.objects.create(wiki=notebook)
        page.update(
            filename="Welcome.md",
            mime_type="text/markdown",
            data=dedent("""\
                # Welcome

                This is a sample wiki page.
            """).encode(),
            created_by=norm,
        )
        page.update(
            filename="Home.md",
            mime_type="text/markdown",
            data=dedent("""\
                # Home

                This is the home page.

                Renamed and updated.
            """).encode(),
            created_by=wendy,
        )

        NotebookPermission.objects.create(
            notebook=notebook,
            user=wendy,
            role=NotebookPermission.Role.EDITOR,
        )
        NotebookPermission.objects.create(
            notebook=notebook,
            user=susan,
            role=NotebookPermission.Role.VIEWER,
        )

        session_page = Page.objects.create(wiki=notebook)
        session_page.update(
            filename="sessions/session-01.md",
            mime_type="text/markdown",
            data=dedent("""\
                # Session 1

                The party met in a tavern.
            """).encode(),
            created_by=norm,
        )

        bestiary_page = Page.objects.create(wiki=notebook)
        bestiary_page.update(
            filename="Bestiary.md",
            mime_type="text/markdown",
            data=dedent("""\
                # Bestiary

                Creatures encountered.
            """).encode(),
            created_by=norm,
        )
        bestiary_page.update(
            filename="Bestiary.md",
            mime_type="text/markdown",
            data=dedent("""\
                # Bestiary

                Creatures encountered.

                ## Goblin

                Small and cunning.
            """).encode(),
            created_by=norm,
        )

        npc_content = dedent("""\
            # NPCs

            Important characters.

            ## Bartender

            Knows everyone.
        """).encode()
        npcs_page = Page.objects.create(wiki=notebook)
        npcs_page.update(
            filename="NPCs.md",
            mime_type="text/markdown",
            data=npc_content,
            created_by=norm,
        )
        npcs_page.update(
            filename="characters/NPCs.md",
            mime_type="text/markdown",
            data=npc_content,
            created_by=norm,
        )

        cafe_page = Page.objects.create(wiki=notebook)
        cafe_page.update(
            filename="The Old Café.md",
            mime_type="text/markdown",
            data=dedent("""\
                # The Old Café

                A cosy establishment frequented by adventurers.
            """).encode(),
            created_by=norm,
        )

        region_page = Page.objects.create(wiki=notebook)
        region_page.update(
            filename="World Regions/Northern Kingdoms/Frosthold.md",
            mime_type="text/markdown",
            data=dedent("""\
                # Frosthold

                A fortress city in the frozen north.
            """).encode(),
            created_by=norm,
        )

        deleted_page = Page.objects.create(wiki=notebook)
        deleted_page.update(
            filename="Old Notes.md",
            mime_type="text/markdown",
            data=dedent("""\
                # Old Notes

                These notes are no longer needed.
            """).encode(),
            created_by=norm,
        )
        deleted_page.soft_delete()

        wendys_notebook = Notebook.objects.create(
            name="World Building",
            owner=wendy,
        )
        places_page = Page.objects.create(wiki=wendys_notebook)
        places_page.update(
            filename="places/index.md",
            mime_type="text/markdown",
            data=dedent("""\
                # Places

                Locations in the world.
            """).encode(),
            created_by=wendy,
        )
        places_page.update(
            filename="places/index.md",
            mime_type="text/markdown",
            data=dedent("""\
                # Places

                Locations in the world.

                - [[The Capital]]
                - [[The Wilds]]
            """).encode(),
            created_by=wendy,
        )
        capital_page = Page.objects.create(wiki=wendys_notebook)
        capital_page.update(
            filename="places/The Capital.md",
            mime_type="text/markdown",
            data=dedent("""\
                # The Capital

                A bustling city of commerce and intrigue.

                See also: [[The Wilds|the wilderness beyond]].
            """).encode(),
            created_by=wendy,
        )
        wilds_page = Page.objects.create(wiki=wendys_notebook)
        wilds_page.update(
            filename="places/The Wilds.md",
            mime_type="text/markdown",
            data=dedent("""\
                # The Wilds

                Untamed forests and ancient ruins.

                Return to [Places](./index).
            """).encode(),
            created_by=wendy,
        )
        NotebookPermission.objects.create(
            notebook=wendys_notebook,
            user=norm,
            role=NotebookPermission.Role.VIEWER,
        )

        norms_campaign = Campaign.objects.create(
            name="The Long Road",
            owner=norm,
            description=dedent("""\
                A journey across the realm.

                The party must travel from **Millbrook** to the distant city of
                *Thornhaven*, facing dangers along the way.
            """).strip(),
        )
        norms_campaign.players.add(wendy)

        norms_wiki = norms_campaign.campaign_notebooks.get(is_wiki=True).notebook
        wiki_index = Page.objects.create(wiki=norms_wiki)
        wiki_index.update(
            filename="index.md",
            mime_type="text/markdown",
            data=dedent("""\
                # The Long Road

                A campaign wiki for tracking our journey.

                ## Quick Links
                - [[Characters]]
                - [[Locations]]
                - [[Session Notes]]
            """).strip().encode(),
            created_by=norm,
        )
        wiki_chars = Page.objects.create(wiki=norms_wiki)
        wiki_chars.update(
            filename="characters.md",
            mime_type="text/markdown",
            data=dedent("""\
                # Characters

                ## Party Members
                - **Thorn** - Human fighter
                - **Elara** - Elf wizard
                - **Bramble** - Halfling rogue
            """).strip().encode(),
            created_by=norm,
        )

        wendys_campaign = Campaign.objects.create(
            name="Secrets of the Tower",
            owner=wendy,
            description=dedent("""\
                Mysteries await in the ancient tower.

                - Explore the ruins
                - Uncover the secrets
                - Survive the guardians
            """).strip(),
        )
        wendys_campaign.players.add(norm)
        wendys_campaign.players.add(susan)

        CampaignNotebook.objects.create(
            campaign=norms_campaign,
            notebook=notebook,
            linked_by=norm,
        )
        CampaignNotebook.objects.create(
            campaign=wendys_campaign,
            notebook=wendys_notebook,
            linked_by=wendy,
        )
        CampaignNotebook.objects.create(
            campaign=wendys_campaign,
            notebook=notebook,
            linked_by=norm,
        )

        # Long names for wrapping tests
        long_campaign = Campaign.objects.create(
            name=(
                "Whispers from the Forgotten Crypts Beneath the Mountains "
                "of Eternal Sorrow"
            ),
            owner=norm,
            description="A campaign with a deliberately long name for testing.",
        )
        long_campaign.players.add(wendy)

        long_notebook = Notebook.objects.create(
            name=(
                "Comprehensive Bestiary and Geographical Survey of the "
                "Blighted Territories Including Appendices on Local Customs"
            ),
            owner=norm,
            visibility=Notebook.Visibility.INTERNAL,
        )
        long_index = Page.objects.create(wiki=long_notebook)
        long_index.update(
            filename="index.md",
            mime_type="text/markdown",
            data=dedent("""\
                # Campaign Notes

                Welcome to our campaign wiki.

                ![Map](random-hexmap-7.png)
            """).encode(),
            created_by=norm,
        )
        long_map = Page.objects.create(wiki=long_notebook)
        long_map.update(
            filename="random-hexmap-7.png",
            mime_type="image/png",
            data=map_data,
            created_by=norm,
        )
        long_folder_one = Page.objects.create(wiki=long_notebook)
        long_folder_one.update(
            filename="Legends and Oral Histories of the Northern Clans/index.md",
            mime_type="text/markdown",
            data=b"# Legends and Oral Histories of the Northern Clans\n",
            created_by=norm,
        )
        long_folder_two = Page.objects.create(wiki=long_notebook)
        long_folder_two.update(
            filename="Alchemical Reagents and Their Mundane Substitutes/index.md",
            mime_type="text/markdown",
            data=b"# Alchemical Reagents and Their Mundane Substitutes\n",
            created_by=norm,
        )
        CampaignNotebook.objects.create(
            campaign=long_campaign,
            notebook=long_notebook,
            linked_by=norm,
        )

        Notebook.objects.create(
            name="Empty Notebook",
            owner=norm,
            visibility=Notebook.Visibility.PUBLIC,
        )

        call_command("sync_docs")
