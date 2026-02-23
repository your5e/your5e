from http import HTTPStatus
from io import BytesIO

import pytest

from notebooks.models import Notebook, NotebookPermission
from users.tests import UserMixin
from wikis.models import Page

PNG_BYTES = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01"


class NotebookMixin(UserMixin):
    # Permission matrix:
    #   wendy's notebook (private): susan=editor, mary=viewer
    #   susan's notebook (public):  mary=editor
    #   mary's notebook (site):     wendy=editor
    #   hugh has no permissions

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
        self.marys_notebook = Notebook.objects.create(
            name="World Lore",
            owner=self.mary,
            visibility=Notebook.Visibility.SITE,
        )
        self.susans_permission = NotebookPermission.objects.create(
            notebook=self.wendys_notebook,
            user=self.susan,
            role=NotebookPermission.Role.EDITOR,
        )
        NotebookPermission.objects.create(
            notebook=self.wendys_notebook,
            user=self.mary,
            role=NotebookPermission.Role.VIEWER,
        )
        NotebookPermission.objects.create(
            notebook=self.susans_notebook,
            user=self.mary,
            role=NotebookPermission.Role.EDITOR,
        )
        NotebookPermission.objects.create(
            notebook=self.marys_notebook,
            user=self.wendy,
            role=NotebookPermission.Role.EDITOR,
        )

        index_page = Page.objects.create(wiki=self.wendys_notebook)
        index_page.update(
            filename="index.md",
            mime_type="text/markdown",
            data=b"# Welcome\n\nThis is the index page.",
            created_by=self.wendy,
        )
        heroes_page = Page.objects.create(wiki=self.wendys_notebook)
        heroes_page.update(
            filename="heroes/theron.md",
            mime_type="text/markdown",
            data=b"# Theron\n\nA ranger.",
            created_by=self.wendy,
        )
        notes_page = Page.objects.create(wiki=self.wendys_notebook)
        notes_page.update(
            filename="notes.md",
            mime_type="text/markdown",
            data=b"# Notes\n\nSome notes.",
            created_by=self.wendy,
        )
        deleted_page = Page.objects.create(wiki=self.wendys_notebook)
        deleted_page.update(
            filename="old-draft.md",
            mime_type="text/markdown",
            data=b"# Old Draft\n\nDeleted content.",
            created_by=self.wendy,
        )
        deleted_page.soft_delete()
        self.deleted_page = deleted_page

        image_page = Page.objects.create(wiki=self.wendys_notebook)
        image_page.update(
            filename="heroes/shield.png",
            mime_type="image/png",
            data=PNG_BYTES,
            created_by=self.wendy,
        )

        page_with_wikilinks = Page.objects.create(wiki=self.wendys_notebook)
        page_with_wikilinks.update(
            filename="links.md",
            mime_type="text/markdown",
            data=b"# Links\n\n[[Theron]]\n[Notes](./notes)",
            created_by=self.wendy,
        )

        versioned_page = Page.objects.create(wiki=self.wendys_notebook)
        versioned_page.update(
            filename="Session One.md",
            mime_type="text/markdown",
            data=b"# Session One\n\nFirst draft.",
            created_by=self.wendy,
        )
        versioned_page.update(
            filename="Session One.md",
            mime_type="text/markdown",
            data=b"# Session One\n\nSecond draft with more detail.",
            created_by=self.susan,
        )
        versioned_page.update(
            filename="Session One.md",
            mime_type="text/markdown",
            data=b"# Session One\n\nFinal version.",
            created_by=self.wendy,
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
    @UserMixin.as_user("wendy")
    def test_own_profile_lists_notebooks(self, client):
        response = client.get("/profile/wendy/")
        content = response.content.decode()
        assert "Héros &amp; Légendes" in content

    @UserMixin.as_user("wendy")
    def test_own_profile_shows_create_notebook_form(self, client):
        response = client.get("/profile/wendy/")
        content = response.content.decode()
        assert 'name="notebook_name"' in content

    @UserMixin.as_user("wendy")
    def test_create_notebook(self, client):
        response = client.post(
            "/profile/wendy/notebooks",
            {"notebook_name": "New Notebook"},
        )
        assert response.status_code == HTTPStatus.FOUND
        notebook = Notebook.objects.get(name="New Notebook")
        assert notebook.owner == self.wendy
        assert notebook.slug == "new-notebook"

    @UserMixin.as_user("wendy")
    def test_create_notebook_redirects_to_profile(self, client):
        response = client.post(
            "/profile/wendy/notebooks",
            {"notebook_name": "New Notebook"},
        )
        assert response.url == "/profile/wendy/"

    @UserMixin.as_user("wendy")
    def test_other_profile_does_not_show_notebooks(self, client):
        response = client.get("/profile/susan/")
        content = response.content.decode()
        assert "Campaign Notes" not in content

    @UserMixin.as_user("wendy")
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
    @UserMixin.as_user("wendy")
    def test_owner_can_view_notebook(self, client):
        response = client.get("/notebooks/wendy/heros-legendes/")
        assert response.status_code == HTTPStatus.OK
        content = response.content.decode()
        assert "Héros &amp; Légendes" in content

    @UserMixin.as_user("wendy")
    def test_owner_sees_rename_form(self, client):
        response = client.get("/notebooks/wendy/heros-legendes/")
        content = response.content.decode()
        assert 'name="name"' in content

    @UserMixin.as_user("wendy")
    def test_owner_sees_visibility_controls(self, client):
        response = client.get("/notebooks/wendy/heros-legendes/")
        content = response.content.decode()
        assert "visibility" in content.lower()

    @UserMixin.as_user("wendy")
    def test_owner_sees_collaborator_section(self, client):
        response = client.get("/notebooks/wendy/heros-legendes/")
        content = response.content.decode()
        assert "collaborator" in content.lower()

    @UserMixin.as_user("wendy")
    def test_non_owner_does_not_see_rename_form(self, client):
        self.susans_notebook.visibility = Notebook.Visibility.SITE
        self.susans_notebook.save()
        response = client.get("/notebooks/susan/campaign-notes/")
        content = response.content.decode()
        assert 'name="name"' not in content

    @UserMixin.as_user("wendy")
    def test_non_owner_does_not_see_collaborator_section(self, client):
        self.susans_notebook.visibility = Notebook.Visibility.SITE
        self.susans_notebook.save()
        response = client.get("/notebooks/susan/campaign-notes/")
        content = response.content.decode()
        assert "collaborator" not in content.lower()


@pytest.mark.django_db
class TestNotebookRenameView(NotebookMixin):
    @UserMixin.as_user("wendy")
    def test_owner_can_rename_notebook(self, client):
        response = client.post(
            "/notebooks/rename",
            {"notebook": self.wendys_notebook.pk, "name": "Session Notes"},
        )
        assert response.status_code == HTTPStatus.FOUND
        self.wendys_notebook.refresh_from_db()
        assert self.wendys_notebook.name == "Session Notes"
        assert self.wendys_notebook.slug == "session-notes"

    @UserMixin.as_user("wendy")
    def test_rename_redirects_to_new_slug(self, client):
        response = client.post(
            "/notebooks/rename",
            {"notebook": self.wendys_notebook.pk, "name": "Session Notes"},
        )
        assert response.url == "/notebooks/wendy/session-notes/"

    @UserMixin.as_user("wendy")
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
    @UserMixin.as_user("wendy")
    def test_visibility_change_shows_confirmation(self, client):
        response = client.post(
            "/notebooks/visibility",
            {"notebook": self.wendys_notebook.pk, "visibility": "public"},
        )
        assert response.status_code == HTTPStatus.OK
        content = response.content.decode()
        assert "confirm" in content.lower()

    @UserMixin.as_user("wendy")
    def test_visibility_change_confirmed(self, client):
        response = client.post("/notebooks/visibility", {
            "notebook": self.wendys_notebook.pk,
            "visibility": "public",
            "confirmed": "true",
        })
        assert response.status_code == HTTPStatus.FOUND
        self.wendys_notebook.refresh_from_db()
        assert self.wendys_notebook.visibility == Notebook.Visibility.PUBLIC

    @UserMixin.as_user("wendy")
    def test_visibility_change_redirects_to_notebook(self, client):
        response = client.post("/notebooks/visibility", {
            "notebook": self.wendys_notebook.pk,
            "visibility": "public",
            "confirmed": "true",
        })
        assert response.url == "/notebooks/wendy/heros-legendes/"

    @UserMixin.as_user("wendy")
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
    @UserMixin.as_user("wendy")
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

    @UserMixin.as_user("wendy")
    def test_add_collaborator_confirmed(self, client):
        response = client.post("/notebooks/collaborators", {
            "notebook": self.wendys_notebook.pk,
            "username": "hugh",
            "role": "viewer",
            "confirmed": "true",
        })
        assert response.status_code == HTTPStatus.FOUND
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
        assert "confirm" in content.lower()

    @UserMixin.as_user("wendy")
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

    @UserMixin.as_user("wendy")
    def test_change_collaborator_role_shows_confirmation(self, client):
        response = client.post("/notebooks/collaborators", {
            "notebook": self.wendys_notebook.pk,
            "change_role": str(self.susan.pk),
            "role": "viewer",
        })
        assert response.status_code == HTTPStatus.OK
        content = response.content.decode()
        assert "confirm" in content.lower()

    @UserMixin.as_user("wendy")
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

    @UserMixin.as_user("wendy")
    def test_non_owner_cannot_add_collaborator(self, client):
        response = client.post("/notebooks/collaborators", {
            "notebook": self.marys_notebook.pk,
            "username": "hugh",
            "role": "editor",
            "confirmed": "true",
        })
        assert response.status_code == HTTPStatus.FORBIDDEN
        assert not NotebookPermission.objects.filter(
            notebook=self.marys_notebook,
            user=self.hugh,
        ).exists()

    def test_anonymous_cannot_add_collaborator(self, client):
        response = client.post("/notebooks/collaborators", {
            "notebook": self.wendys_notebook.pk,
            "username": "hugh",
            "role": "editor",
            "confirmed": "true",
        })
        assert response.status_code == HTTPStatus.UNAUTHORIZED
        assert not NotebookPermission.objects.filter(
            notebook=self.wendys_notebook,
            user=self.hugh,
        ).exists()


@pytest.mark.django_db
class TestNotebookIndexPage(NotebookMixin):
    def assert_shows_content(self, content):
        assert 'href="heroes/"' in content
        assert 'href="/notebooks/wendy/heros-legendes/notes"' in content
        assert "This is the index page" in content

    def assert_shows_edit_features(self, content):
        assert 'href="/notebooks/wendy/heros-legendes/notes?edit"' in content
        assert 'href="old-draft.md/restore"' in content
        assert 'type="file"' in content
        assert 'href="index?edit"' in content

    @UserMixin.as_user("wendy")
    def test_owner_sees_full_index(self, client):
        response = client.get("/notebooks/wendy/heros-legendes/")
        content = response.content.decode()
        assert response.status_code == HTTPStatus.OK
        self.assert_shows_content(content)
        self.assert_shows_edit_features(content)

    @UserMixin.as_user("susan")
    def test_editor_sees_full_index(self, client):
        response = client.get("/notebooks/wendy/heros-legendes/")
        content = response.content.decode()
        assert response.status_code == HTTPStatus.OK
        self.assert_shows_content(content)
        self.assert_shows_edit_features(content)

    @UserMixin.as_user("susan")
    def test_viewer_sees_content_only(self, client):
        self.susans_permission.role = NotebookPermission.Role.VIEWER
        self.susans_permission.save()
        response = client.get("/notebooks/wendy/heros-legendes/")
        content = response.content.decode()
        assert response.status_code == HTTPStatus.OK
        self.assert_shows_content(content)
        assert 'href="notes/edit"' not in content
        assert "old-draft.md" not in content
        assert 'type="file"' not in content
        assert 'href="index.md/edit"' not in content

    @UserMixin.as_user("hugh")
    def test_non_collaborator_cannot_view_private(self, client):
        response = client.get("/notebooks/wendy/heros-legendes/")
        assert response.status_code == HTTPStatus.FORBIDDEN

    def test_anonymous_cannot_view_private(self, client):
        response = client.get("/notebooks/wendy/heros-legendes/")
        assert response.status_code == HTTPStatus.UNAUTHORIZED

    @UserMixin.as_user("wendy")
    def test_index_not_listed_as_page(self, client):
        response = client.get("/notebooks/wendy/heros-legendes/")
        content = response.content.decode()
        assert "This is the index page" in content
        assert ">index<" not in content.lower()

    @UserMixin.as_user("wendy")
    def test_index_page_shows_version_dropdown(self, client):
        response = client.get("/notebooks/wendy/heros-legendes/")
        content = response.content.decode()
        assert "This is the index page" in content
        assert '<option value="1"' in content

    @UserMixin.as_user("wendy")
    def test_empty_folder_returns_404_with_creation_form(self, client):
        response = client.get("/notebooks/wendy/heros-legendes/monsters/")
        assert response.status_code == HTTPStatus.NOT_FOUND
        content = response.content.decode()
        assert 'name="filename" value="Monsters/Index"' in content
        assert 'action="/notebooks/wendy/heros-legendes/monsters/index"' in content

    @UserMixin.as_user("wendy")
    def test_folder_with_content_but_no_index_shows_create(self, client):
        response = client.get("/notebooks/wendy/heros-legendes/heroes/")
        assert response.status_code == HTTPStatus.OK
        content = response.content.decode()
        assert "Create index" in content
        assert "Edit index" not in content

    @UserMixin.as_user("wendy")
    def test_creating_index_redirects_to_folder(self, client):
        response = client.post("/notebooks/wendy/heros-legendes/monsters/index", {
            "filename": "monsters/index",
            "content": "# Monsters",
        })
        assert response.status_code == HTTPStatus.FOUND
        assert response.url == "/notebooks/wendy/heros-legendes/monsters/"

    @UserMixin.as_user("wendy")
    def test_creating_page_with_no_content_does_not_create(self, client):
        response = client.post("/notebooks/wendy/heros-legendes/monsters/index", {
            "filename": "monsters/index",
            "content": "",
        })
        assert response.status_code == HTTPStatus.FOUND
        assert response.url == "/notebooks/wendy/heros-legendes/monsters/"
        with pytest.raises(Page.DoesNotExist):
            self.wendys_notebook.get_page(path="monsters/index")


@pytest.mark.django_db
class TestNotebookUpload(NotebookMixin):
    @UserMixin.as_user("wendy")
    def test_upload_creates_page_with_markdown_mime(self, client):
        data = b"# New Page\n\nSome content."
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
    def test_upload_creates_page_with_png_mime(self, client):
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

    def test_anonymous_cannot_upload(self, client):
        upload = BytesIO(b"# Hacked\n")
        upload.name = "hacked.md"
        response = client.post("/notebooks/upload", {
            "notebook": self.wendys_notebook.pk,
            "file": upload,
            "filename": "hacked.md",
        })
        assert response.status_code == HTTPStatus.UNAUTHORIZED


@pytest.mark.django_db
class TestNotebookPageView(NotebookMixin):
    @UserMixin.as_user("wendy")
    def test_view_markdown_page_without_extension(self, client):
        response = client.get("/notebooks/wendy/heros-legendes/notes")
        assert response.status_code == HTTPStatus.OK
        content = response.content.decode()
        assert "<h1>Notes</h1>" in content

    @UserMixin.as_user("wendy")
    def test_view_nested_markdown_page(self, client):
        response = client.get("/notebooks/wendy/heros-legendes/heroes/theron")
        assert response.status_code == HTTPStatus.OK
        content = response.content.decode()
        assert "<h1>Theron</h1>" in content

    @UserMixin.as_user("wendy")
    def test_view_markdown_with_extension_redirects(self, client):
        response = client.get("/notebooks/wendy/heros-legendes/heroes/theron.md")
        assert response.status_code == HTTPStatus.MOVED_PERMANENTLY
        assert response.url == "/notebooks/wendy/heros-legendes/heroes/theron"

    @UserMixin.as_user("wendy")
    def test_view_non_markdown_file_returns_raw(self, client):
        response = client.get("/notebooks/wendy/heros-legendes/heroes/shield.png")
        assert response.status_code == HTTPStatus.OK
        assert response["Content-Type"] == "image/png"
        assert response.content == PNG_BYTES

    @UserMixin.as_user("wendy")
    def test_view_nonexistent_page_returns_404(self, client):
        response = client.get("/notebooks/wendy/heros-legendes/nonexistent")
        assert response.status_code == HTTPStatus.NOT_FOUND

    @UserMixin.as_user("wendy")
    def test_view_page_renders_links(self, client):
        response = client.get("/notebooks/wendy/heros-legendes/links")
        assert response.status_code == HTTPStatus.OK
        content = response.content.decode()
        assert (
            '<a href="/notebooks/wendy/heros-legendes/heroes/theron">Theron</a>'
            in content
        )
        assert (
            '<a href="/notebooks/wendy/heros-legendes/notes">Notes</a>'
            in content
        )

    @UserMixin.as_user("wendy")
    def test_view_page_shows_version_info(self, client):
        response = client.get("/notebooks/wendy/heros-legendes/session-one")
        content = response.content.decode()
        page = self.wendys_notebook.get_page(path="session-one")
        versions = page.history()
        v1_date = versions[0].created_at.strftime("%-d %b %Y")
        v2_date = versions[1].created_at.strftime("%-d %b %Y")
        v3_date = versions[2].created_at.strftime("%-d %b %Y")
        assert f"<option value=\"1\">v1 by wendy on {v1_date}</option>" in content
        assert f"<option value=\"2\">v2 by susan on {v2_date}</option>" in content
        assert (
            f"<option value=\"3\" selected>v3 by wendy on {v3_date}</option>"
            in content
        )
        assert "Version 3 of" not in content

    @UserMixin.as_user("wendy")
    def test_view_old_version(self, client):
        response = client.get("/notebooks/wendy/heros-legendes/session-one?version=1")
        content = response.content.decode()
        assert "First draft" in content
        assert "Version 1 of" in content

    @UserMixin.as_user("wendy")
    def test_view_invalid_version_returns_404(self, client):
        response = client.get("/notebooks/wendy/heros-legendes/session-one?version=99")
        assert response.status_code == HTTPStatus.NOT_FOUND

    @UserMixin.as_user("wendy")
    def test_edit_markdown_shows_form_with_content(self, client):
        response = client.get("/notebooks/wendy/heros-legendes/notes?edit")
        assert response.status_code == HTTPStatus.OK
        content = response.content.decode()
        assert "<form" in content
        assert "# Notes" in content
        assert "<textarea" in content
        assert 'type="file"' in content
        assert 'type="submit"' in content

    @UserMixin.as_user("wendy")
    def test_edit_binary_shows_form(self, client):
        response = client.get("/notebooks/wendy/heros-legendes/heroes/shield.png?edit")
        assert response.status_code == HTTPStatus.OK
        content = response.content.decode()
        assert "<form" in content
        assert "<textarea" in content
        assert 'type="file"' in content
        assert 'type="submit"' in content

    @UserMixin.as_user("susan")
    def test_editor_can_see_edit_form(self, client):
        response = client.get("/notebooks/wendy/heros-legendes/notes?edit")
        assert response.status_code == HTTPStatus.OK
        assert "<form" in response.content.decode()

    @UserMixin.as_user("mary")
    def test_viewer_cannot_see_edit_form(self, client):
        response = client.get("/notebooks/wendy/heros-legendes/notes?edit")
        assert response.status_code == HTTPStatus.FORBIDDEN

    def test_anonymous_cannot_see_edit_form(self, client):
        self.wendys_notebook.visibility = Notebook.Visibility.PUBLIC
        self.wendys_notebook.save()
        response = client.get("/notebooks/wendy/heros-legendes/notes?edit")
        assert response.status_code == HTTPStatus.UNAUTHORIZED

    @UserMixin.as_user("wendy")
    def test_owner_sees_edit_link(self, client):
        response = client.get("/notebooks/wendy/heros-legendes/notes")
        assert '?edit"' in response.content.decode()

    @UserMixin.as_user("susan")
    def test_editor_sees_edit_link(self, client):
        response = client.get("/notebooks/wendy/heros-legendes/notes")
        assert '?edit"' in response.content.decode()

    @UserMixin.as_user("mary")
    def test_viewer_does_not_see_edit_link(self, client):
        response = client.get("/notebooks/susan/campaign-notes/session-log")
        assert '?edit"' not in response.content.decode()

    def test_anonymous_does_not_see_edit_link(self, client):
        response = client.get("/notebooks/susan/campaign-notes/session-log")
        assert '?edit"' not in response.content.decode()

    @UserMixin.as_user("wendy")
    def test_owner_can_edit_page(self, client):
        page = self.wendys_notebook.get_page(path="notes")
        initial_version_count = page.version_set.count()
        response = client.post("/notebooks/wendy/heros-legendes/notes?edit", {
            "content": "# Updated Notes\n\nNew content.",
        })
        assert response.status_code == HTTPStatus.FOUND
        assert response.url == "/notebooks/wendy/heros-legendes/notes"
        page.refresh_from_db()
        assert page.version_set.count() == initial_version_count + 1
        assert page.latest_version.content.data == b"# Updated Notes\n\nNew content."

    @UserMixin.as_user("susan")
    def test_editor_can_edit_page(self, client):
        page = self.wendys_notebook.get_page(path="notes")
        response = client.post("/notebooks/wendy/heros-legendes/notes?edit", {
            "content": "# Editor Update",
        })
        assert response.status_code == HTTPStatus.FOUND
        page.refresh_from_db()
        assert page.latest_version.content.data == b"# Editor Update"
        assert page.latest_version.created_by == self.susan

    @UserMixin.as_user("wendy")
    def test_editing_index_redirects_to_folder(self, client):
        response = client.post("/notebooks/wendy/heros-legendes/index", {
            "content": "# Updated Index",
        })
        assert response.status_code == HTTPStatus.FOUND
        assert response.url == "/notebooks/wendy/heros-legendes/"

    @UserMixin.as_user("wendy")
    def test_edit_page_with_file_upload(self, client):
        page = self.wendys_notebook.get_page(path="heroes/shield.png")
        initial_version_count = page.version_set.count()
        new_png = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x02"
        upload = BytesIO(new_png)
        upload.name = "shield.png"
        response = client.post(
            "/notebooks/wendy/heros-legendes/heroes/shield.png?edit",
            {"file": upload},
        )
        assert response.status_code == HTTPStatus.FOUND
        page.refresh_from_db()
        assert page.version_set.count() == initial_version_count + 1
        assert page.latest_version.content.data == new_png

    @UserMixin.as_user("susan")
    def test_editor_can_upload_file(self, client):
        page = self.wendys_notebook.get_page(path="heroes/shield.png")
        new_png = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x03"
        upload = BytesIO(new_png)
        upload.name = "shield.png"
        response = client.post(
            "/notebooks/wendy/heros-legendes/heroes/shield.png?edit",
            {"file": upload},
        )
        assert response.status_code == HTTPStatus.FOUND
        page.refresh_from_db()
        assert page.latest_version.content.data == new_png

    @UserMixin.as_user("mary")
    def test_viewer_cannot_upload_file(self, client):
        page = self.wendys_notebook.get_page(path="heroes/shield.png")
        initial_data = page.latest_version.content.data
        upload = BytesIO(b"\x89PNG\r\n\x1a\n")
        upload.name = "shield.png"
        response = client.post(
            "/notebooks/wendy/heros-legendes/heroes/shield.png?edit",
            {"file": upload},
        )
        assert response.status_code == HTTPStatus.FORBIDDEN
        page.refresh_from_db()
        assert page.latest_version.content.data == initial_data

    def test_anonymous_cannot_upload_file(self, client):
        self.wendys_notebook.visibility = Notebook.Visibility.PUBLIC
        self.wendys_notebook.save()
        page = self.wendys_notebook.get_page(path="heroes/shield.png")
        initial_data = page.latest_version.content.data
        upload = BytesIO(b"\x89PNG\r\n\x1a\n")
        upload.name = "shield.png"
        response = client.post(
            "/notebooks/wendy/heros-legendes/heroes/shield.png?edit",
            {"file": upload},
        )
        assert response.status_code == HTTPStatus.UNAUTHORIZED
        page.refresh_from_db()
        assert page.latest_version.content.data == initial_data

    @UserMixin.as_user("mary")
    def test_viewer_cannot_edit(self, client):
        page = self.wendys_notebook.get_page(path="notes")
        initial_data = page.latest_version.content.data
        response = client.post("/notebooks/wendy/heros-legendes/notes?edit", {
            "content": "# Hacked",
        })
        assert response.status_code == HTTPStatus.FORBIDDEN
        page.refresh_from_db()
        assert page.latest_version.content.data == initial_data

    def test_anonymous_cannot_edit(self, client):
        self.wendys_notebook.visibility = Notebook.Visibility.PUBLIC
        self.wendys_notebook.save()
        page = self.wendys_notebook.get_page(path="notes")
        initial_data = page.latest_version.content.data
        response = client.post("/notebooks/wendy/heros-legendes/notes?edit", {
            "content": "# Hacked",
        })
        assert response.status_code == HTTPStatus.UNAUTHORIZED
        page.refresh_from_db()
        assert page.latest_version.content.data == initial_data

    @UserMixin.as_user("wendy")
    def test_unresolved_path_returns_404_with_form_for_owner(self, client):
        response = client.get("/notebooks/wendy/heros-legendes/rumours")
        assert response.status_code == HTTPStatus.NOT_FOUND
        content = response.content.decode()
        assert "<form" in content
        assert 'name="filename" value="Rumours"' in content

    @UserMixin.as_user("susan")
    def test_unresolved_path_returns_404_with_form_for_editor(self, client):
        response = client.get("/notebooks/wendy/heros-legendes/monsters/goblin")
        assert response.status_code == HTTPStatus.NOT_FOUND
        content = response.content.decode()
        assert "<form" in content
        assert 'name="filename" value="Monsters/Goblin"' in content

    @UserMixin.as_user("mary")
    def test_unresolved_path_returns_404_without_form_for_viewer(self, client):
        response = client.get("/notebooks/wendy/heros-legendes/rumours")
        assert response.status_code == HTTPStatus.NOT_FOUND
        content = response.content.decode()
        assert 'name="filename"' not in content

    def test_unresolved_path_returns_404_without_form_for_anonymous(self, client):
        self.wendys_notebook.visibility = Notebook.Visibility.PUBLIC
        self.wendys_notebook.save()
        response = client.get("/notebooks/wendy/heros-legendes/rumours")
        assert response.status_code == HTTPStatus.NOT_FOUND
        content = response.content.decode()
        assert 'name="filename"' not in content

    @UserMixin.as_user("wendy")
    def test_create_page_from_unresolved_path(self, client):
        response = client.post("/notebooks/wendy/heros-legendes/bestiary/dragon", {
            "filename": "dragon",
            "content": "# Dragon\n\nA fearsome creature.",
        })
        assert response.status_code == HTTPStatus.FOUND
        assert response.url == "/notebooks/wendy/heros-legendes/bestiary/dragon"
        page = self.wendys_notebook.get_page(path="bestiary/dragon")
        assert page.latest_version.filename == "bestiary/dragon.md"
        assert page.latest_version.content.data == b"# Dragon\n\nA fearsome creature."
        assert page.latest_version.created_by == self.wendy

    @UserMixin.as_user("wendy")
    def test_create_page_allows_different_filename(self, client):
        response = client.post(
            "/notebooks/wendy/heros-legendes/quests/retrieve-artifact",
            {
                "filename": "Adventures/The MacGuffin Quest.md",
                "content": "# The MacGuffin Quest",
            },
        )
        assert response.status_code == HTTPStatus.FOUND
        expected_url = "/notebooks/wendy/heros-legendes/adventures/the-macguffin-quest"
        assert response.url == expected_url
        page = self.wendys_notebook.get_page(path="adventures/the-macguffin-quest")
        assert page.latest_version.filename == "Adventures/The MacGuffin Quest.md"

    @UserMixin.as_user("wendy")
    def test_create_page_without_filename_returns_error(self, client):
        initial_count = Page.objects.filter(wiki=self.wendys_notebook).count()
        response = client.post("/notebooks/wendy/heros-legendes/tavern", {
            "filename": "",
            "content": "# The Prancing Pony",
        })
        assert response.status_code == HTTPStatus.BAD_REQUEST
        assert Page.objects.filter(wiki=self.wendys_notebook).count() == initial_count
