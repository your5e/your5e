import html
from http import HTTPStatus

import pytest

from notebooks.tests import NotebookMixin


@pytest.mark.django_db
class TestNotebookListView(NotebookMixin):
    def test_anonymous_viewing_public_notebooks(self, client):
        response = client.get("/notebooks/")
        content = response.content.decode()
        assert html.escape("Campaign Notes") in content
        assert html.escape("Héros & Légendes") not in content
        assert html.escape("World Lore") not in content
        assert response.status_code == HTTPStatus.OK

    @NotebookMixin.as_user("wendy")
    def test_authenticated_viewing_public_notebooks(self, client):
        response = client.get("/notebooks/")
        content = response.content.decode()
        assert 'href="/notebooks/wendy/"' in content
        assert response.status_code == HTTPStatus.OK

    def test_notebook_with_description_shows_in_list(self, client):
        index_page = self.susans_notebook.get_page(path="index")
        index_page.update(
            filename="index.md",
            mime_type="text/markdown",
            data=b"---\nnotebook: Public campaign reference material\n---\n# Welcome",
            created_by=self.susan,
        )
        response = client.get("/notebooks/")
        content = response.content.decode()
        assert "Public campaign reference material" in content

    def test_notebook_without_description_shows_in_list(self, client):
        response = client.get("/notebooks/")
        content = response.content.decode()
        assert html.escape("Campaign Notes") in content


@pytest.mark.django_db
class TestNotebookMineRedirect(NotebookMixin):
    @NotebookMixin.as_user("wendy")
    def test_logged_in_user_redirects_to_own_list(self, client):
        response = client.get("/notebooks/mine")
        assert response.status_code == HTTPStatus.FOUND
        assert response.url == "/notebooks/wendy/"

    def test_anonymous_user_redirects_to_login(self, client):
        response = client.get("/notebooks/mine")
        assert response.status_code == HTTPStatus.FOUND
        assert response.url == "/login?next=/notebooks/mine"


@pytest.mark.django_db
class TestNotebookUserListView(NotebookMixin):
    @NotebookMixin.as_user("wendy")
    def test_owner_viewing_own_list(self, client):
        response = client.get("/notebooks/wendy/")
        content = response.content.decode()
        assert html.escape("Wendy's Secret") in content
        assert html.escape("World Lore") in content
        assert html.escape("Campaign Notes") in content
        assert response.status_code == HTTPStatus.OK

    @NotebookMixin.as_user("susan")
    def test_editor_viewing_other_users_list(self, client):
        response = client.get("/notebooks/wendy/")
        content = response.content.decode()
        assert html.escape("Héros & Légendes") in content
        assert html.escape("Wendy's Secret") not in content
        assert response.status_code == HTTPStatus.OK

    @NotebookMixin.as_user("mary")
    def test_viewer_viewing_other_users_list(self, client):
        response = client.get("/notebooks/wendy/")
        content = response.content.decode()
        assert html.escape("Héros & Légendes") in content
        assert html.escape("Wendy's Secret") not in content
        assert response.status_code == HTTPStatus.OK

    @NotebookMixin.as_user("hugh")
    def test_user_viewing_other_users_list(self, client):
        response = client.get("/notebooks/wendy/")
        content = response.content.decode()
        assert html.escape("Héros & Légendes") not in content
        assert html.escape("Wendy's Secret") not in content
        assert response.status_code == HTTPStatus.OK

    def test_anonymous_viewing_non_public_profile_list(self, client):
        response = client.get("/notebooks/wendy/")
        content = response.content.decode()
        assert html.escape("Héros & Légendes") not in content
        assert html.escape("Wendy's Secret") not in content
        assert response.status_code == HTTPStatus.OK

    def test_anonymous_viewing_public_profile_list(self, client):
        response = client.get("/notebooks/susan/")
        content = response.content.decode()
        assert html.escape("Campaign Notes") in content
        assert response.status_code == HTTPStatus.OK

    @NotebookMixin.as_user("wendy")
    def test_owner_sees_create_form(self, client):
        response = client.get("/notebooks/wendy/")
        content = response.content.decode()
        assert 'action="/notebooks/create"' in content

    @NotebookMixin.as_user("susan")
    def test_editor_does_not_see_create_form(self, client):
        response = client.get("/notebooks/wendy/")
        content = response.content.decode()
        assert 'action="/notebooks/create"' not in content

    @NotebookMixin.as_user("mary")
    def test_viewer_does_not_see_create_form(self, client):
        response = client.get("/notebooks/wendy/")
        content = response.content.decode()
        assert 'action="/notebooks/create"' not in content

    @NotebookMixin.as_user("hugh")
    def test_user_does_not_see_create_form(self, client):
        response = client.get("/notebooks/wendy/")
        content = response.content.decode()
        assert 'action="/notebooks/create"' not in content

    def test_anonymous_does_not_see_create_form(self, client):
        response = client.get("/notebooks/susan/")
        content = response.content.decode()
        assert 'action="/notebooks/create"' not in content
