from http import HTTPStatus
from textwrap import dedent

import pytest

from notebooks.models import Notebook
from users.tests import UserMixin
from wikis.models import Page

from . import NotebookMixin

PNG_BYTES = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01"


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
        assert 'action="/notebooks/create"' in content
        assert 'name="name"' in content

    @UserMixin.as_user("wendy")
    def test_profile_form_submits_to_create_view(self, client):
        response = client.post("/notebooks/create", {"name": "New Notebook"})
        assert response.status_code == HTTPStatus.OK
        content = response.content.decode()
        assert 'value="New Notebook"' in content
        assert 'name="visibility"' in content
        assert not Notebook.objects.filter(name="New Notebook").exists()

    @UserMixin.as_user("wendy")
    def test_other_profile_does_not_show_notebooks(self, client):
        response = client.get("/profile/susan/")
        content = response.content.decode()
        assert "Campaign Notes" not in content


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
            '<a href="./notes">Notes</a>'
            in content
        )

    @UserMixin.as_user("wendy")
    def test_view_page_shows_version_select_with_single_version(self, client):
        response = client.get("/notebooks/wendy/heros-legendes/notes")
        content = response.content.decode()
        self.assert_page_heading_present(content, "Notes")
        page = self.wendys_notebook.get_page(path="notes")
        self.assert_versions_present(content, "version", page)

    @UserMixin.as_user("wendy")
    def test_view_page_shows_version_select_in_form(self, client):
        response = client.get("/notebooks/wendy/heros-legendes/session-one")
        content = response.content.decode()
        self.assert_notebook_name_present(content, self.wendys_notebook)
        self.assert_page_heading_present(content, "Session One")
        self.assert_versions_present(
            content,
            "version",
            self.wendys_notebook.get_page(path="session-one"),
        )

    @UserMixin.as_user("wendy")
    def test_view_old_version(self, client):
        response = client.get("/notebooks/wendy/heros-legendes/session-one?version=1")
        content = response.content.decode()
        assert "First draft" in content
        assert "Version 1 of" in content
        page = self.wendys_notebook.get_page(path="session-one")
        self.assert_versions_present(
            content,
            "version",
            page,
            current=page.version_set.get(number=1),
        )

    @UserMixin.as_user("wendy")
    def test_view_invalid_version_returns_404(self, client):
        response = client.get("/notebooks/wendy/heros-legendes/session-one?version=99")
        assert response.status_code == HTTPStatus.NOT_FOUND

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

    @UserMixin.as_user("mary")
    def test_owner_can_view_internal_restricted_notebook(self, client):
        response = client.get("/notebooks/mary/world-lore/history")
        assert response.status_code == HTTPStatus.OK
        assert "The world began" in response.content.decode()

    @UserMixin.as_user("wendy")
    def test_editor_can_view_internal_restricted_notebook(self, client):
        response = client.get("/notebooks/mary/world-lore/history")
        assert response.status_code == HTTPStatus.OK
        assert "The world began" in response.content.decode()

    @UserMixin.as_user("susan")
    def test_viewer_can_view_internal_restricted_notebook(self, client):
        response = client.get("/notebooks/mary/world-lore/history")
        assert response.status_code == HTTPStatus.OK
        assert "The world began" in response.content.decode()

    @UserMixin.as_user("hugh")
    def test_non_collaborator_can_view_internal_restricted_notebook(self, client):
        response = client.get("/notebooks/mary/world-lore/history")
        assert response.status_code == HTTPStatus.OK

    def test_anonymous_cannot_view_internal_restricted_notebook(self, client):
        response = client.get("/notebooks/mary/world-lore/history")
        assert response.status_code == HTTPStatus.UNAUTHORIZED
        self.assert_notebook_name_absent(
            response.content.decode(),
            self.marys_notebook,
        )

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

    def test_anonymous_can_view_public_notebook(self, client):
        response = client.get("/notebooks/susan/campaign-notes/session-log")
        assert response.status_code == HTTPStatus.OK
        assert "Public campaign notes" in response.content.decode()


