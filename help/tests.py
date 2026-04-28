from http import HTTPStatus
from textwrap import dedent
from unittest.mock import patch

import pytest
from django.core.management import call_command
from whatnext.models import State

from help.models import HelpWiki
from help.roadmap import (
    RoadmapEntry,
    RoadmapTask,
    calculate_task_progress,
    generate_roadmap_markdown,
    parse_roadmap_file,
)
from users.models import User
from wikis.models import Page


@pytest.mark.django_db
class TestSyncApiDocs:
    @pytest.fixture
    def project_dir(self, tmp_path):
        api_docs = tmp_path / "api" / "docs"
        api_docs.mkdir(parents=True)
        help_docs = tmp_path / "help" / "docs"
        help_docs.mkdir(parents=True)
        return tmp_path

    def run_sync(self, project_dir):
        with patch("django.conf.settings.BASE_DIR", project_dir):
            call_command("sync_docs")

    def test_syncs_api_docs_to_wiki(self, project_dir):
        api_docs = project_dir / "api" / "docs"
        (api_docs / "overview.md").write_text("# API Overview\n\nWelcome.")
        (api_docs / "authentication.md").write_text("# Authentication\n\nUse tokens.")

        self.run_sync(project_dir)

        wiki = HelpWiki.objects.get()
        overview = wiki.get_page(path="api/overview")
        auth = wiki.get_page(path="api/authentication")
        assert b"API Overview" in overview.latest_version.content.data
        assert b"Authentication" in auth.latest_version.content.data

    def test_syncs_help_index_to_wiki(self, project_dir):
        help_docs = project_dir / "help" / "docs"
        (help_docs / "index.md").write_text("# Help\n\nWelcome to help.")

        self.run_sync(project_dir)

        wiki = HelpWiki.objects.get()
        index = wiki.get_page(path="index")
        assert b"Welcome to help" in index.latest_version.content.data

    def test_updates_existing_pages(self, project_dir):
        api_docs = project_dir / "api" / "docs"
        (api_docs / "overview.md").write_text("# Version 1")

        self.run_sync(project_dir)

        (api_docs / "overview.md").write_text("# Version 2")

        self.run_sync(project_dir)

        wiki = HelpWiki.objects.get()
        page = wiki.get_page(path="api/overview")
        assert page.latest_version.number == 2
        assert b"Version 2" in page.latest_version.content.data

    def test_unchanged_files_do_not_create_new_versions(self, project_dir):
        api_docs = project_dir / "api" / "docs"
        (api_docs / "overview.md").write_text("# Same Content")

        self.run_sync(project_dir)
        self.run_sync(project_dir)

        wiki = HelpWiki.objects.get()
        page = wiki.get_page(path="api/overview")
        assert page.latest_version.number == 1

    def test_discovers_docs_in_any_app(self, project_dir):
        campaigns_docs = project_dir / "campaigns" / "docs"
        campaigns_docs.mkdir(parents=True)
        (campaigns_docs / "guide.md").write_text("# Campaign Guide")

        self.run_sync(project_dir)

        wiki = HelpWiki.objects.get()
        guide = wiki.get_page(path="campaigns/guide")
        assert b"Campaign Guide" in guide.latest_version.content.data


