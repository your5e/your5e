from http import HTTPStatus

import pytest

from notebooks.models import Notebook
from users.tests import UserMixin


class NotebookMixin(UserMixin):
    @pytest.fixture(autouse=True)
    def setup_notebooks(self, db, setup_users):
        self.wendys_notebook = Notebook.objects.create(
            name="Héros & Légendes",
            owner=self.wendy,
        )
        self.susans_notebook = Notebook.objects.create(
            name="Campaign Notes",
            owner=self.susan,
            visibility=Notebook.Visibility.PUBLIC,
        )


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


@pytest.mark.django_db
class TestProfileNotebooks(NotebookMixin):
    @UserMixin.as_wendy
    def test_own_profile_lists_notebooks(self, client):
        response = client.get("/profile/wendy/")
        content = response.content.decode()
        assert "Héros &amp; Légendes" in content

    @UserMixin.as_wendy
    def test_own_profile_shows_create_notebook_form(self, client):
        response = client.get("/profile/wendy/")
        content = response.content.decode()
        assert 'name="notebook_name"' in content

    @UserMixin.as_wendy
    def test_create_notebook(self, client):
        response = client.post(
            "/profile/wendy/notebooks",
            {"notebook_name": "New Notebook"},
        )
        assert response.status_code == HTTPStatus.FOUND
        notebook = Notebook.objects.get(name="New Notebook")
        assert notebook.owner == self.wendy
        assert notebook.slug == "new-notebook"

    @UserMixin.as_wendy
    def test_create_notebook_redirects_to_profile(self, client):
        response = client.post(
            "/profile/wendy/notebooks",
            {"notebook_name": "New Notebook"},
        )
        assert response.url == "/profile/wendy/"

    @UserMixin.as_wendy
    def test_other_profile_does_not_show_notebooks(self, client):
        response = client.get("/profile/susan/")
        content = response.content.decode()
        assert "Campaign Notes" not in content

    @UserMixin.as_wendy
    def test_cannot_create_notebook_on_other_profile(self, client):
        response = client.post(
            "/profile/susan/notebooks",
            {"notebook_name": "Hacked Notebook"},
        )
        assert response.status_code == HTTPStatus.FORBIDDEN
        assert not Notebook.objects.filter(name="Hacked Notebook").exists()

    def test_anonymous_cannot_create_notebook(self, client):
        response = client.post(
            "/profile/wendy/notebooks",
            {"notebook_name": "Hacked Notebook"},
        )
        assert response.status_code == HTTPStatus.UNAUTHORIZED
        assert not Notebook.objects.filter(name="Hacked Notebook").exists()
