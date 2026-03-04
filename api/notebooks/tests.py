import hashlib
import re
from http import HTTPStatus

import pytest

from api.tests import ApiMixin
from notebooks.models import Notebook
from notebooks.tests import NotebookMixin

TIMESTAMP_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")


class NotebookApiMixin(ApiMixin, NotebookMixin):
    def get_page_uuid(self, path):
        page = self.wendys_notebook.get_page(path=path)
        return str(page.uuid)

    def get_page_hash(self, path):
        page = self.wendys_notebook.get_page(path=path)
        return page.latest_version.content.hash


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
            "editable": True,
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
        filenames = [
            p["filename"]
                for p in response.json()["results"]
        ]
        assert filenames == [
            "Session One.md",
            "links.md",
            "villains/necromancer.md",
            "heroes/index.md",
            "heroes/shield.png",
            "old-draft.md",
            "notes.md",
            "heroes/theron.md",
            "index.md",
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
            "editable",
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
            "url": f"/api/notebooks/wendy/heros-legendes/{page['uuid']}",
            "html_url": "http://testserver/notebooks/wendy/heros-legendes/index",
            "filename": "index.md",
            "mime_type": "text/markdown",
            "version": 1,
            "created_by": "wendy",
            "updated_at": page["updated_at"],
            "deleted_at": None,
            "content_hash": "c97598c919faef1e6b2478920c93a932c01fa126c4581ded374e2de8918c6649",  # noqa: E501
        }

        deleted = results[5]
        assert TIMESTAMP_PATTERN.match(deleted["deleted_at"])
        assert deleted == {
            "uuid": deleted["uuid"],
            "url": f"/api/notebooks/wendy/heros-legendes/{deleted['uuid']}",
            "html_url": "http://testserver/notebooks/wendy/heros-legendes/old-draft",
            "filename": "old-draft.md",
            "mime_type": "text/markdown",
            "version": 1,
            "created_by": "wendy",
            "updated_at": None,
            "deleted_at": deleted["deleted_at"],
            "content_hash": "d04123f976133f704ccec0af8f38bd2fecc66218310485daaba4fa09694f3a7d",  # noqa: E501
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
        filenames = {
            p["filename"]
                for p in response.json()["results"]
        }
        assert filenames == {"notes.md", "links.md"}

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
        filenames = [
            p["filename"]
                for p in response.json()["results"]
        ]
        assert filenames == ["notes.md"]

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


@pytest.mark.django_db
class TestPageContent(NotebookApiMixin):
    def test_unauthenticated(self, api_client):
        uuid = self.get_page_uuid("index")
        response = api_client.get(f"/api/notebooks/wendy/heros-legendes/{uuid}")
        assert response.status_code == HTTPStatus.UNAUTHORIZED

    @ApiMixin.as_api_user("wendy")
    def test_owner(self, api_client):
        uuid = self.get_page_uuid("index")
        response = api_client.get(f"/api/notebooks/wendy/heros-legendes/{uuid}")
        assert response.status_code == HTTPStatus.OK
        assert response["Content-Type"] == "text/markdown"
        assert response.content == b"# Welcome\n\nThis is the index page."

    @ApiMixin.as_api_user("susan")
    def test_editor(self, api_client):
        from notebooks.tests import PNG_BYTES
        uuid = self.get_page_uuid("heroes/shield.png")
        response = api_client.get(f"/api/notebooks/wendy/heros-legendes/{uuid}")
        assert response.status_code == HTTPStatus.OK
        assert response["Content-Type"] == "image/png"
        assert response.content == PNG_BYTES

    @ApiMixin.as_api_user("mary")
    def test_viewer(self, api_client):
        uuid = self.get_page_uuid("index")
        response = api_client.get(f"/api/notebooks/wendy/heros-legendes/{uuid}")
        assert response.status_code == HTTPStatus.OK

    @ApiMixin.as_api_user("hugh")
    def test_user(self, api_client):
        uuid = self.get_page_uuid("index")
        response = api_client.get(f"/api/notebooks/wendy/heros-legendes/{uuid}")
        assert response.status_code == HTTPStatus.NOT_FOUND

    @ApiMixin.as_api_user("wendy")
    def test_deleted_page_returns_not_found(self, api_client):
        uuid = str(self.deleted_page.uuid)
        response = api_client.get(f"/api/notebooks/wendy/heros-legendes/{uuid}")
        assert response.status_code == HTTPStatus.NOT_FOUND

    @ApiMixin.as_api_user("wendy")
    def test_nonexistent_uuid_returns_not_found(self, api_client):
        response = api_client.get(
            "/api/notebooks/wendy/heros-legendes/00000000-0000-0000-0000-000000000000"
        )
        assert response.status_code == HTTPStatus.NOT_FOUND

    @ApiMixin.as_api_user("wendy")
    def test_invalid_uuid_returns_not_found(self, api_client):
        response = api_client.get("/api/notebooks/wendy/heros-legendes/not-a-uuid")
        assert response.status_code == HTTPStatus.NOT_FOUND

    @ApiMixin.as_api_user("wendy")
    def test_version_parameter(self, api_client):
        uuid = self.get_page_uuid("session-one")
        response = api_client.get(
            f"/api/notebooks/wendy/heros-legendes/{uuid}",
            {"version": "1"},
        )
        assert response.status_code == HTTPStatus.OK
        assert response.content == b"# Session One\n\nFirst draft."

    @ApiMixin.as_api_user("wendy")
    def test_version_parameter_invalid(self, api_client):
        uuid = self.get_page_uuid("session-one")
        response = api_client.get(
            f"/api/notebooks/wendy/heros-legendes/{uuid}",
            {"version": "999"},
        )
        assert response.status_code == HTTPStatus.NOT_FOUND

    @ApiMixin.as_api_user("wendy")
    def test_nonexistent_notebook(self, api_client):
        uuid = self.get_page_uuid("index")
        response = api_client.get(f"/api/notebooks/wendy/no-such-notebook/{uuid}")
        assert response.status_code == HTTPStatus.NOT_FOUND

    @ApiMixin.as_api_user("wendy")
    def test_nonexistent_user(self, api_client):
        uuid = self.get_page_uuid("index")
        response = api_client.get(f"/api/notebooks/nobody/some-notebook/{uuid}")
        assert response.status_code == HTTPStatus.NOT_FOUND

    @ApiMixin.as_api_user("wendy")
    def test_uuid_from_different_notebook(self, api_client):
        from wikis.models import Page
        page = Page.objects.create(wiki=self.susans_notebook)
        page.update(
            filename="test.md",
            mime_type="text/markdown",
            data=b"# Test",
            created_by=self.susan,
        )
        response = api_client.get(
            f"/api/notebooks/wendy/heros-legendes/{page.uuid}"
        )
        assert response.status_code == HTTPStatus.NOT_FOUND


@pytest.mark.django_db
class TestPageContentPut(NotebookApiMixin):
    @ApiMixin.as_api_user("wendy")
    def test_owner(self, api_client):
        uuid = self.get_page_uuid("index")
        response = api_client.put(
            f"/api/notebooks/wendy/heros-legendes/{uuid}",
            data=b"# Updated Welcome\n\nNew content.",
            content_type="text/markdown",
        )
        assert response.status_code == HTTPStatus.OK

    @ApiMixin.as_api_user("susan")
    def test_editor(self, api_client):
        uuid = self.get_page_uuid("index")
        response = api_client.put(
            f"/api/notebooks/wendy/heros-legendes/{uuid}",
            data=b"# Editor Update\n\nEdited by susan.",
            content_type="text/markdown",
        )
        assert response.status_code == HTTPStatus.OK

    @ApiMixin.as_api_user("mary")
    def test_viewer(self, api_client):
        uuid = self.get_page_uuid("index")
        response = api_client.put(
            f"/api/notebooks/wendy/heros-legendes/{uuid}",
            data=b"# Viewer Update",
            content_type="text/markdown",
        )
        assert response.status_code == HTTPStatus.FORBIDDEN

    @ApiMixin.as_api_user("hugh")
    def test_user(self, api_client):
        uuid = self.get_page_uuid("index")
        response = api_client.put(
            f"/api/notebooks/wendy/heros-legendes/{uuid}",
            data=b"# User Update",
            content_type="text/markdown",
        )
        assert response.status_code == HTTPStatus.NOT_FOUND

    def test_unauthenticated(self, api_client):
        uuid = self.get_page_uuid("index")
        response = api_client.put(
            f"/api/notebooks/wendy/heros-legendes/{uuid}",
            data=b"# Unauthenticated Update",
            content_type="text/markdown",
        )
        assert response.status_code == HTTPStatus.UNAUTHORIZED

    @ApiMixin.as_api_user("wendy")
    def test_response_fields(self, api_client):
        uuid = self.get_page_uuid("index")
        previous_hash = self.get_page_hash("index")
        new_content = b"# Response Test"
        new_hash = hashlib.sha256(new_content).hexdigest()
        response = api_client.put(
            f"/api/notebooks/wendy/heros-legendes/{uuid}",
            data=new_content,
            content_type="text/markdown",
        )
        data = response.json()
        assert TIMESTAMP_PATTERN.match(data["updated_at"])
        assert data == {
            "uuid": uuid,
            "url": f"/api/notebooks/wendy/heros-legendes/{uuid}",
            "html_url": "http://testserver/notebooks/wendy/heros-legendes/index",
            "filename": "index.md",
            "mime_type": "text/markdown",
            "version": 2,
            "created_by": "wendy",
            "updated_at": data["updated_at"],
            "content_hash": new_hash,
            "previous_hash": previous_hash,
        }
        response = api_client.get(f"/api/notebooks/wendy/heros-legendes/{uuid}")
        assert response.content == new_content

    @ApiMixin.as_api_user("wendy")
    def test_deleted_page_is_undeleted(self, api_client):
        uuid = str(self.deleted_page.uuid)
        previous_hash = self.deleted_page.latest_version.content.hash
        new_content = b"# Revived"
        new_hash = hashlib.sha256(new_content).hexdigest()
        response = api_client.put(
            f"/api/notebooks/wendy/heros-legendes/{uuid}",
            data=new_content,
            content_type="text/markdown",
        )
        data = response.json()
        assert TIMESTAMP_PATTERN.match(data["updated_at"])
        assert data == {
            "uuid": uuid,
            "url": f"/api/notebooks/wendy/heros-legendes/{uuid}",
            "html_url": "http://testserver/notebooks/wendy/heros-legendes/old-draft",
            "filename": "old-draft.md",
            "mime_type": "text/markdown",
            "version": 2,
            "created_by": "wendy",
            "updated_at": data["updated_at"],
            "content_hash": new_hash,
            "previous_hash": previous_hash,
        }
        response = api_client.get(f"/api/notebooks/wendy/heros-legendes/{uuid}")
        assert response.content == new_content

    @ApiMixin.as_api_user("wendy")
    def test_nonexistent_uuid_returns_not_found(self, api_client):
        response = api_client.put(
            "/api/notebooks/wendy/heros-legendes/00000000-0000-0000-0000-000000000000",
            data=b"# Nonexistent",
            content_type="text/markdown",
        )
        assert response.status_code == HTTPStatus.NOT_FOUND

    @ApiMixin.as_api_user("wendy")
    def test_invalid_uuid_returns_not_found(self, api_client):
        response = api_client.put(
            "/api/notebooks/wendy/heros-legendes/not-a-uuid",
            data=b"# Invalid UUID",
            content_type="text/markdown",
        )
        assert response.status_code == HTTPStatus.NOT_FOUND

    @ApiMixin.as_api_user("wendy")
    def test_nonexistent_notebook(self, api_client):
        uuid = self.get_page_uuid("index")
        response = api_client.put(
            f"/api/notebooks/wendy/no-such-notebook/{uuid}",
            data=b"# Nonexistent Notebook",
            content_type="text/markdown",
        )
        assert response.status_code == HTTPStatus.NOT_FOUND

    @ApiMixin.as_api_user("wendy")
    def test_uuid_from_different_notebook(self, api_client):
        from wikis.models import Page
        page = Page.objects.create(wiki=self.susans_notebook)
        page.update(
            filename="test.md",
            mime_type="text/markdown",
            data=b"# Test",
            created_by=self.susan,
        )
        response = api_client.put(
            f"/api/notebooks/wendy/heros-legendes/{page.uuid}",
            data=b"# Wrong Notebook",
            content_type="text/markdown",
        )
        assert response.status_code == HTTPStatus.NOT_FOUND

    @ApiMixin.as_api_user("wendy")
    def test_identical_content_no_new_version(self, api_client):
        uuid = self.get_page_uuid("index")
        original_hash = self.get_page_hash("index")
        response = api_client.put(
            f"/api/notebooks/wendy/heros-legendes/{uuid}",
            data=b"# Welcome\n\nThis is the index page.",
            content_type="text/markdown",
        )
        data = response.json()
        assert TIMESTAMP_PATTERN.match(data["updated_at"])
        assert data == {
            "uuid": uuid,
            "url": f"/api/notebooks/wendy/heros-legendes/{uuid}",
            "html_url": "http://testserver/notebooks/wendy/heros-legendes/index",
            "filename": "index.md",
            "mime_type": "text/markdown",
            "version": 1,
            "created_by": "wendy",
            "updated_at": data["updated_at"],
            "content_hash": original_hash,
            "previous_hash": original_hash,
        }


@pytest.mark.django_db
class TestPageContentPatch(NotebookApiMixin):
    @ApiMixin.as_api_user("wendy")
    def test_owner(self, api_client):
        uuid = self.get_page_uuid("index")
        response = api_client.patch(
            f"/api/notebooks/wendy/heros-legendes/{uuid}",
            data={"filename": "welcome.md"},
            format="json",
        )
        assert response.status_code == HTTPStatus.OK

    @ApiMixin.as_api_user("susan")
    def test_editor(self, api_client):
        uuid = self.get_page_uuid("index")
        response = api_client.patch(
            f"/api/notebooks/wendy/heros-legendes/{uuid}",
            data={"filename": "welcome.md"},
            format="json",
        )
        assert response.status_code == HTTPStatus.OK

    @ApiMixin.as_api_user("mary")
    def test_viewer(self, api_client):
        uuid = self.get_page_uuid("index")
        response = api_client.patch(
            f"/api/notebooks/wendy/heros-legendes/{uuid}",
            data={"filename": "welcome.md"},
            format="json",
        )
        assert response.status_code == HTTPStatus.FORBIDDEN

    @ApiMixin.as_api_user("hugh")
    def test_user(self, api_client):
        uuid = self.get_page_uuid("index")
        response = api_client.patch(
            f"/api/notebooks/wendy/heros-legendes/{uuid}",
            data={"filename": "welcome.md"},
            format="json",
        )
        assert response.status_code == HTTPStatus.NOT_FOUND

    def test_unauthenticated(self, api_client):
        uuid = self.get_page_uuid("index")
        response = api_client.patch(
            f"/api/notebooks/wendy/heros-legendes/{uuid}",
            data={"filename": "welcome.md"},
            format="json",
        )
        assert response.status_code == HTTPStatus.UNAUTHORIZED

    @ApiMixin.as_api_user("wendy")
    def test_response_fields(self, api_client):
        uuid = self.get_page_uuid("index")
        original_hash = self.get_page_hash("index")
        response = api_client.patch(
            f"/api/notebooks/wendy/heros-legendes/{uuid}",
            data={"filename": "welcome.md"},
            format="json",
        )
        data = response.json()
        assert TIMESTAMP_PATTERN.match(data["updated_at"])
        assert data == {
            "uuid": uuid,
            "url": f"/api/notebooks/wendy/heros-legendes/{uuid}",
            "html_url": "http://testserver/notebooks/wendy/heros-legendes/welcome",
            "filename": "welcome.md",
            "mime_type": "text/markdown",
            "version": 2,
            "created_by": "wendy",
            "updated_at": data["updated_at"],
            "content_hash": original_hash,
        }

    @ApiMixin.as_api_user("wendy")
    def test_content_preserved(self, api_client):
        uuid = self.get_page_uuid("index")
        api_client.patch(
            f"/api/notebooks/wendy/heros-legendes/{uuid}",
            data={"filename": "welcome.md"},
            format="json",
        )
        response = api_client.get(f"/api/notebooks/wendy/heros-legendes/{uuid}")
        assert response.content == b"# Welcome\n\nThis is the index page."

    @ApiMixin.as_api_user("wendy")
    def test_html_url_with_directory(self, api_client):
        uuid = self.get_page_uuid("index")
        response = api_client.patch(
            f"/api/notebooks/wendy/heros-legendes/{uuid}",
            data={"filename": "pages/welcome.md"},
            format="json",
        )
        data = response.json()
        assert data["html_url"] == "http://testserver/notebooks/wendy/heros-legendes/pages/welcome"
        assert data["filename"] == "pages/welcome.md"

    @ApiMixin.as_api_user("wendy")
    def test_identical_filename_no_new_version(self, api_client):
        uuid = self.get_page_uuid("index")
        original_hash = self.get_page_hash("index")
        response = api_client.patch(
            f"/api/notebooks/wendy/heros-legendes/{uuid}",
            data={"filename": "index.md"},
            format="json",
        )
        data = response.json()
        assert data == {
            "uuid": uuid,
            "url": f"/api/notebooks/wendy/heros-legendes/{uuid}",
            "html_url": "http://testserver/notebooks/wendy/heros-legendes/index",
            "filename": "index.md",
            "mime_type": "text/markdown",
            "version": 1,
            "created_by": "wendy",
            "updated_at": data["updated_at"],
            "content_hash": original_hash,
        }

    @ApiMixin.as_api_user("wendy")
    def test_nonexistent_uuid_returns_not_found(self, api_client):
        response = api_client.patch(
            "/api/notebooks/wendy/heros-legendes/00000000-0000-0000-0000-000000000000",
            data={"filename": "welcome.md"},
            format="json",
        )
        assert response.status_code == HTTPStatus.NOT_FOUND

    @ApiMixin.as_api_user("wendy")
    def test_invalid_uuid_returns_not_found(self, api_client):
        response = api_client.patch(
            "/api/notebooks/wendy/heros-legendes/not-a-uuid",
            data={"filename": "welcome.md"},
            format="json",
        )
        assert response.status_code == HTTPStatus.NOT_FOUND

    @ApiMixin.as_api_user("wendy")
    def test_nonexistent_notebook(self, api_client):
        uuid = self.get_page_uuid("index")
        response = api_client.patch(
            f"/api/notebooks/wendy/no-such-notebook/{uuid}",
            data={"filename": "welcome.md"},
            format="json",
        )
        assert response.status_code == HTTPStatus.NOT_FOUND

    @ApiMixin.as_api_user("wendy")
    def test_uuid_from_different_notebook(self, api_client):
        from wikis.models import Page
        page = Page.objects.create(wiki=self.susans_notebook)
        page.update(
            filename="test.md",
            mime_type="text/markdown",
            data=b"# Test",
            created_by=self.susan,
        )
        response = api_client.patch(
            f"/api/notebooks/wendy/heros-legendes/{page.uuid}",
            data={"filename": "welcome.md"},
            format="json",
        )
        assert response.status_code == HTTPStatus.NOT_FOUND

    @ApiMixin.as_api_user("wendy")
    def test_deleted_page_returns_not_found(self, api_client):
        uuid = str(self.deleted_page.uuid)
        response = api_client.patch(
            f"/api/notebooks/wendy/heros-legendes/{uuid}",
            data={"filename": "revived.md"},
            format="json",
        )
        assert response.status_code == HTTPStatus.NOT_FOUND

    @ApiMixin.as_api_user("wendy")
    def test_invalid_filename(self, api_client):
        uuid = self.get_page_uuid("index")
        response = api_client.patch(
            f"/api/notebooks/wendy/heros-legendes/{uuid}",
            data={"filename": "invalid[name].md"},
            format="json",
        )
        assert response.status_code == HTTPStatus.BAD_REQUEST

    @ApiMixin.as_api_user("wendy")
    def test_path_conflict(self, api_client):
        uuid = self.get_page_uuid("index")
        response = api_client.patch(
            f"/api/notebooks/wendy/heros-legendes/{uuid}",
            data={"filename": "notes.md"},
            format="json",
        )
        assert response.status_code == HTTPStatus.BAD_REQUEST

    @ApiMixin.as_api_user("wendy")
    def test_missing_filename(self, api_client):
        uuid = self.get_page_uuid("index")
        response = api_client.patch(
            f"/api/notebooks/wendy/heros-legendes/{uuid}",
            data={},
            format="json",
        )
        assert response.status_code == HTTPStatus.BAD_REQUEST


@pytest.mark.django_db
class TestPageContentPatchRevert(NotebookApiMixin):
    @ApiMixin.as_api_user("wendy")
    def test_owner(self, api_client):
        uuid = self.get_page_uuid("session-one")
        response = api_client.patch(
            f"/api/notebooks/wendy/heros-legendes/{uuid}",
            data={"revert_to": 1},
            format="json",
        )
        assert response.status_code == HTTPStatus.OK

    @ApiMixin.as_api_user("susan")
    def test_editor(self, api_client):
        uuid = self.get_page_uuid("session-one")
        response = api_client.patch(
            f"/api/notebooks/wendy/heros-legendes/{uuid}",
            data={"revert_to": 1},
            format="json",
        )
        assert response.status_code == HTTPStatus.OK

    @ApiMixin.as_api_user("mary")
    def test_viewer(self, api_client):
        uuid = self.get_page_uuid("session-one")
        response = api_client.patch(
            f"/api/notebooks/wendy/heros-legendes/{uuid}",
            data={"revert_to": 1},
            format="json",
        )
        assert response.status_code == HTTPStatus.FORBIDDEN

    @ApiMixin.as_api_user("hugh")
    def test_user(self, api_client):
        uuid = self.get_page_uuid("session-one")
        response = api_client.patch(
            f"/api/notebooks/wendy/heros-legendes/{uuid}",
            data={"revert_to": 1},
            format="json",
        )
        assert response.status_code == HTTPStatus.NOT_FOUND

    def test_unauthenticated(self, api_client):
        uuid = self.get_page_uuid("session-one")
        response = api_client.patch(
            f"/api/notebooks/wendy/heros-legendes/{uuid}",
            data={"revert_to": 1},
            format="json",
        )
        assert response.status_code == HTTPStatus.UNAUTHORIZED

    @ApiMixin.as_api_user("wendy")
    def test_response_fields(self, api_client):
        uuid = self.get_page_uuid("session-one")
        response = api_client.patch(
            f"/api/notebooks/wendy/heros-legendes/{uuid}",
            data={"revert_to": 1},
            format="json",
        )
        data = response.json()
        expected_hash = hashlib.sha256(b"# Session One\n\nFirst draft.").hexdigest()
        assert TIMESTAMP_PATTERN.match(data["updated_at"])
        assert data == {
            "uuid": uuid,
            "url": f"/api/notebooks/wendy/heros-legendes/{uuid}",
            "html_url": "http://testserver/notebooks/wendy/heros-legendes/session-one",
            "filename": "Session One.md",
            "mime_type": "text/markdown",
            "version": 4,
            "created_by": "wendy",
            "updated_at": data["updated_at"],
            "content_hash": expected_hash,
        }

    @ApiMixin.as_api_user("wendy")
    def test_invalid_version(self, api_client):
        uuid = self.get_page_uuid("session-one")
        response = api_client.patch(
            f"/api/notebooks/wendy/heros-legendes/{uuid}",
            data={"revert_to": 999},
            format="json",
        )
        assert response.status_code == HTTPStatus.BAD_REQUEST

    @ApiMixin.as_api_user("wendy")
    def test_revert_to_and_filename_mutually_exclusive(self, api_client):
        uuid = self.get_page_uuid("session-one")
        response = api_client.patch(
            f"/api/notebooks/wendy/heros-legendes/{uuid}",
            data={"revert_to": 1, "filename": "new-name.md"},
            format="json",
        )
        assert response.status_code == HTTPStatus.BAD_REQUEST

    @ApiMixin.as_api_user("wendy")
    def test_revert_to_current_version_no_new_version(self, api_client):
        uuid = self.get_page_uuid("session-one")
        response = api_client.patch(
            f"/api/notebooks/wendy/heros-legendes/{uuid}",
            data={"revert_to": 3},
            format="json",
        )
        data = response.json()
        assert data["version"] == 3


@pytest.mark.django_db
class TestPageCreate(NotebookApiMixin):
    def test_unauthenticated(self, api_client):
        from django.core.files.uploadedfile import SimpleUploadedFile
        response = api_client.post(
            "/api/notebooks/wendy/heros-legendes/",
            data={"file": SimpleUploadedFile("test.md", b"# New Page")},
            format="multipart",
        )
        assert response.status_code == HTTPStatus.UNAUTHORIZED

    @ApiMixin.as_api_user("wendy")
    def test_owner(self, api_client):
        from django.core.files.uploadedfile import SimpleUploadedFile
        response = api_client.post(
            "/api/notebooks/wendy/heros-legendes/",
            data={"file": SimpleUploadedFile("new-page.md", b"# New Page")},
            format="multipart",
        )
        assert response.status_code == HTTPStatus.CREATED

    @ApiMixin.as_api_user("susan")
    def test_editor(self, api_client):
        from django.core.files.uploadedfile import SimpleUploadedFile
        response = api_client.post(
            "/api/notebooks/wendy/heros-legendes/",
            data={"file": SimpleUploadedFile("editor-page.md", b"# Editor Page")},
            format="multipart",
        )
        assert response.status_code == HTTPStatus.CREATED

    @ApiMixin.as_api_user("mary")
    def test_viewer(self, api_client):
        from django.core.files.uploadedfile import SimpleUploadedFile
        response = api_client.post(
            "/api/notebooks/wendy/heros-legendes/",
            data={"file": SimpleUploadedFile("viewer-page.md", b"# Viewer Page")},
            format="multipart",
        )
        assert response.status_code == HTTPStatus.FORBIDDEN

    @ApiMixin.as_api_user("hugh")
    def test_user(self, api_client):
        from django.core.files.uploadedfile import SimpleUploadedFile
        response = api_client.post(
            "/api/notebooks/wendy/heros-legendes/",
            data={"file": SimpleUploadedFile("user-page.md", b"# User Page")},
            format="multipart",
        )
        assert response.status_code == HTTPStatus.NOT_FOUND

    @ApiMixin.as_api_user("wendy")
    def test_response_fields(self, api_client):
        from django.core.files.uploadedfile import SimpleUploadedFile
        content = b"# Response Test\n\nContent here."
        content_hash = hashlib.sha256(content).hexdigest()
        response = api_client.post(
            "/api/notebooks/wendy/heros-legendes/",
            data={"file": SimpleUploadedFile("response-test.md", content)},
            format="multipart",
        )
        data = response.json()
        assert TIMESTAMP_PATTERN.match(data["updated_at"])
        assert data == {
            "uuid": data["uuid"],
            "url": f"/api/notebooks/wendy/heros-legendes/{data['uuid']}",
            "html_url": "http://testserver/notebooks/wendy/heros-legendes/response-test",
            "filename": "response-test.md",
            "mime_type": "text/markdown",
            "version": 1,
            "created_by": "wendy",
            "updated_at": data["updated_at"],
            "content_hash": content_hash,
        }

    @ApiMixin.as_api_user("wendy")
    def test_content_retrievable(self, api_client):
        from django.core.files.uploadedfile import SimpleUploadedFile
        content = b"# Retrievable\n\nThis content should be retrievable."
        response = api_client.post(
            "/api/notebooks/wendy/heros-legendes/",
            data={"file": SimpleUploadedFile("retrievable.md", content)},
            format="multipart",
        )
        uuid = response.json()["uuid"]
        response = api_client.get(f"/api/notebooks/wendy/heros-legendes/{uuid}")
        assert response.content == content

    @ApiMixin.as_api_user("wendy")
    def test_filename_override(self, api_client):
        from django.core.files.uploadedfile import SimpleUploadedFile
        response = api_client.post(
            "/api/notebooks/wendy/heros-legendes/",
            data={
                "file": SimpleUploadedFile("original.md", b"# Override Test"),
                "filename": "custom-name.md",
            },
            format="multipart",
        )
        data = response.json()
        assert data["filename"] == "custom-name.md"
        assert data["html_url"] == "http://testserver/notebooks/wendy/heros-legendes/custom-name"

    @ApiMixin.as_api_user("wendy")
    def test_filename_with_directory(self, api_client):
        from django.core.files.uploadedfile import SimpleUploadedFile
        response = api_client.post(
            "/api/notebooks/wendy/heros-legendes/",
            data={
                "file": SimpleUploadedFile("nested.md", b"# Nested"),
                "filename": "subdir/nested.md",
            },
            format="multipart",
        )
        data = response.json()
        assert data["filename"] == "subdir/nested.md"
        assert data["html_url"] == "http://testserver/notebooks/wendy/heros-legendes/subdir/nested"

    @ApiMixin.as_api_user("wendy")
    def test_image_upload(self, api_client):
        from django.core.files.uploadedfile import SimpleUploadedFile

        from notebooks.tests import PNG_BYTES
        response = api_client.post(
            "/api/notebooks/wendy/heros-legendes/",
            data={"file": SimpleUploadedFile("test-image.png", PNG_BYTES)},
            format="multipart",
        )
        data = response.json()
        assert data["mime_type"] == "image/png"
        assert data["filename"] == "test-image.png"

    @ApiMixin.as_api_user("wendy")
    def test_no_file_extension_rejected(self, api_client):
        from django.core.files.uploadedfile import SimpleUploadedFile
        response = api_client.post(
            "/api/notebooks/wendy/heros-legendes/",
            data={"file": SimpleUploadedFile("noextension", b"# No Extension")},
            format="multipart",
        )
        assert response.status_code == HTTPStatus.BAD_REQUEST

    @ApiMixin.as_api_user("wendy")
    def test_filename_override_no_extension_rejected(self, api_client):
        from django.core.files.uploadedfile import SimpleUploadedFile
        response = api_client.post(
            "/api/notebooks/wendy/heros-legendes/",
            data={
                "file": SimpleUploadedFile("valid.md", b"# Valid"),
                "filename": "noextension",
            },
            format="multipart",
        )
        assert response.status_code == HTTPStatus.BAD_REQUEST

    @ApiMixin.as_api_user("wendy")
    def test_page_already_exists_rejected(self, api_client):
        from django.core.files.uploadedfile import SimpleUploadedFile
        response = api_client.post(
            "/api/notebooks/wendy/heros-legendes/",
            data={"file": SimpleUploadedFile("index.md", b"# Duplicate")},
            format="multipart",
        )
        assert response.status_code == HTTPStatus.CONFLICT

    @ApiMixin.as_api_user("wendy")
    def test_path_conflict_rejected(self, api_client):
        from django.core.files.uploadedfile import SimpleUploadedFile
        response = api_client.post(
            "/api/notebooks/wendy/heros-legendes/",
            data={"file": SimpleUploadedFile("Index.md", b"# Path Conflict")},
            format="multipart",
        )
        assert response.status_code == HTTPStatus.CONFLICT

    @ApiMixin.as_api_user("wendy")
    def test_no_file_rejected(self, api_client):
        response = api_client.post(
            "/api/notebooks/wendy/heros-legendes/",
            data={},
            format="multipart",
        )
        assert response.status_code == HTTPStatus.BAD_REQUEST

    @ApiMixin.as_api_user("wendy")
    def test_nonexistent_notebook(self, api_client):
        from django.core.files.uploadedfile import SimpleUploadedFile
        response = api_client.post(
            "/api/notebooks/wendy/no-such-notebook/",
            data={"file": SimpleUploadedFile("test.md", b"# Test")},
            format="multipart",
        )
        assert response.status_code == HTTPStatus.NOT_FOUND

    @ApiMixin.as_api_user("wendy")
    def test_nonexistent_user(self, api_client):
        from django.core.files.uploadedfile import SimpleUploadedFile
        response = api_client.post(
            "/api/notebooks/nobody/some-notebook/",
            data={"file": SimpleUploadedFile("test.md", b"# Test")},
            format="multipart",
        )
        assert response.status_code == HTTPStatus.NOT_FOUND


@pytest.mark.django_db
class TestPageContentDelete(NotebookApiMixin):
    @ApiMixin.as_api_user("wendy")
    def test_owner(self, api_client):
        uuid = self.get_page_uuid("index")
        response = api_client.delete(f"/api/notebooks/wendy/heros-legendes/{uuid}")
        assert response.status_code == HTTPStatus.NO_CONTENT

    @ApiMixin.as_api_user("susan")
    def test_editor(self, api_client):
        uuid = self.get_page_uuid("index")
        response = api_client.delete(f"/api/notebooks/wendy/heros-legendes/{uuid}")
        assert response.status_code == HTTPStatus.NO_CONTENT

    @ApiMixin.as_api_user("mary")
    def test_viewer(self, api_client):
        uuid = self.get_page_uuid("index")
        response = api_client.delete(f"/api/notebooks/wendy/heros-legendes/{uuid}")
        assert response.status_code == HTTPStatus.FORBIDDEN

    @ApiMixin.as_api_user("hugh")
    def test_user(self, api_client):
        uuid = self.get_page_uuid("index")
        response = api_client.delete(f"/api/notebooks/wendy/heros-legendes/{uuid}")
        assert response.status_code == HTTPStatus.NOT_FOUND

    def test_unauthenticated(self, api_client):
        uuid = self.get_page_uuid("index")
        response = api_client.delete(f"/api/notebooks/wendy/heros-legendes/{uuid}")
        assert response.status_code == HTTPStatus.UNAUTHORIZED

    @ApiMixin.as_api_user("wendy")
    def test_page_is_soft_deleted(self, api_client):
        uuid = self.get_page_uuid("index")
        response = api_client.delete(f"/api/notebooks/wendy/heros-legendes/{uuid}")
        assert response.status_code == HTTPStatus.NO_CONTENT

        response = api_client.get(f"/api/notebooks/wendy/heros-legendes/{uuid}")
        assert response.status_code == HTTPStatus.NOT_FOUND

    @ApiMixin.as_api_user("wendy")
    def test_deleted_page_returns_not_found(self, api_client):
        uuid = str(self.deleted_page.uuid)
        response = api_client.delete(f"/api/notebooks/wendy/heros-legendes/{uuid}")
        assert response.status_code == HTTPStatus.NOT_FOUND

    @ApiMixin.as_api_user("wendy")
    def test_nonexistent_uuid_returns_not_found(self, api_client):
        response = api_client.delete(
            "/api/notebooks/wendy/heros-legendes/00000000-0000-0000-0000-000000000000"
        )
        assert response.status_code == HTTPStatus.NOT_FOUND

    @ApiMixin.as_api_user("wendy")
    def test_invalid_uuid_returns_not_found(self, api_client):
        response = api_client.delete(
            "/api/notebooks/wendy/heros-legendes/not-a-uuid"
        )
        assert response.status_code == HTTPStatus.NOT_FOUND

    @ApiMixin.as_api_user("wendy")
    def test_nonexistent_notebook(self, api_client):
        uuid = self.get_page_uuid("index")
        response = api_client.delete(f"/api/notebooks/wendy/no-such-notebook/{uuid}")
        assert response.status_code == HTTPStatus.NOT_FOUND

    @ApiMixin.as_api_user("wendy")
    def test_uuid_from_different_notebook(self, api_client):
        from wikis.models import Page
        page = Page.objects.create(wiki=self.susans_notebook)
        page.update(
            filename="test.md",
            mime_type="text/markdown",
            data=b"# Test",
            created_by=self.susan,
        )
        response = api_client.delete(
            f"/api/notebooks/wendy/heros-legendes/{page.uuid}"
        )
        assert response.status_code == HTTPStatus.NOT_FOUND
