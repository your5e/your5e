from http import HTTPStatus
from io import BytesIO

import pytest

from notebooks.models import Notebook, NotebookPermission
from users.tests import UserMixin
from wikis.models import Page

from . import NotebookMixin


@pytest.mark.django_db
class TestNotebookSettingsView(NotebookMixin):
    @UserMixin.as_user("wendy")
    def test_owner_sees_modification_options(self, client):
        response = client.get("/notebooks/settings/wendy/heros-legendes/")
        assert response.status_code == HTTPStatus.OK
        content = response.content.decode()
        assert 'action="/notebooks/rename"' in content
        assert 'action="/notebooks/visibility"' in content
        assert 'action="/notebooks/collaborators"' in content
        assert 'action="/notebooks/delete"' in content
        assert 'value="Héros &amp; Légendes"' in content
        assert 'value="private" selected' in content
        normalised = " ".join(content.split())
        assert (
            'susan</a> <select name="role"> <option value="editor" selected>'
            in normalised
        )
        assert (
            'mary</a> <select name="role"> <option value="editor" >Editor</option>'
            ' <option value="viewer" selected>' in normalised
        )

    @UserMixin.as_user("susan")
    def test_editor_cannot_access_settings(self, client):
        response = client.get("/notebooks/settings/wendy/heros-legendes/")
        assert response.status_code == HTTPStatus.FORBIDDEN

    @UserMixin.as_user("mary")
    def test_viewer_cannot_access_settings(self, client):
        response = client.get("/notebooks/settings/wendy/heros-legendes/")
        assert response.status_code == HTTPStatus.FORBIDDEN

    @UserMixin.as_user("hugh")
    def test_non_collaborator_cannot_access_settings(self, client):
        response = client.get("/notebooks/settings/wendy/heros-legendes/")
        assert response.status_code == HTTPStatus.FORBIDDEN

    def test_anonymous_cannot_access_settings(self, client):
        response = client.get("/notebooks/settings/wendy/heros-legendes/")
        assert response.status_code == HTTPStatus.UNAUTHORIZED


@pytest.mark.django_db
class TestNotebookDeletedPagesView(NotebookMixin):
    @UserMixin.as_user("wendy")
    def test_owner_can_access_deleted_pages(self, client):
        response = client.get("/notebooks/deleted/wendy/heros-legendes/")
        assert response.status_code == HTTPStatus.OK
        content = response.content.decode()
        assert "<h1>Deleted Pages</h1>" in content
        assert (
            f'<a href="/notebooks/restore?page={self.deleted_page.uuid}">Restore</a>'
            in content
        )

    @UserMixin.as_user("susan")
    def test_editor_can_access_deleted_pages(self, client):
        response = client.get("/notebooks/deleted/wendy/heros-legendes/")
        assert response.status_code == HTTPStatus.OK

    @UserMixin.as_user("mary")
    def test_viewer_cannot_access_deleted_pages(self, client):
        response = client.get("/notebooks/deleted/wendy/heros-legendes/")
        assert response.status_code == HTTPStatus.FORBIDDEN

    @UserMixin.as_user("hugh")
    def test_non_collaborator_cannot_access_deleted_pages(self, client):
        response = client.get("/notebooks/deleted/wendy/heros-legendes/")
        assert response.status_code == HTTPStatus.FORBIDDEN

    def test_anonymous_cannot_access_deleted_pages(self, client):
        response = client.get("/notebooks/deleted/wendy/heros-legendes/")
        assert response.status_code == HTTPStatus.UNAUTHORIZED

    @UserMixin.as_user("wendy")
    def test_index_links_to_deleted_pages_view(self, client):
        response = client.get("/notebooks/wendy/heros-legendes/")
        content = response.content.decode()
        assert '<p class="notebook-name">Héros &amp; Légendes</p>' in content
        assert 'href="/notebooks/deleted/wendy/heros-legendes/"' in content


@pytest.mark.django_db
class TestNotebookPageCreateView(NotebookMixin):
    @UserMixin.as_user("wendy")
    def test_owner_can_access_create_page(self, client):
        response = client.get("/notebooks/create-page/wendy/heros-legendes/")
        assert response.status_code == HTTPStatus.OK
        content = response.content.decode()
        assert 'name="filename"' in content
        assert 'name="content"' in content
        assert 'name="file"' in content
        assert 'action="/notebooks/wendy/heros-legendes/new-page"' in content
        assert 'action="/notebooks/upload"' in content
        assert f'name="notebook" value="{self.wendys_notebook.pk}"' in content

    @UserMixin.as_user("susan")
    def test_editor_can_access_create_page(self, client):
        response = client.get("/notebooks/create-page/wendy/heros-legendes/")
        assert response.status_code == HTTPStatus.OK

    @UserMixin.as_user("mary")
    def test_viewer_cannot_access_create_page(self, client):
        response = client.get("/notebooks/create-page/wendy/heros-legendes/")
        assert response.status_code == HTTPStatus.FORBIDDEN

    @UserMixin.as_user("hugh")
    def test_non_collaborator_cannot_access_create_page(self, client):
        response = client.get("/notebooks/create-page/wendy/heros-legendes/")
        assert response.status_code == HTTPStatus.FORBIDDEN

    def test_anonymous_cannot_access_create_page(self, client):
        response = client.get("/notebooks/create-page/wendy/heros-legendes/")
        assert response.status_code == HTTPStatus.UNAUTHORIZED


