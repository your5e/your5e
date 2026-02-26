import re
from http import HTTPStatus

import pytest

from api.tests import ApiMixin
from notebooks.models import Notebook
from notebooks.tests import NotebookMixin

TIMESTAMP_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")


class NotebookApiMixin(ApiMixin, NotebookMixin):
    pass


@pytest.mark.django_db
class TestNotebooksList(NotebookApiMixin):
    def test_unauthenticated(self, api_client):
        response = api_client.get("/api/notebooks/")
        assert response.status_code == HTTPStatus.UNAUTHORIZED

    @ApiMixin.as_api_user("wendy")
    def test_owner(self, api_client):
        response = api_client.get("/api/notebooks/")
        assert response.status_code == HTTPStatus.OK
        assert [
            n["name"]
                for n in response.json()["results"]
        ] == [
            "World Lore",
            "Campaign Notes",
            "Héros & Légendes",
        ]

    @ApiMixin.as_api_user("susan")
    def test_editor(self, api_client):
        response = api_client.get("/api/notebooks/")
        assert [
            n["name"]
                for n in response.json()["results"]
        ] == [
            "World Lore",
            "Campaign Notes",
            "Héros & Légendes",
        ]

    @ApiMixin.as_api_user("mary")
    def test_viewer(self, api_client):
        response = api_client.get("/api/notebooks/")
        assert [
            n["name"]
                for n in response.json()["results"]
        ] == [
            "World Lore",
            "Campaign Notes",
            "Héros & Légendes",
        ]

    @ApiMixin.as_api_user("hugh")
    def test_user(self, api_client):
        response = api_client.get("/api/notebooks/")
        assert [
            n["name"]
                for n in response.json()["results"]
        ] == [
            "World Lore",
            "Campaign Notes",
        ]

    @ApiMixin.as_api_user("wendy")
    def test_response_fields(self, api_client):
        response = api_client.get("/api/notebooks/")
        notebook = response.json()["results"][2]
        assert TIMESTAMP_PATTERN.match(notebook["last_updated"])
        assert notebook == {
            "name": "Héros & Légendes",
            "slug": "heros-legendes",
            "owner": "wendy",
            "visibility": "private",
            "url": "/notebooks/wendy/heros-legendes/",
            "last_updated": notebook["last_updated"],
            "copied_from": None,
        }

    @ApiMixin.as_api_user("wendy")
    def test_response_structure(self, api_client):
        response = api_client.get("/api/notebooks/")
        assert set(response.json().keys()) == {
            "next",
            "previous",
            "results",
            "total_results",
        }

    @ApiMixin.as_api_user("wendy")
    def test_cursor_pagination(self, api_client):
        from api.notebooks.views import PAGE_SIZE
        for i in range(PAGE_SIZE + 2):
            Notebook.objects.create(
                name=f"Notebook {i:02d}",
                owner=self.wendy,
            )

        first_page = api_client.get("/api/notebooks/")
        assert len(first_page.json()["results"]) == PAGE_SIZE
        assert first_page.json()["next"] is not None
        assert first_page.json()["previous"] is None

        second_page = api_client.get(first_page.json()["next"])
        assert len(second_page.json()["results"]) == 5
        assert second_page.json()["previous"] is not None


@pytest.mark.django_db
class TestNotebooksPublic(NotebookApiMixin):
    def test_unauthenticated(self, api_client):
        response = api_client.get("/api/notebooks/public")
        assert response.status_code == HTTPStatus.UNAUTHORIZED

    @ApiMixin.as_api_user("susan")
    def test_owner(self, api_client):
        response = api_client.get("/api/notebooks/public")
        assert response.status_code == HTTPStatus.OK
        assert [
            n["name"]
                for n in response.json()["results"]
        ] == [
            "Campaign Notes",
        ]

    @ApiMixin.as_api_user("mary")
    def test_editor(self, api_client):
        response = api_client.get("/api/notebooks/public")
        assert [
            n["name"]
                for n in response.json()["results"]
        ] == [
            "Campaign Notes",
        ]

    @ApiMixin.as_api_user("wendy")
    def test_viewer(self, api_client):
        response = api_client.get("/api/notebooks/public")
        assert [
            n["name"]
                for n in response.json()["results"]
        ] == [
            "Campaign Notes",
        ]

    @ApiMixin.as_api_user("hugh")
    def test_user(self, api_client):
        response = api_client.get("/api/notebooks/public")
        assert [
            n["name"]
                for n in response.json()["results"]
        ] == [
            "Campaign Notes",
        ]