@pytest.mark.django_db
class TestNotebookPageEditView(NotebookMixin):
    @UserMixin.as_user("wendy")
    def test_owner_can_see_edit_form(self, client):
        response = client.get("/notebooks/wendy/heros-legendes/notes?edit")
        assert response.status_code == HTTPStatus.OK
        content = response.content.decode()
        self.assert_edit_page_form_present(content)
        assert "# Notes" in content
        assert 'name="filename" value="notes"' in content

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
        response = client.get("/notebooks/wendy/heros-legendes/notes?edit")
        assert response.status_code == HTTPStatus.UNAUTHORIZED
        assert "Access denied" in response.content.decode()

    @UserMixin.as_user("wendy")
    def test_edit_binary_shows_form(self, client):
        response = client.get("/notebooks/wendy/heros-legendes/heroes/shield.png?edit")
        assert response.status_code == HTTPStatus.OK
        content = response.content.decode()
        self.assert_edit_page_form_present(content)

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
        assert page.latest_version.content.data == b"# Updated Notes\n\nNew content.\n"

    @UserMixin.as_user("wendy")
    def test_editing_sanitises_crlf_line_endings(self, client):
        response = client.post("/notebooks/wendy/heros-legendes/test-file", {
            # browsers send CRLF in textarea content per HTML spec
            "filename": "test-file",
            "content": "First line\r\nSecond line\r\nThird line",
        })
        assert response.status_code == HTTPStatus.FOUND
        page = self.wendys_notebook.get_page(path="test-file")
        assert (
            page.latest_version.content.data
            == b"First line\nSecond line\nThird line\n"
        )

    @UserMixin.as_user("susan")
    def test_editor_can_edit_page(self, client):
        page = self.wendys_notebook.get_page(path="notes")
        response = client.post("/notebooks/wendy/heros-legendes/notes", {
            "filename": "notes",
            "content": "# Editor Update",
        })
        assert response.status_code == HTTPStatus.FOUND
        page.refresh_from_db()
        assert page.latest_version.content.data == b"# Editor Update\n"
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
        page = self.wendys_notebook.get_page(path="notes")
        initial_data = page.latest_version.content.data
        response = client.post("/notebooks/wendy/heros-legendes/notes", {
            "filename": "notes",
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
        assert page.latest_version.content.data == b"# Campaign Notes\n\nRenamed.\n"

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

    @UserMixin.as_user("wendy")
    def test_unresolved_path_for_owner(self, client):
        response = client.get("/notebooks/wendy/heros-legendes/rumours")
        assert response.status_code == HTTPStatus.NOT_FOUND
        content = response.content.decode()
        self.assert_create_form_present(content)
        assert 'name="filename" value="Rumours"' in content

    @UserMixin.as_user("susan")
    def test_unresolved_path_for_editor(self, client):
        response = client.get("/notebooks/wendy/heros-legendes/rumours")
        assert response.status_code == HTTPStatus.NOT_FOUND
        content = response.content.decode()
        self.assert_create_form_present(content)
        assert 'name="filename" value="Rumours"' in content

    @UserMixin.as_user("mary")
    def test_unresolved_path_for_viewer(self, client):
        response = client.get("/notebooks/wendy/heros-legendes/rumours")
        assert response.status_code == HTTPStatus.NOT_FOUND
        self.assert_create_form_absent(response.content.decode())

    @UserMixin.as_user("hugh")
    def test_unresolved_path_for_non_collaborator(self, client):
        response = client.get("/notebooks/wendy/heros-legendes/rumours")
        assert response.status_code == HTTPStatus.FORBIDDEN
        self.assert_create_form_absent(response.content.decode())

    def test_unresolved_path_for_anonymous(self, client):
        response = client.get("/notebooks/wendy/heros-legendes/rumours")
        assert response.status_code == HTTPStatus.UNAUTHORIZED
        assert "Access denied" in response.content.decode()

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
        assert page.latest_version.content.data == b"# Dragon\n\nA fearsome creature.\n"
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
    def test_owner_can_create_page(self, client):
        response = client.post("/notebooks/wendy/heros-legendes/locations/tavern", {
            "filename": "Locations/Tavern",
            "content": "# The Tavern",
        })
        assert response.status_code == HTTPStatus.FOUND
        page = self.wendys_notebook.get_page(path="locations/tavern")
        assert page.latest_version.created_by == self.wendy

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
        initial_count = Page.objects.filter(wiki=self.wendys_notebook).count()
        response = client.post("/notebooks/wendy/heros-legendes/locations/tavern", {
            "filename": "Locations/Tavern",
            "content": "# The Tavern",
        })
        assert response.status_code == HTTPStatus.UNAUTHORIZED
        assert Page.objects.filter(wiki=self.wendys_notebook).count() == initial_count

    @UserMixin.as_user("wendy")
    def test_editor_can_edit_internal_restricted_notebook(self, client):
        page = self.marys_notebook.get_page(path="history")
        response = client.post("/notebooks/mary/world-lore/history", {
            "filename": "history",
            "content": "# History\n\nEdited by Wendy.",
        })
        assert response.status_code == HTTPStatus.FOUND
        page.refresh_from_db()
        assert page.latest_version.content.data == b"# History\n\nEdited by Wendy.\n"
        assert page.latest_version.created_by == self.wendy

    @UserMixin.as_user("wendy")
    def test_editor_can_create_page_in_internal_restricted_notebook(self, client):
        response = client.post("/notebooks/mary/world-lore/geography", {
            "filename": "Geography",
            "content": "# Geography\n\nMountains and rivers.",
        })
        assert response.status_code == HTTPStatus.FOUND
        page = self.marys_notebook.get_page(path="geography")
        assert page.latest_version.created_by == self.wendy

    @UserMixin.as_user("hugh")
    def test_non_collaborator_cannot_edit_internal_restricted_notebook(self, client):
        response = client.post("/notebooks/mary/world-lore/history", {
            "filename": "history",
            "content": "# Hacked",
        })
        assert response.status_code == HTTPStatus.FORBIDDEN

    @UserMixin.as_user("mary")
    def test_owner_can_edit_internal_restricted_notebook(self, client):
        page = self.marys_notebook.get_page(path="history")
        response = client.post("/notebooks/mary/world-lore/history", {
            "filename": "history",
            "content": "# History\n\nEdited by Mary.",
        })
        assert response.status_code == HTTPStatus.FOUND
        page.refresh_from_db()
        assert page.latest_version.content.data == b"# History\n\nEdited by Mary.\n"
        assert page.latest_version.created_by == self.mary

    @UserMixin.as_user("susan")
    def test_viewer_cannot_edit_internal_restricted_notebook(self, client):
        page = self.marys_notebook.get_page(path="history")
        initial_data = page.latest_version.content.data
        response = client.post("/notebooks/mary/world-lore/history", {
            "filename": "history",
            "content": "# Hacked",
        })
        assert response.status_code == HTTPStatus.FORBIDDEN
        page.refresh_from_db()
        assert page.latest_version.content.data == initial_data

    def test_anonymous_cannot_edit_internal_restricted_notebook(self, client):
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
    def test_owner_can_create_page_in_internal_restricted_notebook(self, client):
        response = client.post("/notebooks/mary/world-lore/cultures", {
            "filename": "Cultures",
            "content": "# Cultures\n\nThe elves and dwarves.",
        })
        assert response.status_code == HTTPStatus.FOUND
        page = self.marys_notebook.get_page(path="cultures")
        assert page.latest_version.created_by == self.mary

    @UserMixin.as_user("susan")
    def test_viewer_cannot_create_page_in_internal_restricted_notebook(self, client):
        initial_count = Page.objects.filter(wiki=self.marys_notebook).count()
        response = client.post("/notebooks/mary/world-lore/religions", {
            "filename": "Religions",
            "content": "# Religions",
        })
        assert response.status_code == HTTPStatus.FORBIDDEN
        assert Page.objects.filter(wiki=self.marys_notebook).count() == initial_count

    @UserMixin.as_user("hugh")
    def test_non_collaborator_cannot_create_page_in_internal_restricted_notebook(self, client):  # noqa: E501
        initial_count = Page.objects.filter(wiki=self.marys_notebook).count()
        response = client.post("/notebooks/mary/world-lore/religions", {
            "filename": "Religions",
            "content": "# Religions",
        })
        assert response.status_code == HTTPStatus.FORBIDDEN
        assert Page.objects.filter(wiki=self.marys_notebook).count() == initial_count

    def test_anonymous_cannot_create_page_in_internal_restricted_notebook(self, client):
        initial_count = Page.objects.filter(wiki=self.marys_notebook).count()
        response = client.post("/notebooks/mary/world-lore/religions", {
            "filename": "Religions",
            "content": "# Religions",
        })
        assert response.status_code == HTTPStatus.UNAUTHORIZED
        assert Page.objects.filter(wiki=self.marys_notebook).count() == initial_count

    @UserMixin.as_user("hugh")
    def test_non_collaborator_cannot_edit_public_notebook(self, client):
        response = client.post("/notebooks/susan/campaign-notes/session-log", {
            "filename": "session-log",
            "content": "# Hacked",
        })
        assert response.status_code == HTTPStatus.FORBIDDEN

    @UserMixin.as_user("susan")
    def test_owner_can_edit_public_notebook(self, client):
        page = self.susans_notebook.get_page(path="session-log")
        response = client.post("/notebooks/susan/campaign-notes/session-log", {
            "filename": "session-log",
            "content": "# Session Log\n\nEdited by Susan.",
        })
        assert response.status_code == HTTPStatus.FOUND
        page.refresh_from_db()
        assert (
            page.latest_version.content.data == b"# Session Log\n\nEdited by Susan.\n"
        )
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
        assert (
            page.latest_version.content.data == b"# Session Log\n\nEdited by Mary.\n"
        )
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

    @UserMixin.as_user("wendy")
    def test_edit_form_includes_previous_hash(self, client):
        page = self.wendys_notebook.get_page(path="notes")
        expected_hash = page.latest_version.content.hash
        response = client.get("/notebooks/wendy/heros-legendes/notes?edit")
        assert response.status_code == HTTPStatus.OK
        content = response.content.decode()
        assert f'name="previous_hash" value="{expected_hash}"' in content

    @UserMixin.as_user("wendy")
    def test_saving_with_matching_hash_updates_directly(self, client):
        page = self.wendys_notebook.get_page(path="notes")
        page.update(
            filename="notes.md",
            mime_type="text/markdown",
            data=b"# Notes\n\nOriginal content.\n",
            created_by=self.wendy,
        )
        current_hash = page.latest_version.content.hash
        initial_version_count = page.version_set.count()
        response = client.post("/notebooks/wendy/heros-legendes/notes", {
            "filename": "notes",
            "content": "# Notes\n\nUpdated content.",
            "previous_hash": current_hash,
        })
        assert response.status_code == HTTPStatus.FOUND
        page.refresh_from_db()
        assert page.version_set.count() == initial_version_count + 1
        assert page.latest_version.content.data == b"# Notes\n\nUpdated content.\n"

    @UserMixin.as_user("wendy")
    def test_saving_with_previous_hash_triggers_merge(self, client):
        page = self.wendys_notebook.get_page(path="notes")
        page.update(
            filename="notes.md",
            mime_type="text/markdown",
            data=dedent("""\
                # Notes

                - Ale: 4cp
                - Bread: 2cp
            """).encode(),
            created_by=self.wendy,
        )
        base_hash = page.latest_version.content.hash
        page.update(
            filename="notes.md",
            mime_type="text/markdown",
            data=dedent("""\
                # Notes

                - Ale: 5cp
                - Bread: 2cp
            """).encode(),
            created_by=self.susan,
        )
        response = client.post("/notebooks/wendy/heros-legendes/notes", {
            "filename": "notes",
            "content": dedent("""\
                # Notes

                - Ale: 4cp
                - Bread: 3cp
            """),
            "previous_hash": base_hash,
        })
        assert response.status_code == HTTPStatus.FOUND
        page.refresh_from_db()
        merged = page.latest_version.content.data.decode()
        assert "Ale: 5cp" in merged
        assert "Bread: 3cp" in merged

    @UserMixin.as_user("wendy")
    def test_saving_with_unknown_hash_replaces_content(self, client):
        page = self.wendys_notebook.get_page(path="notes")
        page.update(
            filename="notes.md",
            mime_type="text/markdown",
            data=b"# Notes\n\nServer content.\n",
            created_by=self.wendy,
        )
        initial_version_count = page.version_set.count()
        response = client.post("/notebooks/wendy/heros-legendes/notes", {
            "filename": "notes",
            "content": "# Notes\n\nReplacement content.",
            "previous_hash": "nonexistent-hash-abc123",
        })
        assert response.status_code == HTTPStatus.FOUND
        page.refresh_from_db()
        assert page.version_set.count() == initial_version_count + 1
        assert page.latest_version.content.data == b"# Notes\n\nReplacement content.\n"


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
    def test_owner_sees_internal_restricted_notebook_index(self, client):
        response = client.get("/notebooks/mary/world-lore/regions/")
        content = response.content.decode()
        assert response.status_code == HTTPStatus.OK
        self.assert_notebook_name_present(content, self.marys_notebook)
        assert self.marys_regions_index_text in content
        self.assert_edit_controls_present(content)

    @UserMixin.as_user("wendy")
    def test_editor_sees_internal_restricted_notebook_index(self, client):
        response = client.get("/notebooks/mary/world-lore/regions/")
        content = response.content.decode()
        assert response.status_code == HTTPStatus.OK
        self.assert_notebook_name_present(content, self.marys_notebook)
        assert self.marys_regions_index_text in content
        self.assert_edit_controls_present(content)

    @UserMixin.as_user("susan")
    def test_viewer_sees_internal_restricted_notebook_index(self, client):
        response = client.get("/notebooks/mary/world-lore/regions/")
        content = response.content.decode()
        assert response.status_code == HTTPStatus.OK
        self.assert_notebook_name_present(content, self.marys_notebook)
        assert self.marys_regions_index_text in content
        self.assert_edit_controls_absent(content)

    @UserMixin.as_user("hugh")
    def test_non_collaborator_sees_internal_restricted_notebook_index(self, client):
        response = client.get("/notebooks/mary/world-lore/regions/")
        content = response.content.decode()
        assert response.status_code == HTTPStatus.OK
        self.assert_notebook_name_present(content, self.marys_notebook)
        assert self.marys_regions_index_text in content
        self.assert_edit_controls_absent(content)

    def test_anonymous_cannot_see_internal_restricted_notebook_index(self, client):
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

    @UserMixin.as_user("susan")
    def test_index_page_shows_version_select_with_single_version(self, client):
        response = client.get("/notebooks/susan/campaign-notes/npcs/")
        content = response.content.decode()
        assert self.susans_npcs_index_text in content
        self.assert_versions_present(
            content,
            "index_version",
            self.susans_notebook.get_page(path="npcs/index"),
        )

    @UserMixin.as_user("wendy")
    def test_index_page_shows_version_select_in_form(self, client):
        response = client.get("/notebooks/wendy/heros-legendes/heroes/")
        content = response.content.decode()
        assert self.wendys_heroes_index_text in content
        self.assert_versions_present(
            content,
            "index_version",
            self.wendys_notebook.get_page(path="heroes/index"),
        )

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
        normalised = " ".join(content.split())
        assert (
            '<a href="/notebooks/wendy/heros-legendes/villains/index?edit"'
            ' class="button">Create</a>' in normalised
        )
        assert "Edit index" not in content

    @UserMixin.as_user("susan")
    def test_editor_sees_create_index_link(self, client):
        response = client.get("/notebooks/wendy/heros-legendes/villains/")
        assert response.status_code == HTTPStatus.OK
        content = response.content.decode()
        normalised = " ".join(content.split())
        assert (
            '<a href="/notebooks/wendy/heros-legendes/villains/index?edit"'
            ' class="button">Create</a>' in normalised
        )

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