@pytest.mark.django_db
class TestNotebookDeleteView(NotebookMixin):
    @UserMixin.as_user("wendy")
    def test_empty_notebook_deletes_immediately(self, client):
        empty_notebook = Notebook.objects.create(
            name="Empty Notebook",
            owner=self.wendy,
        )
        notebook_id = empty_notebook.id
        response = client.post(
            "/notebooks/delete",
            {"notebook": empty_notebook.pk},
        )
        assert response.status_code == HTTPStatus.FOUND
        assert response.url == "/profile/wendy/"
        assert not Notebook.objects.filter(id=notebook_id).exists()

    @UserMixin.as_user("wendy")
    def test_notebook_with_pages_shows_confirmation(self, client):
        response = client.post(
            "/notebooks/delete",
            {"notebook": self.wendys_notebook.pk},
        )
        assert response.status_code == HTTPStatus.OK
        assert Notebook.objects.filter(id=self.wendys_notebook.id).exists()
        self.assert_confirmation_form_present(
            response.content.decode(),
            "/notebooks/delete",
        )

    @UserMixin.as_user("wendy")
    def test_notebook_with_pages_deletes_after_confirmation(self, client):
        notebook_id = self.wendys_notebook.id
        response = client.post(
            "/notebooks/delete",
            {"notebook": self.wendys_notebook.pk, "confirm": "true"},
        )
        assert response.status_code == HTTPStatus.FOUND
        assert response.url == "/profile/wendy/"
        assert not Notebook.objects.filter(id=notebook_id).exists()

    @UserMixin.as_user("susan")
    def test_editor_cannot_delete_notebook(self, client):
        response = client.post(
            "/notebooks/delete",
            {"notebook": self.wendys_notebook.pk, "confirm": "true"},
        )
        assert response.status_code == HTTPStatus.FORBIDDEN
        assert Notebook.objects.filter(id=self.wendys_notebook.id).exists()

    @UserMixin.as_user("mary")
    def test_viewer_cannot_delete_notebook(self, client):
        response = client.post(
            "/notebooks/delete",
            {"notebook": self.wendys_notebook.pk, "confirm": "true"},
        )
        assert response.status_code == HTTPStatus.FORBIDDEN
        assert Notebook.objects.filter(id=self.wendys_notebook.id).exists()

    @UserMixin.as_user("hugh")
    def test_non_collaborator_cannot_delete_notebook(self, client):
        response = client.post(
            "/notebooks/delete",
            {"notebook": self.wendys_notebook.pk, "confirm": "true"},
        )
        assert response.status_code == HTTPStatus.FORBIDDEN
        assert Notebook.objects.filter(id=self.wendys_notebook.id).exists()

    def test_anonymous_cannot_delete_notebook(self, client):
        response = client.post(
            "/notebooks/delete",
            {"notebook": self.wendys_notebook.pk, "confirm": "true"},
        )
        assert response.status_code == HTTPStatus.UNAUTHORIZED
        assert Notebook.objects.filter(id=self.wendys_notebook.id).exists()

    @UserMixin.as_user("wendy")
    def test_cancel_delete_redirects_to_settings(self, client):
        response = client.post(
            "/notebooks/delete",
            {"notebook": self.wendys_notebook.pk},
        )
        assert response.status_code == HTTPStatus.OK
        content = response.content.decode()
        assert "/notebooks/settings/wendy/heros-legendes/" in content