@pytest.mark.django_db
class TestNotebooksInternal(NotebookApiMixin):
    def test_unauthenticated(self, api_client):
        response = api_client.get("/api/notebooks/internal")
        assert response.status_code == HTTPStatus.UNAUTHORIZED

    @ApiMixin.as_api_user("mary")
    def test_owner(self, api_client):
        response = api_client.get("/api/notebooks/internal")
        assert response.status_code == HTTPStatus.OK
        assert [
            n["name"]
                for n in response.json()["results"]
        ] == [
            "World Lore",
        ]

    @ApiMixin.as_api_user("wendy")
    def test_editor(self, api_client):
        response = api_client.get("/api/notebooks/internal")
        assert [
            n["name"]
                for n in response.json()["results"]
        ] == [
            "World Lore",
        ]

    @ApiMixin.as_api_user("susan")
    def test_viewer(self, api_client):
        response = api_client.get("/api/notebooks/internal")
        assert [
            n["name"]
                for n in response.json()["results"]
        ] == [
            "World Lore",
        ]

    @ApiMixin.as_api_user("hugh")
    def test_user(self, api_client):
        response = api_client.get("/api/notebooks/internal")
        assert [
            n["name"]
                for n in response.json()["results"]
        ] == [
            "World Lore",
        ]


@pytest.mark.django_db
class TestNotebooksPrivate(NotebookApiMixin):
    def test_unauthenticated(self, api_client):
        response = api_client.get("/api/notebooks/private")
        assert response.status_code == HTTPStatus.UNAUTHORIZED

    @ApiMixin.as_api_user("wendy")
    def test_owner(self, api_client):
        response = api_client.get("/api/notebooks/private")
        assert response.status_code == HTTPStatus.OK
        assert [
            n["name"]
                for n in response.json()["results"]
        ] == [
            "Héros & Légendes",
        ]

    @ApiMixin.as_api_user("susan")
    def test_editor(self, api_client):
        response = api_client.get("/api/notebooks/private")
        assert [
            n["name"]
                for n in response.json()["results"]
        ] == [
            "Héros & Légendes",
        ]

    @ApiMixin.as_api_user("mary")
    def test_viewer(self, api_client):
        response = api_client.get("/api/notebooks/private")
        assert [
            n["name"]
                for n in response.json()["results"]
        ] == [
            "Héros & Légendes",
        ]

    @ApiMixin.as_api_user("hugh")
    def test_user(self, api_client):
        response = api_client.get("/api/notebooks/private")
        assert [
            n["name"]
                for n in response.json()["results"]
        ] == []


@pytest.mark.django_db
class TestNotebooksUser(NotebookApiMixin):
    def test_unauthenticated(self, api_client):
        response = api_client.get("/api/notebooks/wendy/")
        assert response.status_code == HTTPStatus.UNAUTHORIZED

    @ApiMixin.as_api_user("wendy")
    def test_owner(self, api_client):
        response = api_client.get("/api/notebooks/wendy/")
        assert response.status_code == HTTPStatus.OK
        assert [
            n["name"]
                for n in response.json()["results"]
        ] == [
            "Héros & Légendes",
        ]

    @ApiMixin.as_api_user("susan")
    def test_editor(self, api_client):
        response = api_client.get("/api/notebooks/wendy/")
        assert [
            n["name"]
                for n in response.json()["results"]
        ] == [
            "Héros & Légendes",
        ]

    @ApiMixin.as_api_user("mary")
    def test_viewer(self, api_client):
        response = api_client.get("/api/notebooks/wendy/")
        assert [
            n["name"]
                for n in response.json()["results"]
        ] == [
            "Héros & Légendes",
        ]

    @ApiMixin.as_api_user("hugh")
    def test_user(self, api_client):
        response = api_client.get("/api/notebooks/wendy/")
        assert [
            n["name"]
                for n in response.json()["results"]
        ] == []

    @ApiMixin.as_api_user("wendy")
    def test_nonexistent_user(self, api_client):
        response = api_client.get("/api/notebooks/nobody/")
        assert response.status_code == HTTPStatus.NOT_FOUND
