import html
from http import HTTPStatus

import pytest

from campaigns.tests import LinkedCampaignNotebooksMixin


class TestNotebookListRedirect:
    def test_user_notebooks_redirects_to_list(self, client):
        response = client.get("/notebooks/wendy/")
        assert response.status_code == HTTPStatus.FOUND
        assert response.url == "/notebooks/"


@pytest.mark.django_db
class TestNotebookListView(LinkedCampaignNotebooksMixin):
    @LinkedCampaignNotebooksMixin.as_user("wendy")
    def test_user_sees_owned_and_collaborated_notebooks(self, client):
        response = client.get("/notebooks/")
        assert response.status_code == HTTPStatus.OK
        content = response.content.decode()
        assert html.escape("Wendy's Notes") in content
        assert html.escape("Mary's Prayer") in content
        assert 'href="/notebooks/create"' in content
        assert "The Old Forest" in content

    @LinkedCampaignNotebooksMixin.as_user("hugh")
    def test_user_with_no_access_sees_empty_list(self, client):
        response = client.get("/notebooks/")
        assert response.status_code == HTTPStatus.OK
        content = response.content.decode()
        assert html.escape("Wendy's Notes") not in content
        assert html.escape("Mary's Prayer") not in content

    def test_anonymous_cannot_view(self, client):
        response = client.get("/notebooks/")
        assert response.status_code == HTTPStatus.UNAUTHORIZED