@pytest.mark.django_db
class TestNotebookPageRestoreView(NotebookMixin):
    @UserMixin.as_user("wendy")
    def test_get_shows_restore_form(self, client):
        response = client.get(
            "/notebooks/restore",
            {"page": str(self.deleted_page.uuid)},
        )
        assert response.status_code == HTTPStatus.OK
        content = response.content.decode()
        assert "old-draft.md" in content
        assert 'name="filename"' in content

    @UserMixin.as_user("mary")
    def test_viewer_cannot_get_restore_form(self, client):
        response = client.get(
            "/notebooks/restore",
            {"page": str(self.deleted_page.uuid)},
        )
        assert response.status_code == HTTPStatus.FORBIDDEN

    @UserMixin.as_user("hugh")
    def test_non_collaborator_cannot_get_restore_form(self, client):
        response = client.get(
            "/notebooks/restore",
            {"page": str(self.deleted_page.uuid)},
        )
        assert response.status_code == HTTPStatus.FORBIDDEN

    def test_anonymous_cannot_get_restore_form(self, client):
        response = client.get(
            "/notebooks/restore",
            {"page": str(self.deleted_page.uuid)},
        )
        assert response.status_code == HTTPStatus.UNAUTHORIZED

    @UserMixin.as_user("wendy")
    def test_restore_non_deleted_page_redirects_to_page(self, client):
        page = self.wendys_notebook.get_page(filename="heroes/theron.md")
        response = client.get(
            "/notebooks/restore",
            {"page": str(page.uuid)},
        )
        assert response.status_code == HTTPStatus.FOUND
        assert response.url == "/notebooks/wendy/heros-legendes/heroes/theron"

    @UserMixin.as_user("wendy")
    def test_owner_can_restore_page(self, client):
        response = client.post("/notebooks/restore", {
            "page": str(self.deleted_page.uuid),
        })
        assert response.status_code == HTTPStatus.FOUND
        assert response.url == "/notebooks/wendy/heros-legendes/"
        self.deleted_page.refresh_from_db()
        assert self.deleted_page.deleted_at is None

    @UserMixin.as_user("susan")
    def test_editor_can_restore_page(self, client):
        response = client.post("/notebooks/restore", {
            "page": str(self.deleted_page.uuid),
        })
        assert response.status_code == HTTPStatus.FOUND
        self.deleted_page.refresh_from_db()
        assert self.deleted_page.deleted_at is None

    @UserMixin.as_user("mary")
    def test_viewer_cannot_restore_page(self, client):
        response = client.post("/notebooks/restore", {
            "page": str(self.deleted_page.uuid),
        })
        assert response.status_code == HTTPStatus.FORBIDDEN
        self.deleted_page.refresh_from_db()
        assert self.deleted_page.deleted_at is not None

    @UserMixin.as_user("hugh")
    def test_non_collaborator_cannot_restore_page(self, client):
        response = client.post("/notebooks/restore", {
            "page": str(self.deleted_page.uuid),
        })
        assert response.status_code == HTTPStatus.FORBIDDEN
        self.deleted_page.refresh_from_db()
        assert self.deleted_page.deleted_at is not None

    def test_anonymous_cannot_restore_page(self, client):
        response = client.post("/notebooks/restore", {
            "page": str(self.deleted_page.uuid),
        })
        assert response.status_code == HTTPStatus.UNAUTHORIZED
        self.deleted_page.refresh_from_db()
        assert self.deleted_page.deleted_at is not None

    @UserMixin.as_user("wendy")
    def test_restore_with_conflict_shows_error(self, client):
        Page.objects.create(wiki=self.wendys_notebook).update(
            filename="old-draft.md",
            mime_type="text/markdown",
            data=b"# New page at same path",
            created_by=self.wendy,
        )
        response = client.post("/notebooks/restore", {
            "page": str(self.deleted_page.uuid),
        })
        assert response.status_code == HTTPStatus.CONFLICT
        content = response.content.decode()
        assert "old-draft" in content
        assert "already exists" in content
        self.deleted_page.refresh_from_db()
        assert self.deleted_page.deleted_at is not None

    @UserMixin.as_user("wendy")
    def test_restore_with_filename_resolves_conflict(self, client):
        Page.objects.create(wiki=self.wendys_notebook).update(
            filename="old-draft.md",
            mime_type="text/markdown",
            data=b"# New page at same path",
            created_by=self.wendy,
        )
        response = client.post("/notebooks/restore", {
            "page": str(self.deleted_page.uuid),
            "filename": "restored-draft.md",
        })
        assert response.status_code == HTTPStatus.FOUND
        self.deleted_page.refresh_from_db()
        assert self.deleted_page.deleted_at is None
        assert self.deleted_page.latest_version.path == "restored-draft"

    @UserMixin.as_user("wendy")
    def test_restore_with_filename_without_conflict(self, client):
        response = client.post("/notebooks/restore", {
            "page": str(self.deleted_page.uuid),
            "filename": "renamed-draft.md",
        })
        assert response.status_code == HTTPStatus.FOUND
        self.deleted_page.refresh_from_db()
        assert self.deleted_page.deleted_at is None
        assert self.deleted_page.latest_version.path == "renamed-draft"

    @UserMixin.as_user("wendy")
    def test_restore_with_conflicting_filename_shows_error(self, client):
        Page.objects.create(wiki=self.wendys_notebook).update(
            filename="existing.md",
            mime_type="text/markdown",
            data=b"# Existing page",
            created_by=self.wendy,
        )
        response = client.post("/notebooks/restore", {
            "page": str(self.deleted_page.uuid),
            "filename": "existing.md",
        })
        assert response.status_code == HTTPStatus.CONFLICT
        content = response.content.decode()
        assert "existing" in content.lower()
        self.deleted_page.refresh_from_db()
        assert self.deleted_page.deleted_at is not None


