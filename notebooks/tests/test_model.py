import pytest

from notebooks.models import Notebook
from wikis.models import Page

from . import NotebookMixin


@pytest.mark.django_db
class TestNotebook(NotebookMixin):
    def test_slug_generated_from_name(self):
        assert self.wendys_notebook.slug == "heros-legendes"

    def test_slug_unique_to_user(self):
        notebook = Notebook.objects.create(
            name="Campaign Notes",
            owner=self.wendy,
        )
        assert notebook.slug == "campaign-notes"
        assert self.susans_notebook.slug == "campaign-notes"

    def test_duplicate_slug_numbered(self):
        notebook = Notebook.objects.create(
            name="Campaign Notes",
            owner=self.susan,
        )
        assert self.susans_notebook.slug == "campaign-notes"
        assert notebook.slug == "campaign-notes-2"

    def test_rename_updates_name_and_slug(self):
        Notebook.objects.create(name="Session Log", owner=self.wendy)
        self.wendys_notebook.rename("Session Log")
        assert self.wendys_notebook.name == "Session Log"
        assert self.wendys_notebook.slug == "session-log-2"

    def test_get_folder_url_for_nested_path(self):
        url = self.wendys_notebook.get_folder_url("heroes/theron")
        assert url == "/notebooks/wendy/heros-legendes/heroes/"

    def test_get_folder_url_for_root_path(self):
        url = self.wendys_notebook.get_folder_url("notes")
        assert url == "/notebooks/wendy/heros-legendes/"

    def test_has_content_with_pages(self):
        assert self.wendys_notebook.has_content() is True

    def test_has_content_when_empty(self):
        empty_notebook = Notebook.objects.create(
            name="Empty Notebook",
            owner=self.wendy,
        )
        assert empty_notebook.has_content() is False

    def test_has_content_with_only_deleted_pages(self):
        notebook = Notebook.objects.create(
            name="Deleted Only",
            owner=self.wendy,
        )
        page = Page.objects.create(wiki=notebook)
        page.update(
            filename="draft.md",
            mime_type="text/markdown",
            data=b"# Draft",
            created_by=self.wendy,
        )
        page.soft_delete()
        assert notebook.has_content() is False

    def test_breadcrumbs_for(self):
        page = self.wendys_notebook.get_page(path="heroes/theron")
        crumbs = self.wendys_notebook.breadcrumbs_for(page.latest_version)
        assert crumbs == [
            {"name": "Héros & Légendes", "url": "/notebooks/wendy/heros-legendes/"},
            {"name": "heroes", "url": "/notebooks/wendy/heros-legendes/heroes/"},
            {"name": "theron", "url": "/notebooks/wendy/heros-legendes/heroes/theron"},
        ]
