import pytest
from django.db import IntegrityError

from campaigns.models import Campaign
from notebooks.models import Notebook, NotebookPermission
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

    def test_is_campaign_wiki_false_for_regular_notebook(self):
        assert self.wendys_notebook.is_campaign_wiki is False

    def test_is_campaign_wiki_true_for_wiki_notebook(self):
        campaign = Campaign.objects.create(owner=self.wendy, name="Test Campaign")
        wiki_notebook = campaign.campaign_notebooks.get(is_wiki=True).notebook
        assert wiki_notebook.is_campaign_wiki is True

    def test_campaign_wiki_notebook_cannot_be_deleted(self):
        campaign = Campaign.objects.create(owner=self.wendy, name="Test Campaign")
        wiki_notebook = campaign.campaign_notebooks.get(is_wiki=True).notebook
        with pytest.raises(ValueError):
            wiki_notebook.delete()


@pytest.mark.django_db
class TestNotebookVisibleTo(NotebookMixin):
    def test_owner_sees_all_own_notebooks(self):
        notebooks = list(Notebook.visible_to(self.wendy, self.wendy))
        assert self.wendys_notebook in notebooks
        assert self.wendys_secret in notebooks

    def test_editor_sees_shared_notebook(self):
        notebooks = list(Notebook.visible_to(self.susan, self.wendy))
        assert self.wendys_notebook in notebooks
        assert self.wendys_secret not in notebooks

    def test_viewer_sees_shared_notebook(self):
        notebooks = list(Notebook.visible_to(self.mary, self.wendy))
        assert self.wendys_notebook in notebooks
        assert self.wendys_secret not in notebooks

    def test_user_sees_public_and_internal(self):
        notebooks = list(Notebook.visible_to(self.hugh, self.susan))
        assert self.susans_notebook in notebooks

    def test_user_does_not_see_private(self):
        notebooks = list(Notebook.visible_to(self.hugh, self.wendy))
        assert self.wendys_notebook not in notebooks
        assert self.wendys_secret not in notebooks


@pytest.mark.django_db
class TestNotebookPermission(NotebookMixin):
    def test_cannot_duplicate_collaborator(self):
        with pytest.raises(IntegrityError):
            NotebookPermission.objects.create(
                notebook=self.wendys_notebook,
                user=self.susan,
                role=NotebookPermission.Role.EDITOR,
            )

    def test_cannot_duplicate_collaborator_with_different_role(self):
        with pytest.raises(IntegrityError):
            NotebookPermission.objects.create(
                notebook=self.wendys_notebook,
                user=self.susan,
                role=NotebookPermission.Role.VIEWER,
            )