@pytest.mark.django_db
class TestNotebookPageDeleteView(NotebookMixin):
    @UserMixin.as_user("wendy")
    def test_delete_shows_confirmation(self, client):
        page = self.wendys_notebook.get_page(path="notes")
        response = client.post("/notebooks/delete-page", {
            "notebook": self.wendys_notebook.pk,
            "page": page.pk,
        })
        assert response.status_code == HTTPStatus.OK
        content = response.content.decode()
        self.assert_confirmation_form_present(content, "/notebooks/delete-page")
        assert "notes" in content.lower()

    @UserMixin.as_user("wendy")
    def test_owner_can_delete_page(self, client):
        page = self.wendys_notebook.get_page(path="heroes/theron")
        assert page.deleted_at is None
        response = client.post("/notebooks/delete-page", {
            "notebook": self.wendys_notebook.pk,
            "page": page.pk,
            "confirm": "true",
        })
        assert response.status_code == HTTPStatus.SEE_OTHER
        assert response.url == "/notebooks/wendy/heros-legendes/heroes/"
        page.refresh_from_db()
        assert page.deleted_at is not None

    @UserMixin.as_user("susan")
    def test_editor_can_delete_page(self, client):
        page = self.wendys_notebook.get_page(path="notes")
        response = client.post("/notebooks/delete-page", {
            "notebook": self.wendys_notebook.pk,
            "page": page.pk,
            "confirm": "true",
        })
        assert response.status_code == HTTPStatus.SEE_OTHER
        page.refresh_from_db()
        assert page.deleted_at is not None

    @UserMixin.as_user("mary")
    def test_viewer_cannot_delete_page(self, client):
        page = self.wendys_notebook.get_page(path="notes")
        response = client.post("/notebooks/delete-page", {
            "notebook": self.wendys_notebook.pk,
            "page": page.pk,
            "confirm": "true",
        })
        assert response.status_code == HTTPStatus.FORBIDDEN
        page.refresh_from_db()
        assert page.deleted_at is None

    @UserMixin.as_user("hugh")
    def test_non_collaborator_cannot_delete_page(self, client):
        page = self.wendys_notebook.get_page(path="notes")
        response = client.post("/notebooks/delete-page", {
            "notebook": self.wendys_notebook.pk,
            "page": page.pk,
            "confirm": "true",
        })
        assert response.status_code == HTTPStatus.FORBIDDEN
        page.refresh_from_db()
        assert page.deleted_at is None

    def test_anonymous_cannot_delete_page(self, client):
        page = self.wendys_notebook.get_page(path="notes")
        response = client.post("/notebooks/delete-page", {
            "notebook": self.wendys_notebook.pk,
            "page": page.pk,
            "confirm": "true",
        })
        assert response.status_code == HTTPStatus.UNAUTHORIZED
        page.refresh_from_db()
        assert page.deleted_at is None