@pytest.mark.django_db
class TestHelpPageView:
    def create_help_page(self, filename, data):
        wiki = HelpWiki.objects.get()
        user = User.objects.get(username="help")
        page = Page.objects.create(wiki=wiki)
        page.update(
            filename=filename,
            mime_type="text/markdown",
            data=data,
            created_by=user,
        )
        return page

    @pytest.fixture
    def help_index(self):
        return self.create_help_page(
            "Index.md",
            b"# Help\n\nWelcome to the help section.",
        )

    @pytest.fixture
    def help_page(self):
        return self.create_help_page(
            "api/Overview.md",
            b"# API Overview\n\nWelcome to the API.",
        )

    @pytest.fixture
    def api_index(self):
        return self.create_help_page(
            "api/Index.md",
            b"# API\n\nAPI documentation.",
        )

    @pytest.fixture
    def obsidian_plugin_page(self):
        return self.create_help_page(
            "obsidian-plugin.md",
            b"# Obsidian Plugin\n\n"
            b"Sync your notebooks.\n\n"
            b"Create an API token from [your profile](/profile/).",
        )

    def test_index_serves_root_page(self, client, help_index):
        response = client.get("/help/")
        assert response.status_code == HTTPStatus.OK
        assert b"Welcome to the help section" in response.content

    def test_directory_serves_index_page(self, client, api_index):
        response = client.get("/help/api/")
        assert response.status_code == HTTPStatus.OK
        assert b"API documentation" in response.content

    def test_index_path_redirects_to_directory(self, client, api_index):
        response = client.get("/help/api/index")
        assert response.status_code == HTTPStatus.FOUND
        assert response.url == "/help/api/"

    def test_root_index_path_redirects_to_help(self, client, help_index):
        response = client.get("/help/index")
        assert response.status_code == HTTPStatus.FOUND
        assert response.url == "/help/"

    def test_serves_existing_page(self, client, help_page):
        response = client.get("/help/api/overview")
        assert response.status_code == HTTPStatus.OK
        assert b"API Overview" in response.content

    def test_renders_markdown_as_html(self, client, help_page):
        response = client.get("/help/api/overview")
        assert b"<h1>" in response.content

    def test_returns_404_for_nonexistent_page(self, client):
        response = client.get("/help/api/nonexistent")
        assert response.status_code == HTTPStatus.NOT_FOUND

    def test_obsidian_plugin_page_links_to_token_management(
        self, client, obsidian_plugin_page
    ):
        response = client.get("/help/obsidian-plugin")
        assert response.status_code == HTTPStatus.OK
        content = response.content.decode()
        assert "Obsidian Plugin" in content
        assert "/profile/" in content
        assert "token" in content.lower()

    def test_cssclass_frontmatter_adds_class_to_article(self, client):
        self.create_help_page(
            "styled.md",
            dedent("""\
                ---
                cssclass: roadmap
                ---
                # Styled Page

                Content.
            """).encode(),
        )
        response = client.get("/help/styled")
        assert response.status_code == HTTPStatus.OK
        assert b'class="site-content roadmap"' in response.content


class RoadmapTasksMixin:
    @pytest.fixture
    def tasks_dir(self, tmp_path):
        tasks = tmp_path / "tasks"
        tasks.mkdir()
        work = tasks / "work"
        work.mkdir()
        roadmap = tasks / "roadmap"
        roadmap.mkdir()

        (work / "complete.md").write_text(dedent("""\
            - [X] done
            - [X] also done
        """))
        (work / "partial.md").write_text(dedent("""\
            - [X] done
            - [ ] not done
        """))
        (work / "empty.md").write_text(dedent("""\
            - [ ] not done
            - [ ] also not done
        """))

        # Roadmap entries in different states
        (roadmap / "notebook_sync.md").write_text(dedent("""\
            # Notebook Sync

            Sync your notebooks with Obsidian.

            - [X] Released @after ../work/complete.md
        """))
        (roadmap / "dark_mode.md").write_text(dedent("""\
            # Dark Mode

            A dark theme for the site.

            - [ ] Release @after ../work/partial.md
        """))
        (roadmap / "session_scheduler.md").write_text(dedent("""\
            # Session Scheduler

            Schedule and manage game sessions.

            - [ ] Release @after ../work/empty.md
        """))
        (roadmap / "api_tokens.md").write_text(dedent("""\
            # API Tokens

            Manage access tokens for integrations.

            - [ ] Release @after ../work/empty.md
        """))
        (roadmap / "character_sheets.md").write_text(dedent("""\
            # Character Sheets

            Create and manage character sheets.

            - [ ] Equipment tracking @after ../work/empty.md
            - [X] Ability scores @after ../work/complete.md
            - [ ] Basic info @after ../work/partial.md
        """))
        (roadmap / "prematurely_marked.md").write_text(dedent("""\
            # Prematurely Marked

            This feature was marked complete before the work was done.

            - [X] Release @after ../work/partial.md
        """))
        return tasks


