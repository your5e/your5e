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
            "url": "/api/notebooks/wendy/heros-legendes/",
            "html_url": "http://testserver/notebooks/wendy/heros-legendes/",
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


@pytest.mark.django_db
class TestNotebookPages(NotebookApiMixin):
    def assert_wendys_notebook_pages(self, response):
        assert response.status_code == HTTPStatus.OK
        paths = [
            p["path"]
                for p in response.json()["results"]
        ]
        assert paths == [
            "session-one",
            "links",
            "villains/necromancer",
            "heroes/index",
            "heroes/shield.png",
            "old-draft",
            "notes",
            "heroes/theron",
            "index",
        ]

    def test_unauthenticated(self, api_client):
        response = api_client.get("/api/notebooks/wendy/heros-legendes/")
        assert response.status_code == HTTPStatus.UNAUTHORIZED

    @ApiMixin.as_api_user("wendy")
    def test_owner(self, api_client):
        response = api_client.get("/api/notebooks/wendy/heros-legendes/")
        self.assert_wendys_notebook_pages(response)

    @ApiMixin.as_api_user("susan")
    def test_editor(self, api_client):
        response = api_client.get("/api/notebooks/wendy/heros-legendes/")
        self.assert_wendys_notebook_pages(response)

    @ApiMixin.as_api_user("mary")
    def test_viewer(self, api_client):
        response = api_client.get("/api/notebooks/wendy/heros-legendes/")
        self.assert_wendys_notebook_pages(response)

    @ApiMixin.as_api_user("hugh")
    def test_user(self, api_client):
        response = api_client.get("/api/notebooks/wendy/heros-legendes/")
        assert response.status_code == HTTPStatus.NOT_FOUND

    @ApiMixin.as_api_user("wendy")
    def test_response_structure(self, api_client):
        response = api_client.get("/api/notebooks/wendy/heros-legendes/")
        assert set(response.json().keys()) == {
            "next",
            "previous",
            "results",
            "total_results",
        }

    @ApiMixin.as_api_user("wendy")
    def test_response_fields(self, api_client):
        response = api_client.get("/api/notebooks/wendy/heros-legendes/")
        results = response.json()["results"]

        page = results[8]
        assert TIMESTAMP_PATTERN.match(page["updated_at"])
        assert page == {
            "uuid": page["uuid"],
            "path": "index",
            "filename": "index.md",
            "mime_type": "text/markdown",
            "version": 1,
            "created_by": "wendy",
            "updated_at": page["updated_at"],
            "deleted_at": None,
        }

        deleted = results[5]
        assert TIMESTAMP_PATTERN.match(deleted["deleted_at"])
        assert deleted == {
            "uuid": deleted["uuid"],
            "path": "old-draft",
            "filename": "old-draft.md",
            "mime_type": "text/markdown",
            "version": 1,
            "created_by": "wendy",
            "updated_at": None,
            "deleted_at": deleted["deleted_at"],
        }

    @ApiMixin.as_api_user("wendy")
    def test_nonexistent_notebook(self, api_client):
        response = api_client.get("/api/notebooks/wendy/no-such-notebook/")
        assert response.status_code == HTTPStatus.NOT_FOUND

    @ApiMixin.as_api_user("wendy")
    def test_nonexistent_user(self, api_client):
        response = api_client.get("/api/notebooks/nobody/some-notebook/")
        assert response.status_code == HTTPStatus.NOT_FOUND

    @ApiMixin.as_api_user("wendy")
    def test_since_filter(self, api_client):
        from django.utils import timezone

        cutoff = timezone.now().strftime("%Y-%m-%dT%H:%M:%SZ")

        updated = self.wendys_notebook.get_page(path="notes")
        updated.update(
            filename="notes.md",
            mime_type="text/markdown",
            data=b"# Notes\n\nUpdated after cutoff.",
            created_by=self.wendy,
        )

        deleted = self.wendys_notebook.get_page(path="links")
        deleted.soft_delete()

        response = api_client.get(
            "/api/notebooks/wendy/heros-legendes/",
            {"since": cutoff},
        )
        assert response.status_code == HTTPStatus.OK
        paths = {
            p["path"]
                for p in response.json()["results"]
        }
        assert paths == {"notes", "links"}

    @ApiMixin.as_api_user("wendy")
    def test_since_filter_no_updates(self, api_client):
        from django.utils import timezone

        cutoff = timezone.now().strftime("%Y-%m-%dT%H:%M:%SZ")

        response = api_client.get(
            "/api/notebooks/wendy/heros-legendes/",
            {"since": cutoff},
        )
        assert response.status_code == HTTPStatus.OK
        assert response.json()["results"] == []

    @ApiMixin.as_api_user("wendy")
    def test_since_filter_unix_timestamp(self, api_client):
        from django.utils import timezone

        cutoff = int(timezone.now().timestamp())

        page = self.wendys_notebook.get_page(path="notes")
        page.update(
            filename="notes.md",
            mime_type="text/markdown",
            data=b"# Notes\n\nUpdated after cutoff.",
            created_by=self.wendy,
        )

        response = api_client.get(
            "/api/notebooks/wendy/heros-legendes/",
            {"since": str(cutoff)},
        )
        assert response.status_code == HTTPStatus.OK
        paths = [
            p["path"]
                for p in response.json()["results"]
        ]
        assert paths == ["notes"]

    @ApiMixin.as_api_user("wendy")
    def test_since_filter_invalid(self, api_client):
        response = api_client.get(
            "/api/notebooks/wendy/heros-legendes/",
            {"since": "banana"},
        )
        assert response.status_code == HTTPStatus.BAD_REQUEST

        response = api_client.get(
            "/api/notebooks/wendy/heros-legendes/",
            {"since": "index.md"},
        )
        assert response.status_code == HTTPStatus.BAD_REQUEST

    @ApiMixin.as_api_user("wendy")
    def test_cursor_pagination(self, api_client):
        from api.notebooks.views import PAGE_SIZE
        from wikis.models import Page

        for i in range(PAGE_SIZE + 2):
            page = Page.objects.create(wiki=self.wendys_notebook)
            page.update(
                filename=f"page-{i:02d}.md",
                mime_type="text/markdown",
                data=f"# Page {i}".encode(),
                created_by=self.wendy,
            )

        first_page = api_client.get("/api/notebooks/wendy/heros-legendes/")
        assert len(first_page.json()["results"]) == PAGE_SIZE
        assert first_page.json()["next"] is not None
        assert first_page.json()["previous"] is None

        second_page = api_client.get(first_page.json()["next"])
        assert second_page.json()["previous"] is not None

    @ApiMixin.as_api_user("wendy")
    def test_since_filter_with_pagination(self, api_client):
        from django.utils import timezone

        from api.notebooks.views import PAGE_SIZE
        from wikis.models import Page

        cutoff = timezone.now().strftime("%Y-%m-%dT%H:%M:%SZ")

        for i in range(PAGE_SIZE + 2):
            page = Page.objects.create(wiki=self.wendys_notebook)
            page.update(
                filename=f"new-{i:02d}.md",
                mime_type="text/markdown",
                data=f"# New {i}".encode(),
                created_by=self.wendy,
            )

        first_page = api_client.get(
            "/api/notebooks/wendy/heros-legendes/",
            {"since": cutoff},
        )
        assert len(first_page.json()["results"]) == PAGE_SIZE
        assert first_page.json()["next"] is not None

        second_page = api_client.get(first_page.json()["next"])
        assert len(second_page.json()["results"]) == 2
        assert second_page.json()["previous"] is not None