@pytest.mark.django_db
class TestNotebookUpload(NotebookMixin):
    @UserMixin.as_user("wendy")
    def test_owner_can_upload_markdown(self, client):
        data = b"# New Page\n\nSome content.\n"
        upload = BytesIO(data)
        upload.name = "new-page.md"
        response = client.post("/notebooks/upload", {
            "notebook": self.wendys_notebook.pk,
            "file": upload,
            "filename": "new-page.md",
        })
        assert response.status_code == HTTPStatus.FOUND
        page = self.wendys_notebook.get_page(path="new-page")
        assert page.latest_version.content.data == data
        assert page.latest_version.mime_type == "text/markdown"

    @UserMixin.as_user("wendy")
    def test_owner_can_upload_png(self, client):
        data = b"\x89PNG\r\n\x1a\n"
        upload = BytesIO(data)
        upload.name = "image.png"
        response = client.post("/notebooks/upload", {
            "notebook": self.wendys_notebook.pk,
            "file": upload,
            "filename": "image.png",
        })
        assert response.status_code == HTTPStatus.FOUND
        page = self.wendys_notebook.get_page(path="image.png")
        assert page.latest_version.mime_type == "image/png"

    @UserMixin.as_user("susan")
    def test_editor_can_upload(self, client):
        data = b"\x89PNG\r\n\x1a\n"
        upload = BytesIO(data)
        upload.name = "editor-upload.png"
        response = client.post("/notebooks/upload", {
            "notebook": self.wendys_notebook.pk,
            "file": upload,
            "filename": "editor-upload.png",
        })
        assert response.status_code == HTTPStatus.FOUND
        page = self.wendys_notebook.get_page(path="editor-upload.png")
        assert page.latest_version.content.data == data

    @UserMixin.as_user("mary")
    def test_viewer_cannot_upload(self, client):
        upload = BytesIO(b"# Hacked\n")
        upload.name = "hacked.md"
        response = client.post("/notebooks/upload", {
            "notebook": self.wendys_notebook.pk,
            "file": upload,
            "filename": "hacked.md",
        })
        assert response.status_code == HTTPStatus.FORBIDDEN

    @UserMixin.as_user("hugh")
    def test_non_collaborator_cannot_upload(self, client):
        upload = BytesIO(b"# Hacked\n")
        upload.name = "hacked.md"
        response = client.post("/notebooks/upload", {
            "notebook": self.wendys_notebook.pk,
            "file": upload,
            "filename": "hacked.md",
        })
        assert response.status_code == HTTPStatus.FORBIDDEN

    def test_anonymous_cannot_upload(self, client):
        upload = BytesIO(b"# Hacked\n")
        upload.name = "hacked.md"
        response = client.post("/notebooks/upload", {
            "notebook": self.wendys_notebook.pk,
            "file": upload,
            "filename": "hacked.md",
        })
        assert response.status_code == HTTPStatus.UNAUTHORIZED

    @UserMixin.as_user("susan")
    def test_upload_rejects_over_2mb(self, client):
        large_data = b"x" * (2 * 1024 * 1024 + 1)
        upload = BytesIO(large_data)
        upload.name = "large-file.bin"
        initial_page_count = Page.objects.filter(wiki=self.wendys_notebook).count()
        response = client.post("/notebooks/upload", {
            "notebook": self.wendys_notebook.pk,
            "file": upload,
            "filename": "large-file.bin",
        })
        assert response.status_code == HTTPStatus.BAD_REQUEST
        final_page_count = Page.objects.filter(wiki=self.wendys_notebook).count()
        assert final_page_count == initial_page_count

    @UserMixin.as_user("wendy")
    def test_upload_with_form_filename_uses_form_filename(self, client):
        data = b"# New Page\n\nSome content."
        upload = BytesIO(data)
        upload.name = "ignored.md"
        response = client.post("/notebooks/upload", {
            "notebook": self.wendys_notebook.pk,
            "file": upload,
            "filename": "Specified Name.md",
        })
        assert response.status_code == HTTPStatus.FOUND
        page = self.wendys_notebook.get_page(path="specified-name")
        assert page.latest_version.filename == "Specified Name.md"

    @UserMixin.as_user("wendy")
    def test_upload_without_form_filename_uses_uploaded_filename(self, client):
        data = b"# New Page\n\nSome content."
        upload = BytesIO(data)
        upload.name = "Uploaded File.md"
        response = client.post("/notebooks/upload", {
            "notebook": self.wendys_notebook.pk,
            "file": upload,
        })
        assert response.status_code == HTTPStatus.FOUND
        page = self.wendys_notebook.get_page(path="uploaded-file")
        assert page.latest_version.filename == "Uploaded File.md"

    @UserMixin.as_user("wendy")
    def test_upload_existing_filename_creates_new_version(self, client):
        page = self.wendys_notebook.get_page(path="notes")
        initial_version_count = page.version_set.count()
        upload = BytesIO(b"# Updated Notes\n\nNew content.")
        upload.name = "notes.md"
        response = client.post("/notebooks/upload", {
            "notebook": self.wendys_notebook.pk,
            "file": upload,
            "filename": "notes.md",
        })
        assert response.status_code == HTTPStatus.FOUND
        page.refresh_from_db()
        assert page.version_set.count() == initial_version_count + 1
        assert page.latest_version.content.data == b"# Updated Notes\n\nNew content.\n"

    @UserMixin.as_user("wendy")
    def test_upload_identical_content_does_not_create_version(self, client):
        page = self.wendys_notebook.get_page(path="notes")
        initial_version_count = page.version_set.count()
        existing_content = page.latest_version.content.data
        upload = BytesIO(existing_content)
        upload.name = "notes.md"
        response = client.post("/notebooks/upload", {
            "notebook": self.wendys_notebook.pk,
            "file": upload,
            "filename": "notes.md",
        })
        assert response.status_code == HTTPStatus.FOUND
        page.refresh_from_db()
        assert page.version_set.count() == initial_version_count