class TestRoadmap(RoadmapTasksMixin):
    def test_parse_roadmap_entry(self, tasks_dir):
        assert parse_roadmap_file(
            tasks_dir / "roadmap" / "notebook_sync.md"
        ) == (
            RoadmapEntry(
                title="Notebook Sync",
                description="Sync your notebooks with Obsidian.",
                tasks=[
                    RoadmapTask(
                        text="Released",
                        state=State.COMPLETE,
                        dependencies=[
                            str((tasks_dir / "work" / "complete.md").resolve())
                        ],
                    ),
                ],
            )
        )

    def test_calculates_task_progress(self, tasks_dir):
        roadmap = tasks_dir / "roadmap"

        notebook_sync = parse_roadmap_file(roadmap / "notebook_sync.md")
        assert calculate_task_progress(notebook_sync.tasks[0]) == (3, 3)

        dark_mode = parse_roadmap_file(roadmap / "dark_mode.md")
        assert calculate_task_progress(dark_mode.tasks[0]) == (1, 3)

        session_scheduler = parse_roadmap_file(roadmap / "session_scheduler.md")
        assert calculate_task_progress(session_scheduler.tasks[0]) == (0, 3)

    def test_marked_complete_with_incomplete_dependencies_is_not_available(
        self, tasks_dir
    ):
        roadmap = tasks_dir / "roadmap"
        prematurely_marked = parse_roadmap_file(roadmap / "prematurely_marked.md")
        completed, total = calculate_task_progress(prematurely_marked.tasks[0])
        assert (completed, total) == (1, 3)

    def test_sorts_entries_by_activity(self, tasks_dir):
        markdown = generate_roadmap_markdown(tasks_dir / "roadmap")

        notebook_sync_pos = markdown.index("Notebook Sync")
        dark_mode_pos = markdown.index("Dark Mode")
        assert notebook_sync_pos < dark_mode_pos

        api_tokens_pos = markdown.index("API Tokens")
        assert dark_mode_pos < api_tokens_pos

        session_scheduler_pos = markdown.index("Session Scheduler")
        assert api_tokens_pos < session_scheduler_pos

        assert "Sync your notebooks with Obsidian." in markdown
        assert "A dark theme for the site." in markdown

    def test_does_not_sort_inside_entries(self, tasks_dir):
        markdown = generate_roadmap_markdown(tasks_dir / "roadmap")

        equipment_pos = markdown.index("| Equipment tracking | Planned |")
        ability_pos = markdown.index("| Ability scores | **Available** |")
        basic_pos = markdown.index("| Basic info | _In Progress_ |")
        assert equipment_pos < ability_pos < basic_pos

    def test_calculates_progress_per_task(self, tasks_dir):
        markdown = generate_roadmap_markdown(tasks_dir / "roadmap")

        assert "| Released | **Available** | 3 of 3 tasks |" in markdown
        assert "| Release | _In Progress_ | 1 of 3 tasks |" in markdown
        assert "| Release | Planned | 0 of 3 tasks |" in markdown


@pytest.mark.django_db
class TestSyncDocsRoadmap:
    @pytest.fixture
    def project_dir(self, tmp_path):
        help_docs = tmp_path / "help" / "docs"
        help_docs.mkdir(parents=True)
        tasks = tmp_path / "tasks"
        tasks.mkdir()
        work = tasks / "work"
        work.mkdir()
        roadmap = tasks / "roadmap"
        roadmap.mkdir()
        return tmp_path

    def run_sync(self, project_dir):
        with patch("django.conf.settings.BASE_DIR", project_dir):
            call_command("sync_docs")

    def test_generates_roadmap_page(self, project_dir):
        work = project_dir / "tasks" / "work"
        (work / "dice_roller.md").write_text("- [ ] task\n")

        roadmap = project_dir / "tasks" / "roadmap"
        (roadmap / "dice_roller.md").write_text(dedent("""\
            # Dice Roller

            Roll dice with standard notation.

            - [ ] Release @after ../work/dice_roller.md
        """))

        self.run_sync(project_dir)

        wiki = HelpWiki.objects.get()
        page = wiki.get_page(path="roadmap")
        assert b"Dice Roller" in page.latest_version.content.data
