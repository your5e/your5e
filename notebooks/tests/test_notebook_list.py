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

    def test_anonymous_viewing_other_users_list(self, client):
        response = client.get("/notebooks/wendy/")
        assert response.status_code == HTTPStatus.UNAUTHORIZED