@pytest.mark.django_db
class TestNotebookCollaboratorsView(NotebookMixin):
    @UserMixin.as_user("wendy")
    def test_add_collaborator_shows_confirmation(self, client):
        response = client.post("/notebooks/collaborators", {
            "notebook": self.wendys_notebook.pk,
            "username": "hugh",
            "role": "viewer",
        })
        assert response.status_code == HTTPStatus.OK
        assert not NotebookPermission.objects.filter(
            notebook=self.wendys_notebook,
            user=self.hugh,
        ).exists()
        content = response.content.decode()
        self.assert_notebook_header_present(content, self.wendys_notebook)
        self.assert_confirmation_form_present(content, "/notebooks/collaborators")

    @UserMixin.as_user("wendy")
    def test_add_collaborator_confirmed(self, client):
        response = client.post("/notebooks/collaborators", {
            "notebook": self.wendys_notebook.pk,
            "username": "hugh",
            "role": "viewer",
            "confirm": "true",
        })
        assert response.status_code == HTTPStatus.FOUND
        assert response.url == self.wendys_notebook.get_absolute_url()
        permission = NotebookPermission.objects.get(
            notebook=self.wendys_notebook,
            user=self.hugh,
        )
        assert permission.role == NotebookPermission.Role.VIEWER

    @UserMixin.as_user("wendy")
    def test_remove_collaborator_shows_confirmation(self, client):
        response = client.post("/notebooks/collaborators", {
            "notebook": self.wendys_notebook.pk,
            "remove": str(self.susan.pk),
        })
        assert response.status_code == HTTPStatus.OK
        content = response.content.decode()
        self.assert_notebook_header_present(content, self.wendys_notebook)
        self.assert_confirmation_form_present(content, "/notebooks/collaborators")

    @UserMixin.as_user("wendy")
    def test_remove_collaborator_confirmed(self, client):
        response = client.post("/notebooks/collaborators", {
            "notebook": self.wendys_notebook.pk,
            "remove": str(self.susan.pk),
            "confirm": "true",
        })
        assert response.status_code == HTTPStatus.FOUND
        assert response.url == self.wendys_notebook.get_absolute_url()
        assert not NotebookPermission.objects.filter(
            notebook=self.wendys_notebook,
            user=self.susan,
        ).exists()

    @UserMixin.as_user("wendy")
    def test_change_collaborator_role_shows_confirmation(self, client):
        response = client.post("/notebooks/collaborators", {
            "notebook": self.wendys_notebook.pk,
            "change_role": str(self.susan.pk),
            "role": "viewer",
        })
        assert response.status_code == HTTPStatus.OK
        content = response.content.decode()
        self.assert_notebook_header_present(content, self.wendys_notebook)
        self.assert_confirmation_form_present(content, "/notebooks/collaborators")

    @UserMixin.as_user("wendy")
    def test_change_collaborator_role_confirmed(self, client):
        response = client.post("/notebooks/collaborators", {
            "notebook": self.wendys_notebook.pk,
            "change_role": str(self.susan.pk),
            "role": "viewer",
            "confirm": "true",
        })
        assert response.status_code == HTTPStatus.FOUND
        assert response.url == self.wendys_notebook.get_absolute_url()
        self.susans_permission.refresh_from_db()
        assert self.susans_permission.role == NotebookPermission.Role.VIEWER

    @UserMixin.as_user("susan")
    def test_editor_cannot_add_collaborator(self, client):
        response = client.post("/notebooks/collaborators", {
            "notebook": self.wendys_notebook.pk,
            "username": "hugh",
            "role": "viewer",
            "confirm": "true",
        })
        assert response.status_code == HTTPStatus.FORBIDDEN
        assert not NotebookPermission.objects.filter(
            notebook=self.wendys_notebook,
            user=self.hugh,
        ).exists()

    @UserMixin.as_user("susan")
    def test_editor_cannot_remove_collaborator(self, client):
        response = client.post("/notebooks/collaborators", {
            "notebook": self.wendys_notebook.pk,
            "remove": str(self.mary.pk),
            "confirm": "true",
        })
        assert response.status_code == HTTPStatus.FORBIDDEN
        assert NotebookPermission.objects.filter(
            notebook=self.wendys_notebook,
            user=self.mary,
        ).exists()

    @UserMixin.as_user("susan")
    def test_editor_cannot_change_collaborator_role(self, client):
        response = client.post("/notebooks/collaborators", {
            "notebook": self.wendys_notebook.pk,
            "change_role": str(self.mary.pk),
            "role": "editor",
            "confirm": "true",
        })
        assert response.status_code == HTTPStatus.FORBIDDEN
        permission = NotebookPermission.objects.get(
            notebook=self.wendys_notebook,
            user=self.mary,
        )
        assert permission.role == NotebookPermission.Role.VIEWER

    @UserMixin.as_user("mary")
    def test_viewer_cannot_add_collaborator(self, client):
        response = client.post("/notebooks/collaborators", {
            "notebook": self.wendys_notebook.pk,
            "username": "hugh",
            "role": "viewer",
            "confirm": "true",
        })
        assert response.status_code == HTTPStatus.FORBIDDEN
        assert not NotebookPermission.objects.filter(
            notebook=self.wendys_notebook,
            user=self.hugh,
        ).exists()

    @UserMixin.as_user("mary")
    def test_viewer_cannot_remove_collaborator(self, client):
        response = client.post("/notebooks/collaborators", {
            "notebook": self.wendys_notebook.pk,
            "remove": str(self.susan.pk),
            "confirm": "true",
        })
        assert response.status_code == HTTPStatus.FORBIDDEN
        assert NotebookPermission.objects.filter(
            notebook=self.wendys_notebook,
            user=self.susan,
        ).exists()

    @UserMixin.as_user("mary")
    def test_viewer_cannot_change_collaborator_role(self, client):
        response = client.post("/notebooks/collaborators", {
            "notebook": self.wendys_notebook.pk,
            "change_role": str(self.susan.pk),
            "role": "viewer",
            "confirm": "true",
        })
        assert response.status_code == HTTPStatus.FORBIDDEN
        self.susans_permission.refresh_from_db()
        assert self.susans_permission.role == NotebookPermission.Role.EDITOR

    @UserMixin.as_user("hugh")
    def test_non_collaborator_cannot_add_collaborator(self, client):
        response = client.post("/notebooks/collaborators", {
            "notebook": self.wendys_notebook.pk,
            "username": "mary",
            "role": "viewer",
            "confirm": "true",
        })
        assert response.status_code == HTTPStatus.FORBIDDEN

    @UserMixin.as_user("hugh")
    def test_non_collaborator_cannot_remove_collaborator(self, client):
        response = client.post("/notebooks/collaborators", {
            "notebook": self.wendys_notebook.pk,
            "remove": str(self.susan.pk),
            "confirm": "true",
        })
        assert response.status_code == HTTPStatus.FORBIDDEN
        assert NotebookPermission.objects.filter(
            notebook=self.wendys_notebook,
            user=self.susan,
        ).exists()

    @UserMixin.as_user("hugh")
    def test_non_collaborator_cannot_change_collaborator_role(self, client):
        response = client.post("/notebooks/collaborators", {
            "notebook": self.wendys_notebook.pk,
            "change_role": str(self.susan.pk),
            "role": "viewer",
            "confirm": "true",
        })
        assert response.status_code == HTTPStatus.FORBIDDEN
        self.susans_permission.refresh_from_db()
        assert self.susans_permission.role == NotebookPermission.Role.EDITOR

    def test_anonymous_cannot_add_collaborator(self, client):
        response = client.post("/notebooks/collaborators", {
            "notebook": self.wendys_notebook.pk,
            "username": "hugh",
            "role": "editor",
            "confirm": "true",
        })
        assert response.status_code == HTTPStatus.UNAUTHORIZED
        assert not NotebookPermission.objects.filter(
            notebook=self.wendys_notebook,
            user=self.hugh,
        ).exists()

    def test_anonymous_cannot_remove_collaborator(self, client):
        response = client.post("/notebooks/collaborators", {
            "notebook": self.wendys_notebook.pk,
            "remove": str(self.susan.pk),
            "confirm": "true",
        })
        assert response.status_code == HTTPStatus.UNAUTHORIZED
        assert NotebookPermission.objects.filter(
            notebook=self.wendys_notebook,
            user=self.susan,
        ).exists()

    def test_anonymous_cannot_change_collaborator_role(self, client):
        response = client.post("/notebooks/collaborators", {
            "notebook": self.wendys_notebook.pk,
            "change_role": str(self.susan.pk),
            "role": "viewer",
            "confirm": "true",
        })
        assert response.status_code == HTTPStatus.UNAUTHORIZED
        self.susans_permission.refresh_from_db()
        assert self.susans_permission.role == NotebookPermission.Role.EDITOR

    @UserMixin.as_user("wendy")
    def test_empty_username_redisplays_settings_with_error(self, client):
        response = client.post("/notebooks/collaborators", {
            "notebook": self.wendys_notebook.pk,
            "username": "",
            "role": "viewer",
        })
        assert response.status_code == HTTPStatus.OK
        content = response.content.decode()
        assert 'action="/notebooks/rename"' in content
        assert "No username provided" in content

    @UserMixin.as_user("wendy")
    def test_unknown_username_redisplays_settings_with_error(self, client):
        response = client.post("/notebooks/collaborators", {
            "notebook": self.wendys_notebook.pk,
            "username": "nonexistent",
            "role": "viewer",
        })
        assert response.status_code == HTTPStatus.OK
        content = response.content.decode()
        assert 'action="/notebooks/rename"' in content
        assert "User &#x27;nonexistent&#x27; not found" in content


