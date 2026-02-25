from http import HTTPStatus
from unittest.mock import patch

import pytest
from django.core.management import call_command

from help.models import HelpWiki
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
            call_command("sync_api_docs")

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
    @pytest.fixture
    def help_index(self):
        wiki = HelpWiki.objects.get()
        user = User.objects.get(username="help")
        page = Page.objects.create(wiki=wiki)
        page.update(
            filename="Index.md",
            mime_type="text/markdown",
            data=b"# Help\n\nWelcome to the help section.",
            created_by=user,
        )
        return page

    @pytest.fixture
    def help_page(self):
        wiki = HelpWiki.objects.get()
        user = User.objects.get(username="help")
        page = Page.objects.create(wiki=wiki)
        page.update(
            filename="api/Overview.md",
            mime_type="text/markdown",
            data=b"# API Overview\n\nWelcome to the API.",
            created_by=user,
        )
        return page

    @pytest.fixture
    def api_index(self):
        wiki = HelpWiki.objects.get()
        user = User.objects.get(username="help")
        page = Page.objects.create(wiki=wiki)
        page.update(
            filename="api/Index.md",
            mime_type="text/markdown",
            data=b"# API\n\nAPI documentation.",
            created_by=user,
        )
        return page

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
