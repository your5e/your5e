import html
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
    #   mary's notebook (site):     wendy=editor, susan=viewer
    #   susan's notebook (public):  mary=editor, wendy=viewer
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
            visibility=Notebook.Visibility.USERS,
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
            notebook=self.susans_notebook,
            user=self.wendy,
            role=NotebookPermission.Role.VIEWER,
        )
        NotebookPermission.objects.create(
            notebook=self.marys_notebook,
            user=self.wendy,
            role=NotebookPermission.Role.EDITOR,
        )

        self.wendys_index_text = "This is the index page."
        self.wendys_pages = ["notes", "links", "session-one"]
        index_page = Page.objects.create(wiki=self.wendys_notebook)
        index_page.update(
            filename="index.md",
            mime_type="text/markdown",
            data=b"# Welcome\n\n" + self.wendys_index_text.encode(),
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

        self.wendys_heroes_index_text = "Meet the heroes of this campaign."
        heroes_index = Page.objects.create(wiki=self.wendys_notebook)
        heroes_index.update(
            filename="heroes/index.md",
            mime_type="text/markdown",
            data=b"# Heroes\n\n" + self.wendys_heroes_index_text.encode(),
            created_by=self.wendy,
        )

        villains_page = Page.objects.create(wiki=self.wendys_notebook)
        villains_page.update(
            filename="villains/necromancer.md",
            mime_type="text/markdown",
            data=b"# The Necromancer\n\nA dark wizard.",
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

        self.susans_index_text = "Welcome to the campaign."
        self.susans_pages = ["session-log"]
        susans_index = Page.objects.create(wiki=self.susans_notebook)
        susans_index.update(
            filename="index.md",
            mime_type="text/markdown",
            data=b"# Campaign Notes\n\n" + self.susans_index_text.encode(),
            created_by=self.susan,
        )
        session_log = Page.objects.create(wiki=self.susans_notebook)
        session_log.update(
            filename="session-log.md",
            mime_type="text/markdown",
            data=b"# Session Log\n\nPublic campaign notes.",
            created_by=self.susan,
        )

        self.susans_npcs_index_text = "Notable characters in the campaign."
        npcs_index = Page.objects.create(wiki=self.susans_notebook)
        npcs_index.update(
            filename="npcs/index.md",
            mime_type="text/markdown",
            data=b"# NPCs\n\n" + self.susans_npcs_index_text.encode(),
            created_by=self.susan,
        )
        npcs_page = Page.objects.create(wiki=self.susans_notebook)
        npcs_page.update(
            filename="npcs/innkeeper.md",
            mime_type="text/markdown",
            data=b"# The Innkeeper\n\nA friendly barkeep.",
            created_by=self.susan,
        )

        susans_deleted = Page.objects.create(wiki=self.susans_notebook)
        susans_deleted.update(
            filename="old-session.md",
            mime_type="text/markdown",
            data=b"# Old Session\n\nDeleted session notes.",
            created_by=self.susan,
        )
        susans_deleted.soft_delete()

        self.marys_index_text = "Welcome to the world."
        self.marys_pages = ["history"]
        marys_index = Page.objects.create(wiki=self.marys_notebook)
        marys_index.update(
            filename="index.md",
            mime_type="text/markdown",
            data=b"# World Lore\n\n" + self.marys_index_text.encode(),
            created_by=self.mary,
        )
        lore_page = Page.objects.create(wiki=self.marys_notebook)
        lore_page.update(
            filename="history.md",
            mime_type="text/markdown",
            data=b"# History\n\nThe world began...",
            created_by=self.mary,
        )

        self.marys_regions_index_text = "The regions of this world."
        regions_index = Page.objects.create(wiki=self.marys_notebook)
        regions_index.update(
            filename="regions/index.md",
            mime_type="text/markdown",
            data=b"# Regions\n\n" + self.marys_regions_index_text.encode(),
            created_by=self.mary,
        )
        regions_page = Page.objects.create(wiki=self.marys_notebook)
        regions_page.update(
            filename="regions/northlands.md",
            mime_type="text/markdown",
            data=b"# The Northlands\n\nA frozen wilderness.",
            created_by=self.mary,
        )

        marys_deleted = Page.objects.create(wiki=self.marys_notebook)
        marys_deleted.update(
            filename="old-lore.md",
            mime_type="text/markdown",
            data=b"# Old Lore\n\nDeleted lore.",
            created_by=self.mary,
        )
        marys_deleted.soft_delete()
        NotebookPermission.objects.create(
            notebook=self.marys_notebook,
            user=self.susan,
            role=NotebookPermission.Role.VIEWER,
        )

    def assert_notebook_name_present(self, content, notebook):
        assert html.escape(notebook.name) in content

    def assert_index_content_present(self, content, notebook):
        assert html.escape(notebook.name) in content
        assert notebook.get_absolute_url() in content
        index_text = {
            self.wendys_notebook: self.wendys_index_text,
            self.marys_notebook: self.marys_index_text,
            self.susans_notebook: self.susans_index_text,
        }[notebook]
        assert index_text in content
        pages = {
            self.wendys_notebook: self.wendys_pages,
            self.marys_notebook: self.marys_pages,
            self.susans_notebook: self.susans_pages,
        }[notebook]
        for page_path in pages:
            assert f'href="{notebook.get_absolute_url()}{page_path}"' in content

    def assert_notebook_name_absent(self, content, notebook):
        assert html.escape(notebook.name) not in content

    def assert_index_content_absent(self, content, notebook):
        assert html.escape(notebook.name) not in content
        assert notebook.get_absolute_url() not in content
        index_text = {
            self.wendys_notebook: self.wendys_index_text,
            self.marys_notebook: self.marys_index_text,
            self.susans_notebook: self.susans_index_text,
        }[notebook]
        assert index_text not in content
        pages = {
            self.wendys_notebook: self.wendys_pages,
            self.marys_notebook: self.marys_pages,
            self.susans_notebook: self.susans_pages,
        }[notebook]
        for page_path in pages:
            assert f'href="{notebook.get_absolute_url()}{page_path}"' not in content

    def assert_can_manage(self, content):
        assert 'action="/notebooks/rename"' in content
        assert 'action="/notebooks/visibility"' in content
        assert 'action="/notebooks/collaborators"' in content

    def assert_cannot_manage(self, content):
        assert 'action="/notebooks/rename"' not in content
        assert 'action="/notebooks/visibility"' not in content
        assert 'action="/notebooks/collaborators"' not in content

    def assert_edit_controls_present(self, content):
        assert '?edit">Edit' in content
        assert 'action="/notebooks/restore"' in content
        assert '<input type="file"' in content
        assert 'action="/notebooks/delete"' in content

    def assert_edit_controls_absent(self, content):
        assert '?edit">Edit' not in content
        assert 'action="/notebooks/restore"' not in content
        assert '<input type="file"' not in content
        assert 'action="/notebooks/delete"' not in content

    def assert_page_edit_link_present(self, content):
        assert '?edit">Edit</a>' in content

    def assert_page_edit_link_absent(self, content):
        assert '?edit">Edit</a>' not in content

    def assert_create_form_present(self, content):
        assert 'name="filename"' in content

    def assert_create_form_absent(self, content):
        assert 'name="filename"' not in content

    def assert_page_heading_present(self, content, heading):
        assert f"<h1>{heading}</h1>" in content

    def assert_page_heading_absent(self, content, heading):
        assert f"<h1>{heading}</h1>" not in content

    def assert_confirmation_form_present(self, content, action):
        assert f'action="{action}"' in content
        assert 'name="confirmed"' in content

    def assert_edit_page_form_present(self, content):
        assert "<form" in content
        assert "<textarea" in content
        assert 'type="file"' in content
        assert 'type="submit"' in content
        assert 'action="/notebooks/delete"' in content


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

    def test_get_folder_url_for_nested_path(self):
        url = self.wendys_notebook.get_folder_url("heroes/theron")
        assert url == "/notebooks/wendy/heros-legendes/heroes/"

    def test_get_folder_url_for_root_path(self):
        url = self.wendys_notebook.get_folder_url("notes")
        assert url == "/notebooks/wendy/heros-legendes/"


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
        assert response.url == "/profile/wendy/"
        notebook = Notebook.objects.get(name="New Notebook")
        assert notebook.owner == self.wendy
        assert notebook.slug == "new-notebook"

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

    @UserMixin.as_user("susan")
    def test_editor_cannot_create_notebook_on_other_profile(self, client):
        response = client.post(
            "/profile/wendy/notebooks",
            {"notebook_name": "Hacked Notebook"},
        )
        assert response.status_code == HTTPStatus.FORBIDDEN
        assert not Notebook.objects.filter(name="Hacked Notebook").exists()

    @UserMixin.as_user("mary")
    def test_viewer_cannot_create_notebook_on_other_profile(self, client):
        response = client.post(
            "/profile/wendy/notebooks",
            {"notebook_name": "Hacked Notebook"},
        )
        assert response.status_code == HTTPStatus.FORBIDDEN
        assert not Notebook.objects.filter(name="Hacked Notebook").exists()

    @UserMixin.as_user("hugh")
    def test_non_collaborator_cannot_create_notebook_on_other_profile(self, client):
        response = client.post(
            "/profile/wendy/notebooks",
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
    def test_owner_sees_management_controls(self, client):
        response = client.get("/notebooks/wendy/heros-legendes/")
        assert response.status_code == HTTPStatus.OK
        content = response.content.decode()
        self.assert_index_content_present(content, self.wendys_notebook)
        self.assert_can_manage(content)

    @UserMixin.as_user("susan")
    def test_editor_does_not_see_management_controls(self, client):
        response = client.get("/notebooks/wendy/heros-legendes/")
        content = response.content.decode()
        self.assert_index_content_present(content, self.wendys_notebook)
        self.assert_cannot_manage(content)

    @UserMixin.as_user("mary")
    def test_viewer_does_not_see_management_controls(self, client):
        response = client.get("/notebooks/wendy/heros-legendes/")
        content = response.content.decode()
        self.assert_index_content_present(content, self.wendys_notebook)
        self.assert_cannot_manage(content)

    @UserMixin.as_user("hugh")
    def test_non_collaborator_cannot_view_notebook(self, client):
        response = client.get("/notebooks/wendy/heros-legendes/")
        assert response.status_code == HTTPStatus.FORBIDDEN
        self.assert_index_content_absent(
            response.content.decode(),
            self.wendys_notebook,
        )

    def test_anonymous_cannot_view_notebook(self, client):
        response = client.get("/notebooks/wendy/heros-legendes/")
        assert response.status_code == HTTPStatus.UNAUTHORIZED
        self.assert_index_content_absent(
            response.content.decode(),
            self.wendys_notebook,
        )


@pytest.mark.django_db
class TestNotebookRenameView(NotebookMixin):
    @UserMixin.as_user("wendy")
    def test_owner_can_rename_notebook(self, client):
        response = client.post(
            "/notebooks/rename",
            {"notebook": self.wendys_notebook.pk, "name": "Session Notes"},
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
        self.assert_confirmation_form_present(
            response.content.decode(),
            "/notebooks/visibility",
        )

    @UserMixin.as_user("wendy")
    def test_visibility_change_confirmed(self, client):
        response = client.post("/notebooks/visibility", {
            "notebook": self.wendys_notebook.pk,
            "visibility": "public",
            "confirmed": "true",
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
            "confirmed": "true",
        })
        assert response.status_code == HTTPStatus.FORBIDDEN
        self.wendys_notebook.refresh_from_db()
        assert self.wendys_notebook.visibility == Notebook.Visibility.PRIVATE

    @UserMixin.as_user("mary")
    def test_viewer_cannot_change_visibility(self, client):
        response = client.post("/notebooks/visibility", {
            "notebook": self.wendys_notebook.pk,
            "visibility": "public",
            "confirmed": "true",
        })
        assert response.status_code == HTTPStatus.FORBIDDEN
        self.wendys_notebook.refresh_from_db()
        assert self.wendys_notebook.visibility == Notebook.Visibility.PRIVATE

    @UserMixin.as_user("hugh")
    def test_non_collaborator_cannot_change_visibility(self, client):
        response = client.post("/notebooks/visibility", {
            "notebook": self.wendys_notebook.pk,
            "visibility": "public",
            "confirmed": "true",
        })
        assert response.status_code == HTTPStatus.FORBIDDEN
        self.wendys_notebook.refresh_from_db()
        assert self.wendys_notebook.visibility == Notebook.Visibility.PRIVATE

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
            "username": "hugh",
            "role": "viewer",
        })
        assert response.status_code == HTTPStatus.OK
        assert not NotebookPermission.objects.filter(
            notebook=self.wendys_notebook,
            user=self.hugh,
        ).exists()
        self.assert_confirmation_form_present(
            response.content.decode(),
            "/notebooks/collaborators",
        )

    @UserMixin.as_user("wendy")
    def test_add_collaborator_confirmed(self, client):
        response = client.post("/notebooks/collaborators", {
            "notebook": self.wendys_notebook.pk,
            "username": "hugh",
            "role": "viewer",
            "confirmed": "true",
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
        self.assert_confirmation_form_present(
            response.content.decode(),
            "/notebooks/collaborators",
        )

    @UserMixin.as_user("wendy")
    def test_remove_collaborator_confirmed(self, client):
        response = client.post("/notebooks/collaborators", {
            "notebook": self.wendys_notebook.pk,
            "remove": str(self.susan.pk),
            "confirmed": "true",
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
        self.assert_confirmation_form_present(
            response.content.decode(),
            "/notebooks/collaborators",
        )

    @UserMixin.as_user("wendy")
    def test_change_collaborator_role_confirmed(self, client):
        response = client.post("/notebooks/collaborators", {
            "notebook": self.wendys_notebook.pk,
            "change_role": str(self.susan.pk),
            "role": "viewer",
            "confirmed": "true",
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
            "confirmed": "true",
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
            "confirmed": "true",
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
            "confirmed": "true",
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
            "confirmed": "true",
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
            "confirmed": "true",
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
            "confirmed": "true",
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
            "confirmed": "true",
        })
        assert response.status_code == HTTPStatus.FORBIDDEN

    @UserMixin.as_user("hugh")
    def test_non_collaborator_cannot_remove_collaborator(self, client):
        response = client.post("/notebooks/collaborators", {
            "notebook": self.wendys_notebook.pk,
            "remove": str(self.susan.pk),
            "confirmed": "true",
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
            "confirmed": "true",
        })
        assert response.status_code == HTTPStatus.FORBIDDEN
        self.susans_permission.refresh_from_db()
        assert self.susans_permission.role == NotebookPermission.Role.EDITOR

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

    def test_anonymous_cannot_remove_collaborator(self, client):
        response = client.post("/notebooks/collaborators", {
            "notebook": self.wendys_notebook.pk,
            "remove": str(self.susan.pk),
            "confirmed": "true",
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
            "confirmed": "true",
        })
        assert response.status_code == HTTPStatus.UNAUTHORIZED
        self.susans_permission.refresh_from_db()
        assert self.susans_permission.role == NotebookPermission.Role.EDITOR


@pytest.mark.django_db
class TestNotebookIndexPage(NotebookMixin):
    @UserMixin.as_user("wendy")
    def test_owner_sees_private_restricted_notebook_index(self, client):
        response = client.get("/notebooks/wendy/heros-legendes/heroes/")
        content = response.content.decode()
        assert response.status_code == HTTPStatus.OK
        self.assert_notebook_name_present(content, self.wendys_notebook)
        assert self.wendys_heroes_index_text in content
        self.assert_edit_controls_present(content)

    @UserMixin.as_user("susan")
    def test_editor_sees_private_restricted_notebook_index(self, client):
        response = client.get("/notebooks/wendy/heros-legendes/heroes/")
        content = response.content.decode()
        assert response.status_code == HTTPStatus.OK
        self.assert_notebook_name_present(content, self.wendys_notebook)
        assert self.wendys_heroes_index_text in content
        self.assert_edit_controls_present(content)

    @UserMixin.as_user("mary")
    def test_viewer_sees_private_restricted_notebook_index(self, client):
        response = client.get("/notebooks/wendy/heros-legendes/heroes/")
        content = response.content.decode()
        assert response.status_code == HTTPStatus.OK
        self.assert_notebook_name_present(content, self.wendys_notebook)
        assert self.wendys_heroes_index_text in content
        self.assert_edit_controls_absent(content)

    @UserMixin.as_user("hugh")
    def test_non_collaborator_cannot_see_private_restricted_notebook_index(self, client):  # noqa: E501
        response = client.get("/notebooks/wendy/heros-legendes/heroes/")
        content = response.content.decode()
        assert response.status_code == HTTPStatus.FORBIDDEN
        assert self.wendys_heroes_index_text not in content

    def test_anonymous_cannot_see_private_restricted_notebook_index(self, client):
        response = client.get("/notebooks/wendy/heros-legendes/heroes/")
        content = response.content.decode()
        assert response.status_code == HTTPStatus.UNAUTHORIZED
        assert self.wendys_heroes_index_text not in content

    @UserMixin.as_user("mary")
    def test_owner_sees_users_restricted_notebook_index(self, client):
        response = client.get("/notebooks/mary/world-lore/regions/")
        content = response.content.decode()
        assert response.status_code == HTTPStatus.OK
        self.assert_notebook_name_present(content, self.marys_notebook)
        assert self.marys_regions_index_text in content
        self.assert_edit_controls_present(content)

    @UserMixin.as_user("wendy")
    def test_editor_sees_users_restricted_notebook_index(self, client):
        response = client.get("/notebooks/mary/world-lore/regions/")
        content = response.content.decode()
        assert response.status_code == HTTPStatus.OK
        self.assert_notebook_name_present(content, self.marys_notebook)
        assert self.marys_regions_index_text in content
        self.assert_edit_controls_present(content)

    @UserMixin.as_user("susan")
    def test_viewer_sees_users_restricted_notebook_index(self, client):
        response = client.get("/notebooks/mary/world-lore/regions/")
        content = response.content.decode()
        assert response.status_code == HTTPStatus.OK
        self.assert_notebook_name_present(content, self.marys_notebook)
        assert self.marys_regions_index_text in content
        self.assert_edit_controls_absent(content)

    @UserMixin.as_user("hugh")
    def test_non_collaborator_sees_users_restricted_notebook_index(self, client):
        response = client.get("/notebooks/mary/world-lore/regions/")
        content = response.content.decode()
        assert response.status_code == HTTPStatus.OK
        self.assert_notebook_name_present(content, self.marys_notebook)
        assert self.marys_regions_index_text in content
        self.assert_edit_controls_absent(content)

    def test_anonymous_cannot_see_users_restricted_notebook_index(self, client):
        response = client.get("/notebooks/mary/world-lore/regions/")
        content = response.content.decode()
        assert response.status_code == HTTPStatus.UNAUTHORIZED
        assert self.marys_regions_index_text not in content

    @UserMixin.as_user("susan")
    def test_owner_sees_public_notebook_index(self, client):
        response = client.get("/notebooks/susan/campaign-notes/npcs/")
        content = response.content.decode()
        assert response.status_code == HTTPStatus.OK
        self.assert_notebook_name_present(content, self.susans_notebook)
        assert self.susans_npcs_index_text in content
        self.assert_edit_controls_present(content)

    @UserMixin.as_user("mary")
    def test_editor_sees_public_notebook_index(self, client):
        response = client.get("/notebooks/susan/campaign-notes/npcs/")
        content = response.content.decode()
        assert response.status_code == HTTPStatus.OK
        self.assert_notebook_name_present(content, self.susans_notebook)
        assert self.susans_npcs_index_text in content
        self.assert_edit_controls_present(content)

    @UserMixin.as_user("wendy")
    def test_viewer_sees_public_notebook_index(self, client):
        response = client.get("/notebooks/susan/campaign-notes/npcs/")
        content = response.content.decode()
        assert response.status_code == HTTPStatus.OK
        self.assert_notebook_name_present(content, self.susans_notebook)
        assert self.susans_npcs_index_text in content
        self.assert_edit_controls_absent(content)

    @UserMixin.as_user("hugh")
    def test_non_collaborator_sees_public_notebook_index(self, client):
        response = client.get("/notebooks/susan/campaign-notes/npcs/")
        content = response.content.decode()
        assert response.status_code == HTTPStatus.OK
        self.assert_notebook_name_present(content, self.susans_notebook)
        assert self.susans_npcs_index_text in content
        self.assert_edit_controls_absent(content)

    def test_anonymous_sees_public_notebook_index(self, client):
        response = client.get("/notebooks/susan/campaign-notes/npcs/")
        content = response.content.decode()
        assert response.status_code == HTTPStatus.OK
        self.assert_notebook_name_present(content, self.susans_notebook)
        assert self.susans_npcs_index_text in content
        self.assert_edit_controls_absent(content)

    @UserMixin.as_user("wendy")
    def test_index_not_listed_as_page(self, client):
        response = client.get("/notebooks/wendy/heros-legendes/heroes/")
        content = response.content.decode()
        assert self.wendys_heroes_index_text in content
        assert ">index<" not in content.lower()

    @UserMixin.as_user("wendy")
    def test_index_page_shows_version_dropdown(self, client):
        response = client.get("/notebooks/wendy/heros-legendes/heroes/")
        content = response.content.decode()
        assert self.wendys_heroes_index_text in content
        assert '<option value="1"' in content

    @UserMixin.as_user("wendy")
    def test_owner_sees_creation_form_on_empty_folder(self, client):
        response = client.get("/notebooks/wendy/heros-legendes/monsters/")
        assert response.status_code == HTTPStatus.NOT_FOUND
        content = response.content.decode()
        assert 'name="filename" value="Monsters/Index"' in content
        assert 'action="/notebooks/wendy/heros-legendes/monsters/index"' in content

    @UserMixin.as_user("susan")
    def test_editor_sees_creation_form_on_empty_folder(self, client):
        response = client.get("/notebooks/wendy/heros-legendes/monsters/")
        assert response.status_code == HTTPStatus.NOT_FOUND
        content = response.content.decode()
        assert 'name="filename" value="Monsters/Index"' in content

    @UserMixin.as_user("mary")
    def test_viewer_sees_empty_folder_without_form(self, client):
        response = client.get("/notebooks/wendy/heros-legendes/monsters/")
        assert response.status_code == HTTPStatus.NOT_FOUND
        self.assert_create_form_absent(response.content.decode())

    @UserMixin.as_user("hugh")
    def test_non_collaborator_cannot_view_empty_folder(self, client):
        response = client.get("/notebooks/wendy/heros-legendes/monsters/")
        assert response.status_code == HTTPStatus.FORBIDDEN

    def test_anonymous_cannot_view_empty_folder(self, client):
        response = client.get("/notebooks/wendy/heros-legendes/monsters/")
        assert response.status_code == HTTPStatus.UNAUTHORIZED

    @UserMixin.as_user("wendy")
    def test_folder_with_content_but_no_index_shows_create(self, client):
        response = client.get("/notebooks/wendy/heros-legendes/villains/")
        assert response.status_code == HTTPStatus.OK
        content = response.content.decode()
        assert "Create index" in content
        assert "Edit index" not in content

    @UserMixin.as_user("susan")
    def test_editor_sees_create_index_link(self, client):
        response = client.get("/notebooks/wendy/heros-legendes/villains/")
        assert response.status_code == HTTPStatus.OK
        content = response.content.decode()
        assert "Create index" in content

    @UserMixin.as_user("mary")
    def test_viewer_does_not_see_create_index_link(self, client):
        response = client.get("/notebooks/wendy/heros-legendes/villains/")
        assert response.status_code == HTTPStatus.OK
        content = response.content.decode()
        assert "Create index" not in content

    @UserMixin.as_user("hugh")
    def test_non_collaborator_cannot_view_folder_without_index(self, client):
        response = client.get("/notebooks/wendy/heros-legendes/villains/")
        assert response.status_code == HTTPStatus.FORBIDDEN

    def test_anonymous_cannot_view_folder_without_index(self, client):
        response = client.get("/notebooks/wendy/heros-legendes/villains/")
        assert response.status_code == HTTPStatus.UNAUTHORIZED

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
    def test_owner_can_upload_markdown(self, client):
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
        assert page.latest_version.content.data == b"# Updated Notes\n\nNew content."

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
class TestNotebookPageView(NotebookMixin):
    @UserMixin.as_user("wendy")
    def test_owner_can_view_page(self, client):
        response = client.get("/notebooks/wendy/heros-legendes/heroes/theron")
        assert response.status_code == HTTPStatus.OK
        content = response.content.decode()
        self.assert_notebook_name_present(content, self.wendys_notebook)
        self.assert_page_heading_present(content, "Theron")
        self.assert_page_edit_link_present(content)

    @UserMixin.as_user("susan")
    def test_editor_can_view_page(self, client):
        response = client.get("/notebooks/wendy/heros-legendes/heroes/theron")
        assert response.status_code == HTTPStatus.OK
        content = response.content.decode()
        self.assert_notebook_name_present(content, self.wendys_notebook)
        self.assert_page_heading_present(content, "Theron")
        self.assert_page_edit_link_present(content)

    @UserMixin.as_user("mary")
    def test_viewer_can_view_page(self, client):
        response = client.get("/notebooks/wendy/heros-legendes/heroes/theron")
        assert response.status_code == HTTPStatus.OK
        content = response.content.decode()
        self.assert_notebook_name_present(content, self.wendys_notebook)
        self.assert_page_heading_present(content, "Theron")
        self.assert_page_edit_link_absent(content)

    @UserMixin.as_user("hugh")
    def test_non_collaborator_cannot_view_private_page(self, client):
        response = client.get("/notebooks/wendy/heros-legendes/heroes/theron")
        assert response.status_code == HTTPStatus.FORBIDDEN
        content = response.content.decode()
        self.assert_notebook_name_absent(content, self.wendys_notebook)
        self.assert_page_heading_absent(content, "Theron")

    def test_anonymous_cannot_view_private_page(self, client):
        response = client.get("/notebooks/wendy/heros-legendes/heroes/theron")
        assert response.status_code == HTTPStatus.UNAUTHORIZED
        content = response.content.decode()
        self.assert_notebook_name_absent(content, self.wendys_notebook)
        self.assert_page_heading_absent(content, "Theron")

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
        self.assert_notebook_name_present(
            response.content.decode(),
            self.wendys_notebook,
        )

    @UserMixin.as_user("wendy")
    def test_wikilinks_and_markdown_links_resolve_to_correct_paths(self, client):
        response = client.get("/notebooks/wendy/heros-legendes/links")
        assert response.status_code == HTTPStatus.OK
        content = response.content.decode()
        self.assert_notebook_name_present(content, self.wendys_notebook)
        # [[Theron]] wikilink
        assert (
            '<a href="/notebooks/wendy/heros-legendes/heroes/theron">Theron</a>'
            in content
        )
        # [Notes](./notes) markdown link
        assert (
            '<a href="/notebooks/wendy/heros-legendes/notes">Notes</a>'
            in content
        )

    @UserMixin.as_user("wendy")
    def test_view_page_shows_version_info(self, client):
        response = client.get("/notebooks/wendy/heros-legendes/session-one")
        content = response.content.decode()
        self.assert_notebook_name_present(content, self.wendys_notebook)
        page = self.wendys_notebook.get_page(path="session-one")
        versions = page.history()
        v1_date = versions[0].created_at.strftime("%-d %b %Y")
        v2_date = versions[1].created_at.strftime("%-d %b %Y")
        v3_date = versions[2].created_at.strftime("%-d %b %Y")
        assert (
            f'<option value="1">v1 by wendy on {v1_date}</option>'
            in content
        )
        assert (
            f'<option value="2">v2 by susan on {v2_date}</option>'
            in content
        )
        assert (
            f'<option value="3" selected>v3 by wendy on {v3_date}</option>'
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
        self.assert_edit_page_form_present(content)
        assert "# Notes" in content
        assert 'name="filename" value="notes"' in content

    @UserMixin.as_user("wendy")
    def test_edit_binary_shows_form(self, client):
        response = client.get("/notebooks/wendy/heros-legendes/heroes/shield.png?edit")
        assert response.status_code == HTTPStatus.OK
        content = response.content.decode()
        self.assert_edit_page_form_present(content)

    @UserMixin.as_user("susan")
    def test_editor_can_see_edit_form(self, client):
        response = client.get("/notebooks/wendy/heros-legendes/notes?edit")
        assert response.status_code == HTTPStatus.OK
        assert "<form" in response.content.decode()

    @UserMixin.as_user("mary")
    def test_viewer_cannot_see_edit_form(self, client):
        response = client.get("/notebooks/wendy/heros-legendes/notes?edit")
        assert response.status_code == HTTPStatus.FORBIDDEN

    @UserMixin.as_user("hugh")
    def test_non_collaborator_cannot_see_edit_form(self, client):
        response = client.get("/notebooks/wendy/heros-legendes/notes?edit")
        assert response.status_code == HTTPStatus.FORBIDDEN

    def test_anonymous_cannot_see_edit_form(self, client):
        response = client.get("/notebooks/susan/campaign-notes/session-log?edit")
        assert response.status_code == HTTPStatus.UNAUTHORIZED

    @UserMixin.as_user("hugh")
    def test_non_collaborator_can_view_public_page(self, client):
        response = client.get("/notebooks/susan/campaign-notes/session-log")
        assert response.status_code == HTTPStatus.OK
        content = response.content.decode()
        self.assert_notebook_name_present(content, self.susans_notebook)
        self.assert_page_heading_present(content, "Session Log")
        self.assert_page_edit_link_absent(content)

    def test_anonymous_can_view_public_page(self, client):
        response = client.get("/notebooks/susan/campaign-notes/session-log")
        assert response.status_code == HTTPStatus.OK
        content = response.content.decode()
        self.assert_notebook_name_present(content, self.susans_notebook)
        self.assert_page_heading_present(content, "Session Log")
        self.assert_page_edit_link_absent(content)

    @UserMixin.as_user("wendy")
    def test_owner_can_edit_page(self, client):
        page = self.wendys_notebook.get_page(path="notes")
        initial_version_count = page.version_set.count()
        response = client.post("/notebooks/wendy/heros-legendes/notes", {
            "filename": "notes",
            "content": "# Updated Notes\n\nNew content.",
        })
        assert response.status_code == HTTPStatus.FOUND
        page.refresh_from_db()
        assert page.version_set.count() == initial_version_count + 1
        assert page.latest_version.content.data == b"# Updated Notes\n\nNew content."

    @UserMixin.as_user("susan")
    def test_editor_can_edit_page(self, client):
        page = self.wendys_notebook.get_page(path="notes")
        response = client.post("/notebooks/wendy/heros-legendes/notes", {
            "filename": "notes",
            "content": "# Editor Update",
        })
        assert response.status_code == HTTPStatus.FOUND
        page.refresh_from_db()
        assert page.latest_version.content.data == b"# Editor Update"
        assert page.latest_version.created_by == self.susan

    @UserMixin.as_user("mary")
    def test_viewer_cannot_edit(self, client):
        page = self.wendys_notebook.get_page(path="notes")
        initial_data = page.latest_version.content.data
        response = client.post("/notebooks/wendy/heros-legendes/notes", {
            "filename": "notes",
            "content": "# Hacked",
        })
        assert response.status_code == HTTPStatus.FORBIDDEN
        page.refresh_from_db()
        assert page.latest_version.content.data == initial_data

    @UserMixin.as_user("hugh")
    def test_non_collaborator_cannot_edit(self, client):
        page = self.wendys_notebook.get_page(path="notes")
        initial_data = page.latest_version.content.data
        response = client.post("/notebooks/wendy/heros-legendes/notes", {
            "filename": "notes",
            "content": "# Hacked",
        })
        assert response.status_code == HTTPStatus.FORBIDDEN
        page.refresh_from_db()
        assert page.latest_version.content.data == initial_data

    def test_anonymous_cannot_edit(self, client):
        page = self.susans_notebook.get_page(path="session-log")
        initial_data = page.latest_version.content.data
        response = client.post("/notebooks/susan/campaign-notes/session-log", {
            "filename": "session-log",
            "content": "# Hacked",
        })
        assert response.status_code == HTTPStatus.UNAUTHORIZED
        page.refresh_from_db()
        assert page.latest_version.content.data == initial_data

    @UserMixin.as_user("wendy")
    def test_editing_index_redirects_to_folder(self, client):
        response = client.post("/notebooks/wendy/heros-legendes/index", {
            "filename": "index",
            "content": "# Updated Index",
        })
        assert response.status_code == HTTPStatus.FOUND
        assert response.url == "/notebooks/wendy/heros-legendes/"

    @UserMixin.as_user("wendy")
    def test_unresolved_path_for_owner(self, client):
        response = client.get("/notebooks/wendy/heros-legendes/rumours")
        assert response.status_code == HTTPStatus.NOT_FOUND
        content = response.content.decode()
        self.assert_create_form_present(content)
        assert 'name="filename" value="Rumours"' in content

    @UserMixin.as_user("susan")
    def test_unresolved_path_for_editor(self, client):
        response = client.get("/notebooks/wendy/heros-legendes/monsters/goblin")
        assert response.status_code == HTTPStatus.NOT_FOUND
        content = response.content.decode()
        self.assert_create_form_present(content)
        assert 'name="filename" value="Monsters/Goblin"' in content

    @UserMixin.as_user("mary")
    def test_unresolved_path_for_viewer(self, client):
        response = client.get("/notebooks/wendy/heros-legendes/rumours")
        assert response.status_code == HTTPStatus.NOT_FOUND
        self.assert_create_form_absent(response.content.decode())

    @UserMixin.as_user("hugh")
    def test_unresolved_path_for_non_collaborator(self, client):
        response = client.get("/notebooks/wendy/heros-legendes/rumours")
        assert response.status_code == HTTPStatus.FORBIDDEN

    def test_unresolved_path_for_anonymous(self, client):
        response = client.get("/notebooks/susan/campaign-notes/rumours")
        assert response.status_code == HTTPStatus.NOT_FOUND
        self.assert_create_form_absent(response.content.decode())

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

    @UserMixin.as_user("wendy")
    def test_edit_page_with_new_filename_renames(self, client):
        page = self.wendys_notebook.get_page(path="notes")
        initial_version_count = page.version_set.count()
        response = client.post("/notebooks/wendy/heros-legendes/notes", {
            "filename": "archive/Campaign Notes",
            "content": "# Campaign Notes\n\nRenamed.",
        })
        assert response.status_code == HTTPStatus.FOUND
        assert response.url == "/notebooks/wendy/heros-legendes/archive/campaign-notes"
        page.refresh_from_db()
        assert page.version_set.count() == initial_version_count + 1
        assert page.latest_version.filename == "archive/Campaign Notes.md"
        assert page.latest_version.content.data == b"# Campaign Notes\n\nRenamed."

    @UserMixin.as_user("wendy")
    def test_rename_to_existing_path_shows_error_with_link(self, client):
        page = self.wendys_notebook.get_page(path="notes")
        initial_version_count = page.version_set.count()
        response = client.post("/notebooks/wendy/heros-legendes/notes", {
            "filename": "Session One",
            "content": "# Conflict",
        })
        assert response.status_code == HTTPStatus.CONFLICT
        content = response.content.decode()
        assert "already exists" in content
        expected_link = (
            '<a href="/notebooks/wendy/heros-legendes/session-one">'
            "Session One</a>"
        )
        assert expected_link in content
        page.refresh_from_db()
        assert page.version_set.count() == initial_version_count

    @UserMixin.as_user("susan")
    def test_editor_can_create_page(self, client):
        response = client.post("/notebooks/wendy/heros-legendes/locations/tavern", {
            "filename": "Locations/Tavern",
            "content": "# The Tavern",
        })
        assert response.status_code == HTTPStatus.FOUND
        page = self.wendys_notebook.get_page(path="locations/tavern")
        assert page.latest_version.created_by == self.susan

    @UserMixin.as_user("mary")
    def test_viewer_cannot_create_page(self, client):
        initial_count = Page.objects.filter(wiki=self.wendys_notebook).count()
        response = client.post("/notebooks/wendy/heros-legendes/locations/tavern", {
            "filename": "Locations/Tavern",
            "content": "# The Tavern",
        })
        assert response.status_code == HTTPStatus.FORBIDDEN
        assert Page.objects.filter(wiki=self.wendys_notebook).count() == initial_count

    @UserMixin.as_user("hugh")
    def test_non_collaborator_cannot_create_page(self, client):
        initial_count = Page.objects.filter(wiki=self.wendys_notebook).count()
        response = client.post("/notebooks/wendy/heros-legendes/locations/tavern", {
            "filename": "Locations/Tavern",
            "content": "# The Tavern",
        })
        assert response.status_code == HTTPStatus.FORBIDDEN
        assert Page.objects.filter(wiki=self.wendys_notebook).count() == initial_count

    def test_anonymous_cannot_create_page(self, client):
        initial_count = Page.objects.filter(wiki=self.susans_notebook).count()
        response = client.post("/notebooks/susan/campaign-notes/locations/tavern", {
            "filename": "Locations/Tavern",
            "content": "# The Tavern",
        })
        assert response.status_code == HTTPStatus.UNAUTHORIZED
        assert Page.objects.filter(wiki=self.susans_notebook).count() == initial_count

    @UserMixin.as_user("mary")
    def test_owner_can_view_users_restricted_notebook(self, client):
        response = client.get("/notebooks/mary/world-lore/history")
        assert response.status_code == HTTPStatus.OK
        assert "The world began" in response.content.decode()

    @UserMixin.as_user("wendy")
    def test_editor_can_view_users_restricted_notebook(self, client):
        response = client.get("/notebooks/mary/world-lore/history")
        assert response.status_code == HTTPStatus.OK
        assert "The world began" in response.content.decode()

    @UserMixin.as_user("wendy")
    def test_editor_can_edit_users_restricted_notebook(self, client):
        page = self.marys_notebook.get_page(path="history")
        response = client.post("/notebooks/mary/world-lore/history", {
            "filename": "history",
            "content": "# History\n\nEdited by Wendy.",
        })
        assert response.status_code == HTTPStatus.FOUND
        page.refresh_from_db()
        assert page.latest_version.content.data == b"# History\n\nEdited by Wendy."
        assert page.latest_version.created_by == self.wendy

    @UserMixin.as_user("wendy")
    def test_editor_can_create_page_in_users_restricted_notebook(self, client):
        response = client.post("/notebooks/mary/world-lore/geography", {
            "filename": "Geography",
            "content": "# Geography\n\nMountains and rivers.",
        })
        assert response.status_code == HTTPStatus.FOUND
        page = self.marys_notebook.get_page(path="geography")
        assert page.latest_version.created_by == self.wendy

    @UserMixin.as_user("susan")
    def test_viewer_can_view_users_restricted_notebook(self, client):
        response = client.get("/notebooks/mary/world-lore/history")
        assert response.status_code == HTTPStatus.OK
        assert "The world began" in response.content.decode()

    @UserMixin.as_user("hugh")
    def test_non_collaborator_can_view_users_restricted_notebook(self, client):
        response = client.get("/notebooks/mary/world-lore/history")
        assert response.status_code == HTTPStatus.OK

    @UserMixin.as_user("hugh")
    def test_non_collaborator_cannot_edit_users_restricted_notebook(self, client):
        response = client.post("/notebooks/mary/world-lore/history", {
            "filename": "history",
            "content": "# Hacked",
        })
        assert response.status_code == HTTPStatus.FORBIDDEN

    def test_anonymous_cannot_view_users_restricted_notebook(self, client):
        response = client.get("/notebooks/mary/world-lore/history")
        assert response.status_code == HTTPStatus.UNAUTHORIZED
        self.assert_notebook_name_absent(
            response.content.decode(),
            self.marys_notebook,
        )

    @UserMixin.as_user("mary")
    def test_owner_can_edit_users_restricted_notebook(self, client):
        page = self.marys_notebook.get_page(path="history")
        response = client.post("/notebooks/mary/world-lore/history", {
            "filename": "history",
            "content": "# History\n\nEdited by Mary.",
        })
        assert response.status_code == HTTPStatus.FOUND
        page.refresh_from_db()
        assert page.latest_version.content.data == b"# History\n\nEdited by Mary."
        assert page.latest_version.created_by == self.mary

    @UserMixin.as_user("susan")
    def test_viewer_cannot_edit_users_restricted_notebook(self, client):
        page = self.marys_notebook.get_page(path="history")
        initial_data = page.latest_version.content.data
        response = client.post("/notebooks/mary/world-lore/history", {
            "filename": "history",
            "content": "# Hacked",
        })
        assert response.status_code == HTTPStatus.FORBIDDEN
        page.refresh_from_db()
        assert page.latest_version.content.data == initial_data

    def test_anonymous_cannot_edit_users_restricted_notebook(self, client):
        page = self.marys_notebook.get_page(path="history")
        initial_data = page.latest_version.content.data
        response = client.post("/notebooks/mary/world-lore/history", {
            "filename": "history",
            "content": "# Hacked",
        })
        assert response.status_code == HTTPStatus.UNAUTHORIZED
        page.refresh_from_db()
        assert page.latest_version.content.data == initial_data

    @UserMixin.as_user("mary")
    def test_owner_can_create_page_in_users_restricted_notebook(self, client):
        response = client.post("/notebooks/mary/world-lore/cultures", {
            "filename": "Cultures",
            "content": "# Cultures\n\nThe elves and dwarves.",
        })
        assert response.status_code == HTTPStatus.FOUND
        page = self.marys_notebook.get_page(path="cultures")
        assert page.latest_version.created_by == self.mary

    @UserMixin.as_user("susan")
    def test_viewer_cannot_create_page_in_users_restricted_notebook(self, client):
        initial_count = Page.objects.filter(wiki=self.marys_notebook).count()
        response = client.post("/notebooks/mary/world-lore/religions", {
            "filename": "Religions",
            "content": "# Religions",
        })
        assert response.status_code == HTTPStatus.FORBIDDEN
        assert Page.objects.filter(wiki=self.marys_notebook).count() == initial_count

    @UserMixin.as_user("hugh")
    def test_non_collaborator_cannot_create_page_in_users_restricted_notebook(self, client):  # noqa: E501
        initial_count = Page.objects.filter(wiki=self.marys_notebook).count()
        response = client.post("/notebooks/mary/world-lore/religions", {
            "filename": "Religions",
            "content": "# Religions",
        })
        assert response.status_code == HTTPStatus.FORBIDDEN
        assert Page.objects.filter(wiki=self.marys_notebook).count() == initial_count

    def test_anonymous_cannot_create_page_in_users_restricted_notebook(self, client):
        initial_count = Page.objects.filter(wiki=self.marys_notebook).count()
        response = client.post("/notebooks/mary/world-lore/religions", {
            "filename": "Religions",
            "content": "# Religions",
        })
        assert response.status_code == HTTPStatus.UNAUTHORIZED
        assert Page.objects.filter(wiki=self.marys_notebook).count() == initial_count

    @UserMixin.as_user("susan")
    def test_owner_can_view_public_notebook(self, client):
        response = client.get("/notebooks/susan/campaign-notes/session-log")
        assert response.status_code == HTTPStatus.OK
        assert "Public campaign notes" in response.content.decode()

    @UserMixin.as_user("mary")
    def test_editor_can_view_public_notebook(self, client):
        response = client.get("/notebooks/susan/campaign-notes/session-log")
        assert response.status_code == HTTPStatus.OK
        assert "Public campaign notes" in response.content.decode()

    @UserMixin.as_user("wendy")
    def test_viewer_can_view_public_notebook(self, client):
        response = client.get("/notebooks/susan/campaign-notes/session-log")
        assert response.status_code == HTTPStatus.OK
        assert "Public campaign notes" in response.content.decode()

    @UserMixin.as_user("hugh")
    def test_non_collaborator_can_view_public_notebook(self, client):
        response = client.get("/notebooks/susan/campaign-notes/session-log")
        assert response.status_code == HTTPStatus.OK
        assert "Public campaign notes" in response.content.decode()

    @UserMixin.as_user("hugh")
    def test_non_collaborator_cannot_edit_public_notebook(self, client):
        response = client.post("/notebooks/susan/campaign-notes/session-log", {
            "filename": "session-log",
            "content": "# Hacked",
        })
        assert response.status_code == HTTPStatus.FORBIDDEN

    def test_anonymous_can_view_public_notebook(self, client):
        response = client.get("/notebooks/susan/campaign-notes/session-log")
        assert response.status_code == HTTPStatus.OK
        assert "Public campaign notes" in response.content.decode()

    @UserMixin.as_user("susan")
    def test_owner_can_edit_public_notebook(self, client):
        page = self.susans_notebook.get_page(path="session-log")
        response = client.post("/notebooks/susan/campaign-notes/session-log", {
            "filename": "session-log",
            "content": "# Session Log\n\nEdited by Susan.",
        })
        assert response.status_code == HTTPStatus.FOUND
        page.refresh_from_db()
        assert page.latest_version.content.data == b"# Session Log\n\nEdited by Susan."
        assert page.latest_version.created_by == self.susan

    @UserMixin.as_user("mary")
    def test_editor_can_edit_public_notebook(self, client):
        page = self.susans_notebook.get_page(path="session-log")
        response = client.post("/notebooks/susan/campaign-notes/session-log", {
            "filename": "session-log",
            "content": "# Session Log\n\nEdited by Mary.",
        })
        assert response.status_code == HTTPStatus.FOUND
        page.refresh_from_db()
        assert page.latest_version.content.data == b"# Session Log\n\nEdited by Mary."
        assert page.latest_version.created_by == self.mary

    @UserMixin.as_user("wendy")
    def test_viewer_cannot_edit_public_notebook(self, client):
        page = self.susans_notebook.get_page(path="session-log")
        initial_data = page.latest_version.content.data
        response = client.post("/notebooks/susan/campaign-notes/session-log", {
            "filename": "session-log",
            "content": "# Hacked",
        })
        assert response.status_code == HTTPStatus.FORBIDDEN
        page.refresh_from_db()
        assert page.latest_version.content.data == initial_data

    def test_anonymous_cannot_edit_public_notebook(self, client):
        page = self.susans_notebook.get_page(path="session-log")
        initial_data = page.latest_version.content.data
        response = client.post("/notebooks/susan/campaign-notes/session-log", {
            "filename": "session-log",
            "content": "# Hacked",
        })
        assert response.status_code == HTTPStatus.UNAUTHORIZED
        page.refresh_from_db()
        assert page.latest_version.content.data == initial_data

    @UserMixin.as_user("susan")
    def test_owner_can_create_page_in_public_notebook(self, client):
        response = client.post("/notebooks/susan/campaign-notes/npcs", {
            "filename": "NPCs",
            "content": "# NPCs\n\nThe innkeeper.",
        })
        assert response.status_code == HTTPStatus.FOUND
        page = self.susans_notebook.get_page(path="npcs")
        assert page.latest_version.created_by == self.susan

    @UserMixin.as_user("mary")
    def test_editor_can_create_page_in_public_notebook(self, client):
        response = client.post("/notebooks/susan/campaign-notes/quests", {
            "filename": "Quests",
            "content": "# Quests\n\nFind the artifact.",
        })
        assert response.status_code == HTTPStatus.FOUND
        page = self.susans_notebook.get_page(path="quests")
        assert page.latest_version.created_by == self.mary

    @UserMixin.as_user("wendy")
    def test_viewer_cannot_create_page_in_public_notebook(self, client):
        initial_count = Page.objects.filter(wiki=self.susans_notebook).count()
        response = client.post("/notebooks/susan/campaign-notes/locations", {
            "filename": "Locations",
            "content": "# Locations",
        })
        assert response.status_code == HTTPStatus.FORBIDDEN
        assert Page.objects.filter(wiki=self.susans_notebook).count() == initial_count

    @UserMixin.as_user("hugh")
    def test_non_collaborator_cannot_create_page_in_public_notebook(self, client):
        initial_count = Page.objects.filter(wiki=self.susans_notebook).count()
        response = client.post("/notebooks/susan/campaign-notes/locations", {
            "filename": "Locations",
            "content": "# Locations",
        })
        assert response.status_code == HTTPStatus.FORBIDDEN
        assert Page.objects.filter(wiki=self.susans_notebook).count() == initial_count

    def test_anonymous_cannot_create_page_in_public_notebook(self, client):
        initial_count = Page.objects.filter(wiki=self.susans_notebook).count()
        response = client.post("/notebooks/susan/campaign-notes/locations", {
            "filename": "Locations",
            "content": "# Locations",
        })
        assert response.status_code == HTTPStatus.UNAUTHORIZED
        assert Page.objects.filter(wiki=self.susans_notebook).count() == initial_count


@pytest.mark.django_db
class TestNotebookPageDeleteView(NotebookMixin):
    @UserMixin.as_user("wendy")
    def test_delete_shows_confirmation(self, client):
        page = self.wendys_notebook.get_page(path="notes")
        response = client.post("/notebooks/delete", {
            "notebook": self.wendys_notebook.pk,
            "page": page.pk,
        })
        assert response.status_code == HTTPStatus.OK
        content = response.content.decode()
        self.assert_confirmation_form_present(content, "/notebooks/delete")
        assert "notes" in content.lower()

    @UserMixin.as_user("wendy")
    def test_owner_can_delete_page(self, client):
        page = self.wendys_notebook.get_page(path="heroes/theron")
        assert page.deleted_at is None
        response = client.post("/notebooks/delete", {
            "notebook": self.wendys_notebook.pk,
            "page": page.pk,
            "confirmed": "true",
        })
        assert response.status_code == HTTPStatus.SEE_OTHER
        assert response.url == "/notebooks/wendy/heros-legendes/heroes/"
        page.refresh_from_db()
        assert page.deleted_at is not None

    @UserMixin.as_user("susan")
    def test_editor_can_delete_page(self, client):
        page = self.wendys_notebook.get_page(path="notes")
        response = client.post("/notebooks/delete", {
            "notebook": self.wendys_notebook.pk,
            "page": page.pk,
            "confirmed": "true",
        })
        assert response.status_code == HTTPStatus.SEE_OTHER
        page.refresh_from_db()
        assert page.deleted_at is not None

    @UserMixin.as_user("mary")
    def test_viewer_cannot_delete_page(self, client):
        page = self.wendys_notebook.get_page(path="notes")
        response = client.post("/notebooks/delete", {
            "notebook": self.wendys_notebook.pk,
            "page": page.pk,
            "confirmed": "true",
        })
        assert response.status_code == HTTPStatus.FORBIDDEN
        page.refresh_from_db()
        assert page.deleted_at is None

    @UserMixin.as_user("hugh")
    def test_non_collaborator_cannot_delete_page(self, client):
        page = self.wendys_notebook.get_page(path="notes")
        response = client.post("/notebooks/delete", {
            "notebook": self.wendys_notebook.pk,
            "page": page.pk,
            "confirmed": "true",
        })
        assert response.status_code == HTTPStatus.FORBIDDEN
        page.refresh_from_db()
        assert page.deleted_at is None

    def test_anonymous_cannot_delete_page(self, client):
        page = self.wendys_notebook.get_page(path="notes")
        response = client.post("/notebooks/delete", {
            "notebook": self.wendys_notebook.pk,
            "page": page.pk,
            "confirmed": "true",
        })
        assert response.status_code == HTTPStatus.UNAUTHORIZED
        page.refresh_from_db()
        assert page.deleted_at is None


class TestNotebookPageRestoreView(NotebookMixin):
    @UserMixin.as_user("wendy")
    def test_owner_can_restore_page(self, client):
        response = client.post("/notebooks/restore", {
            "notebook": self.wendys_notebook.pk,
            "page": self.deleted_page.pk,
        })
        assert response.status_code == HTTPStatus.FOUND
        assert response.url == "/notebooks/wendy/heros-legendes/"
        self.deleted_page.refresh_from_db()
        assert self.deleted_page.deleted_at is None

    @UserMixin.as_user("susan")
    def test_editor_can_restore_page(self, client):
        response = client.post("/notebooks/restore", {
            "notebook": self.wendys_notebook.pk,
            "page": self.deleted_page.pk,
        })
        assert response.status_code == HTTPStatus.FOUND
        self.deleted_page.refresh_from_db()
        assert self.deleted_page.deleted_at is None

    @UserMixin.as_user("mary")
    def test_viewer_cannot_restore_page(self, client):
        response = client.post("/notebooks/restore", {
            "notebook": self.wendys_notebook.pk,
            "page": self.deleted_page.pk,
        })
        assert response.status_code == HTTPStatus.FORBIDDEN
        self.deleted_page.refresh_from_db()
        assert self.deleted_page.deleted_at is not None

    @UserMixin.as_user("hugh")
    def test_non_collaborator_cannot_restore_page(self, client):
        response = client.post("/notebooks/restore", {
            "notebook": self.wendys_notebook.pk,
            "page": self.deleted_page.pk,
        })
        assert response.status_code == HTTPStatus.FORBIDDEN
        self.deleted_page.refresh_from_db()
        assert self.deleted_page.deleted_at is not None

    def test_anonymous_cannot_restore_page(self, client):
        response = client.post("/notebooks/restore", {
            "notebook": self.wendys_notebook.pk,
            "page": self.deleted_page.pk,
        })
        assert response.status_code == HTTPStatus.UNAUTHORIZED
        self.deleted_page.refresh_from_db()
        assert self.deleted_page.deleted_at is not None