@pytest.mark.django_db
class TestNotebookVisibilityView(NotebookMixin):
    @UserMixin.as_user("wendy")
    def test_visibility_change_shows_confirmation(self, client):
        response = client.post(
            "/notebooks/visibility",
            {"notebook": self.wendys_notebook.pk, "visibility": "public"},
        )
        assert response.status_code == HTTPStatus.OK
        self.wendys_notebook.refresh_from_db()
        assert self.wendys_notebook.visibility == Notebook.Visibility.PRIVATE
        content = response.content.decode()
        self.assert_notebook_header_present(content, self.wendys_notebook)
        self.assert_confirmation_form_present(content, "/notebooks/visibility")

    @UserMixin.as_user("wendy")
    def test_visibility_change_confirmed(self, client):
        response = client.post("/notebooks/visibility", {
            "notebook": self.wendys_notebook.pk,
            "visibility": "public",
            "confirm": "true",
        })
        assert response.status_code == HTTPStatus.FOUND
        assert response.url == "/notebooks/wendy/heros-legendes/"
        self.wendys_notebook.refresh_from_db()
        assert self.wendys_notebook.visibility == Notebook.Visibility.PUBLIC

    @UserMixin.as_user("susan")
    def test_editor_cannot_change_visibility(self, client):
        response = client.post("/notebooks/visibility", {
            "notebook": self.wendys_notebook.pk,
            "visibility": "public",
            "confirm": "true",
        })
        assert response.status_code == HTTPStatus.FORBIDDEN
        self.wendys_notebook.refresh_from_db()
        assert self.wendys_notebook.visibility == Notebook.Visibility.PRIVATE

    @UserMixin.as_user("mary")
    def test_viewer_cannot_change_visibility(self, client):
        response = client.post("/notebooks/visibility", {
            "notebook": self.wendys_notebook.pk,
            "visibility": "public",
            "confirm": "true",
        })
        assert response.status_code == HTTPStatus.FORBIDDEN
        self.wendys_notebook.refresh_from_db()
        assert self.wendys_notebook.visibility == Notebook.Visibility.PRIVATE

    @UserMixin.as_user("hugh")
    def test_non_collaborator_cannot_change_visibility(self, client):
        response = client.post("/notebooks/visibility", {
            "notebook": self.wendys_notebook.pk,
            "visibility": "public",
            "confirm": "true",
        })
        assert response.status_code == HTTPStatus.FORBIDDEN
        self.wendys_notebook.refresh_from_db()
        assert self.wendys_notebook.visibility == Notebook.Visibility.PRIVATE

    def test_anonymous_cannot_change_visibility(self, client):
        response = client.post("/notebooks/visibility", {
            "notebook": self.wendys_notebook.pk,
            "visibility": "public",
            "confirm": "true",
        })
        assert response.status_code == HTTPStatus.UNAUTHORIZED
        self.wendys_notebook.refresh_from_db()
        assert self.wendys_notebook.visibility == Notebook.Visibility.PRIVATE

    @UserMixin.as_user("wendy")
    def test_cancel_visibility_change_redirects_to_settings(self, client):
        response = client.post("/notebooks/visibility", {
            "notebook": self.wendys_notebook.pk,
            "visibility": "public",
        })
        assert response.status_code == HTTPStatus.OK
        content = response.content.decode()
        assert "/notebooks/settings/wendy/heros-legendes/" in content


