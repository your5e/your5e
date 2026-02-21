from http import HTTPStatus

import pytest

from notebooks.models import Notebook, NotebookPermission
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
        self.susans_permission = NotebookPermission.objects.create(
            notebook=self.wendys_notebook,
            user=self.susan,
            role=NotebookPermission.Role.EDITOR,
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


@pytest.mark.django_db
class TestNotebookView(NotebookMixin):
    @UserMixin.as_wendy
    def test_owner_can_view_notebook(self, client):
        response = client.get("/notebooks/wendy/heros-legendes/")
        assert response.status_code == HTTPStatus.OK
        content = response.content.decode()
        assert "Héros &amp; Légendes" in content

    @UserMixin.as_wendy
    def test_owner_sees_rename_form(self, client):
        response = client.get("/notebooks/wendy/heros-legendes/")
        content = response.content.decode()
        assert 'name="name"' in content

    @UserMixin.as_wendy
    def test_owner_sees_visibility_controls(self, client):
        response = client.get("/notebooks/wendy/heros-legendes/")
        content = response.content.decode()
        assert "visibility" in content.lower()

    @UserMixin.as_wendy
    def test_owner_sees_collaborator_section(self, client):
        response = client.get("/notebooks/wendy/heros-legendes/")
        content = response.content.decode()
        assert "collaborator" in content.lower()

    @UserMixin.as_wendy
    def test_non_owner_does_not_see_rename_form(self, client):
        self.susans_notebook.visibility = Notebook.Visibility.SITE
        self.susans_notebook.save()
        response = client.get("/notebooks/susan/campaign-notes/")
        content = response.content.decode()
        assert 'name="name"' not in content

    @UserMixin.as_wendy
    def test_non_owner_does_not_see_collaborator_section(self, client):
        self.susans_notebook.visibility = Notebook.Visibility.SITE
        self.susans_notebook.save()
        response = client.get("/notebooks/susan/campaign-notes/")
        content = response.content.decode()
        assert "collaborator" not in content.lower()


@pytest.mark.django_db
class TestNotebookRenameView(NotebookMixin):
    @UserMixin.as_wendy
    def test_owner_can_rename_notebook(self, client):
        response = client.post(
            "/notebooks/rename",
            {"notebook": self.wendys_notebook.pk, "name": "Session Notes"},
        )
        assert response.status_code == HTTPStatus.FOUND
        self.wendys_notebook.refresh_from_db()
        assert self.wendys_notebook.name == "Session Notes"
        assert self.wendys_notebook.slug == "session-notes"

    @UserMixin.as_wendy
    def test_rename_redirects_to_new_slug(self, client):
        response = client.post(
            "/notebooks/rename",
            {"notebook": self.wendys_notebook.pk, "name": "Session Notes"},
        )
        assert response.url == "/notebooks/wendy/session-notes/"

    @UserMixin.as_wendy
    def test_non_owner_cannot_rename_notebook(self, client):
        response = client.post(
            "/notebooks/rename",
            {"notebook": self.susans_notebook.pk, "name": "Hacked"},
        )
        assert response.status_code == HTTPStatus.FORBIDDEN
        self.susans_notebook.refresh_from_db()
        assert self.susans_notebook.name == "Campaign Notes"

    def test_anonymous_cannot_rename_notebook(self, client):
        response = client.post(
            "/notebooks/rename",
            {"notebook": self.wendys_notebook.pk, "name": "Hacked"},
        )
        assert response.status_code == HTTPStatus.UNAUTHORIZED
        self.wendys_notebook.refresh_from_db()
        assert self.wendys_notebook.name == "Héros & Légendes"


@pytest.mark.django_db
class TestNotebookVisibilityView(NotebookMixin):
    @UserMixin.as_wendy
    def test_visibility_change_shows_confirmation(self, client):
        response = client.post(
            "/notebooks/visibility",
            {"notebook": self.wendys_notebook.pk, "visibility": "public"},
        )
        assert response.status_code == HTTPStatus.OK
        content = response.content.decode()
        assert "confirm" in content.lower()

    @UserMixin.as_wendy
    def test_visibility_change_confirmed(self, client):
        response = client.post("/notebooks/visibility", {
            "notebook": self.wendys_notebook.pk,
            "visibility": "public",
            "confirmed": "true",
        })
        assert response.status_code == HTTPStatus.FOUND
        self.wendys_notebook.refresh_from_db()
        assert self.wendys_notebook.visibility == Notebook.Visibility.PUBLIC

    @UserMixin.as_wendy
    def test_visibility_change_redirects_to_notebook(self, client):
        response = client.post("/notebooks/visibility", {
            "notebook": self.wendys_notebook.pk,
            "visibility": "public",
            "confirmed": "true",
        })
        assert response.url == "/notebooks/wendy/heros-legendes/"

    @UserMixin.as_wendy
    def test_non_owner_cannot_change_visibility(self, client):
        response = client.post("/notebooks/visibility", {
            "notebook": self.susans_notebook.pk,
            "visibility": "private",
            "confirmed": "true",
        })
        assert response.status_code == HTTPStatus.FORBIDDEN
        self.susans_notebook.refresh_from_db()
        assert self.susans_notebook.visibility == Notebook.Visibility.PUBLIC

    def test_anonymous_cannot_change_visibility(self, client):
        response = client.post("/notebooks/visibility", {
            "notebook": self.wendys_notebook.pk,
            "visibility": "public",
            "confirmed": "true",
        })
        assert response.status_code == HTTPStatus.UNAUTHORIZED
        self.wendys_notebook.refresh_from_db()
        assert self.wendys_notebook.visibility == Notebook.Visibility.PRIVATE


@pytest.mark.django_db
class TestNotebookCollaboratorsView(NotebookMixin):
    @UserMixin.as_wendy
    def test_add_collaborator_shows_confirmation(self, client):
        response = client.post("/notebooks/collaborators", {
            "notebook": self.wendys_notebook.pk,
            "username": "mary",
            "role": "viewer",
        })
        assert response.status_code == HTTPStatus.OK
        content = response.content.decode()
        assert "confirm" in content.lower()
        assert "mary" in content.lower()

    @UserMixin.as_wendy
    def test_add_collaborator_confirmed(self, client):
        response = client.post("/notebooks/collaborators", {
            "notebook": self.wendys_notebook.pk,
            "username": "mary",
            "role": "viewer",
            "confirmed": "true",
        })
        assert response.status_code == HTTPStatus.FOUND
        permission = NotebookPermission.objects.get(
            notebook=self.wendys_notebook,
            user=self.mary,
        )
        assert permission.role == NotebookPermission.Role.VIEWER

    @UserMixin.as_wendy
    def test_remove_collaborator_shows_confirmation(self, client):
        response = client.post("/notebooks/collaborators", {
            "notebook": self.wendys_notebook.pk,
            "remove": str(self.susan.pk),
        })
        assert response.status_code == HTTPStatus.OK
        content = response.content.decode()
        assert "confirm" in content.lower()

    @UserMixin.as_wendy
    def test_remove_collaborator_confirmed(self, client):
        response = client.post("/notebooks/collaborators", {
            "notebook": self.wendys_notebook.pk,
            "remove": str(self.susan.pk),
            "confirmed": "true",
        })
        assert response.status_code == HTTPStatus.FOUND
        assert not NotebookPermission.objects.filter(
            notebook=self.wendys_notebook,
            user=self.susan,
        ).exists()

    @UserMixin.as_wendy
    def test_change_collaborator_role_shows_confirmation(self, client):
        response = client.post("/notebooks/collaborators", {
            "notebook": self.wendys_notebook.pk,
            "change_role": str(self.susan.pk),
            "role": "viewer",
        })
        assert response.status_code == HTTPStatus.OK
        content = response.content.decode()
        assert "confirm" in content.lower()

    @UserMixin.as_wendy
    def test_change_collaborator_role_confirmed(self, client):
        response = client.post("/notebooks/collaborators", {
            "notebook": self.wendys_notebook.pk,
            "change_role": str(self.susan.pk),
            "role": "viewer",
            "confirmed": "true",
        })
        assert response.status_code == HTTPStatus.FOUND
        self.susans_permission.refresh_from_db()
        assert self.susans_permission.role == NotebookPermission.Role.VIEWER

    @UserMixin.as_wendy
    def test_non_owner_cannot_add_collaborator(self, client):
        response = client.post("/notebooks/collaborators", {
            "notebook": self.susans_notebook.pk,
            "username": "mary",
            "role": "editor",
            "confirmed": "true",
        })
        assert response.status_code == HTTPStatus.FORBIDDEN
        assert not NotebookPermission.objects.filter(
            notebook=self.susans_notebook,
            user=self.mary,
        ).exists()

    def test_anonymous_cannot_add_collaborator(self, client):
        response = client.post("/notebooks/collaborators", {
            "notebook": self.wendys_notebook.pk,
            "username": "mary",
            "role": "editor",
            "confirmed": "true",
        })
        assert response.status_code == HTTPStatus.UNAUTHORIZED
        assert not NotebookPermission.objects.filter(
            notebook=self.wendys_notebook,
            user=self.mary,
        ).exists()
