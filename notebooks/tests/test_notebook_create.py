from http import HTTPStatus

import pytest

from notebooks.models import Notebook, NotebookPermission
from users.tests import UserMixin

from . import NotebookMixin


@pytest.mark.django_db
class TestNotebookCreateView(NotebookMixin):
    @UserMixin.as_user("wendy")
    def test_get_shows_create_form(self, client):
        response = client.get("/notebooks/create")
        assert response.status_code == HTTPStatus.OK
        content = response.content.decode()
        assert 'name="name"' in content
        assert 'name="visibility"' in content

    def test_anonymous_cannot_access_create_form(self, client):
        response = client.get("/notebooks/create")
        assert response.status_code == HTTPStatus.UNAUTHORIZED

    @UserMixin.as_user("wendy")
    def test_add_collaborator_shows_in_pending_list(self, client):
        response = client.post("/notebooks/create", {
            "add_collaborator": "true",
            "collaborator_username": "susan",
            "collaborator_role": "editor",
        })
        assert response.status_code == HTTPStatus.OK
        content = response.content.decode()
        assert "susan" in content
        assert "editor" in content

    @UserMixin.as_user("wendy")
    def test_add_invalid_collaborator_shows_error(self, client):
        response = client.post("/notebooks/create", {
            "add_collaborator": "true",
            "collaborator_username": "nonexistent",
            "collaborator_role": "editor",
        })
        assert response.status_code == HTTPStatus.OK
        content = response.content.decode()
        assert "error" in content.lower() or "not found" in content.lower()

    @UserMixin.as_user("wendy")
    def test_remove_pending_collaborator(self, client):
        response = client.post("/notebooks/create", {
            "remove_collaborator": str(self.susan.pk),
            "pending_pk": [str(self.susan.pk)],
            "pending_role": ["editor"],
        })
        assert response.status_code == HTTPStatus.OK
        assert "susan" not in response.content.decode()

    @UserMixin.as_user("wendy")
    def test_create_notebook(self, client):
        response = client.post("/notebooks/create", {
            "name": "Adventure Log",
            "visibility": "public",
            "pending_pk": [str(self.susan.pk), str(self.mary.pk)],
            "pending_role": ["editor", "viewer"],
            "create": "true",
        })
        assert response.status_code == HTTPStatus.FOUND
        notebook = Notebook.objects.get(name="Adventure Log")
        assert notebook.owner == self.wendy
        assert notebook.visibility == Notebook.Visibility.PUBLIC
        assert response.url == notebook.get_absolute_url()

        susan_perm = NotebookPermission.objects.get(notebook=notebook, user=self.susan)
        assert susan_perm.role == NotebookPermission.Role.EDITOR

        mary_perm = NotebookPermission.objects.get(notebook=notebook, user=self.mary)
        assert mary_perm.role == NotebookPermission.Role.VIEWER

    @UserMixin.as_user("wendy")
    def test_create_requires_name(self, client):
        response = client.post("/notebooks/create", {
            "name": "",
            "visibility": "private",
            "create": "true",
        })
        assert response.status_code == HTTPStatus.OK
        content = response.content.decode()
        assert "error" in content.lower() or "required" in content.lower()
        assert not Notebook.objects.filter(name="").exists()

    @UserMixin.as_user("wendy")
    def test_prepopulated_collaborators_from_post(self, client):
        response = client.post("/notebooks/create", {
            "prepopulate_collaborator": [str(self.susan.pk), str(self.mary.pk)],
        })
        assert response.status_code == HTTPStatus.OK
        content = response.content.decode()
        assert "susan" in content
        assert "mary" in content

    def test_anonymous_cannot_create_notebook(self, client):
        response = client.post("/notebooks/create", {
            "name": "Hacked Notebook",
            "visibility": "private",
            "create": "true",
        })
        assert response.status_code == HTTPStatus.UNAUTHORIZED
        assert not Notebook.objects.filter(name="Hacked Notebook").exists()

    @UserMixin.as_user("wendy")
    def test_create_form_has_description_field(self, client):
        response = client.get("/notebooks/create")
        assert response.status_code == HTTPStatus.OK
        content = response.content.decode()
        assert 'name="description"' in content
        assert "<textarea" in content

    @UserMixin.as_user("wendy")
    def test_create_creates_index_with_description(self, client):
        response = client.post("/notebooks/create", {
            "name": "Adventure Log",
            "visibility": "public",
            "description": "Welcome to the adventure.",
            "create": "true",
        })
        assert response.status_code == HTTPStatus.FOUND
        notebook = Notebook.objects.get(name="Adventure Log")
        index_page = notebook.get_page(path="index")
        assert index_page.latest_version.content.data == b"Welcome to the adventure.\n"

    @UserMixin.as_user("wendy")
    def test_create_creates_empty_index_when_no_description(self, client):
        response = client.post("/notebooks/create", {
            "name": "Empty Notebook",
            "visibility": "private",
            "description": "",
            "create": "true",
        })
        assert response.status_code == HTTPStatus.FOUND
        notebook = Notebook.objects.get(name="Empty Notebook")
        index_page = notebook.get_page(path="index")
        assert index_page.latest_version.content.data == b"\n"