@pytest.mark.django_db
class TestNotebookRenameView(NotebookMixin):
    @UserMixin.as_user("wendy")
    def test_owner_can_rename_notebook(self, client):
        response = client.post(
            "/notebooks/rename",
            {
                "notebook": self.wendys_notebook.pk,
                "name": "Session Notes",
                "confirm": "true",
            },
        )
        assert response.status_code == HTTPStatus.FOUND
        assert response.url == "/notebooks/wendy/session-notes/"
        self.wendys_notebook.refresh_from_db()
        assert self.wendys_notebook.name == "Session Notes"
        assert self.wendys_notebook.slug == "session-notes"

    @UserMixin.as_user("susan")
    def test_editor_cannot_rename_notebook(self, client):
        response = client.post(
            "/notebooks/rename",
            {"notebook": self.wendys_notebook.pk, "name": "Hacked"},
        )
        assert response.status_code == HTTPStatus.FORBIDDEN
        self.wendys_notebook.refresh_from_db()
        assert self.wendys_notebook.name == "Héros & Légendes"

    @UserMixin.as_user("mary")
    def test_viewer_cannot_rename_notebook(self, client):
        response = client.post(
            "/notebooks/rename",
            {"notebook": self.wendys_notebook.pk, "name": "Hacked"},
        )
        assert response.status_code == HTTPStatus.FORBIDDEN
        self.wendys_notebook.refresh_from_db()
        assert self.wendys_notebook.name == "Héros & Légendes"

    @UserMixin.as_user("hugh")
    def test_non_collaborator_cannot_rename_notebook(self, client):
        response = client.post(
            "/notebooks/rename",
            {"notebook": self.wendys_notebook.pk, "name": "Hacked"},
        )
        assert response.status_code == HTTPStatus.FORBIDDEN
        self.wendys_notebook.refresh_from_db()
        assert self.wendys_notebook.name == "Héros & Légendes"

    def test_anonymous_cannot_rename_notebook(self, client):
        response = client.post(
            "/notebooks/rename",
            {"notebook": self.wendys_notebook.pk, "name": "Hacked"},
        )
        assert response.status_code == HTTPStatus.UNAUTHORIZED
        self.wendys_notebook.refresh_from_db()
        assert self.wendys_notebook.name == "Héros & Légendes"

    @UserMixin.as_user("wendy")
    def test_rename_shows_confirmation(self, client):
        response = client.post(
            "/notebooks/rename",
            {"notebook": self.wendys_notebook.pk, "name": "Session Notes"},
        )
        assert response.status_code == HTTPStatus.OK
        self.wendys_notebook.refresh_from_db()
        assert self.wendys_notebook.name == "Héros & Légendes"
        self.assert_confirmation_form_present(
            response.content.decode(),
            "/notebooks/rename",
        )

    @UserMixin.as_user("wendy")
    def test_cancel_rename_redirects_to_settings(self, client):
        response = client.post(
            "/notebooks/rename",
            {"notebook": self.wendys_notebook.pk, "name": "Session Notes"},
        )
        assert response.status_code == HTTPStatus.OK
        content = response.content.decode()
        assert "/notebooks/settings/wendy/heros-legendes/" in content

    @UserMixin.as_user("wendy")
    def test_unchanged_name_redirects_to_settings(self, client):
        response = client.post(
            "/notebooks/rename",
            {"notebook": self.wendys_notebook.pk, "name": "Héros & Légendes"},
        )
        assert response.status_code == HTTPStatus.FOUND
        assert response.url == "/notebooks/settings/wendy/heros-legendes/"
