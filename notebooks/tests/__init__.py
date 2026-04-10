import html
from datetime import timedelta

import pytest
from django.utils import timezone

from notebooks.models import Notebook, NotebookPermission
from users.tests import UserMixin
from wikis.models import Page, Version

PNG_BYTES = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01"


class NotebookMixin(UserMixin):
    # Permission matrix:
    #   wendy's notebook (private): susan=editor, mary=viewer
    #   wendy's secret (private):   unshared
    #   mary's notebook (internal): wendy=editor, susan=viewer
    #   susan's notebook (public):  mary=editor, wendy=viewer
    #   hugh has no permissions

    @pytest.fixture(autouse=True)
    def setup_notebooks(self, db, setup_users):
        self.wendys_notebook = Notebook.objects.create(
            name="Héros & Légendes",
            owner=self.wendy,
        )
        self.wendys_secret = Notebook.objects.create(
            name="Wendy's Secret",
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
            visibility=Notebook.Visibility.INTERNAL,
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

        self.wendys_heroes_index_text = "Updated heroes introduction."
        heroes_index = Page.objects.create(wiki=self.wendys_notebook)
        heroes_index.update(
            filename="heroes/index.md",
            mime_type="text/markdown",
            data=b"# Heroes\n\nMeet the heroes of this campaign.",
            created_by=self.wendy,
        )
        heroes_index.update(
            filename="heroes/index.md",
            mime_type="text/markdown",
            data=b"# Heroes\n\n" + self.wendys_heroes_index_text.encode(),
            created_by=self.susan,
        )

        villains_page = Page.objects.create(wiki=self.wendys_notebook)
        villains_page.update(
            filename="villains/necromancer.md",
            mime_type="text/markdown",
            data=b"# The Necromancer\n\nA dark wizard.",
            created_by=self.wendy,
        )

        region_page = Page.objects.create(wiki=self.wendys_notebook)
        region_page.update(
            filename="World Regions/Northern Kingdoms/Frosthold.md",
            mime_type="text/markdown",
            data=b"# Frosthold\n\nA fortress city in the frozen north.",
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

        # backdate fixture data for "since..." tests
        past = timezone.now() - timedelta(seconds=1)
        Version.objects.update(created_at=past)
        Page.objects.filter(deleted_at__isnull=False).update(deleted_at=past)

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
        assert 'href="/notebooks/settings/' in content

    def assert_cannot_manage(self, content):
        assert 'href="/notebooks/settings/' not in content

    def assert_edit_controls_present(self, content):
        normalised = " ".join(content.split())
        assert (
            '<input type="hidden" name="edit"> <button type="submit">Edit</button>'
            in normalised
        )
        assert '/notebooks/deleted/' in content
        assert '/notebooks/create-page/' in content

    def assert_edit_controls_absent(self, content):
        normalised = " ".join(content.split())
        assert (
            '<input type="hidden" name="edit"> <button type="submit">Edit</button>'
            not in normalised
        )
        assert 'href="/notebooks/restore?page=' not in content
        assert '/notebooks/create-page/' not in content
        assert 'action="/notebooks/delete-page"' not in content

    def assert_page_edit_link_present(self, content):
        normalised = " ".join(content.split())
        assert (
            '<input type="hidden" name="edit"> <button type="submit">Edit</button>'
            in normalised
        )

    def assert_page_edit_link_absent(self, content):
        normalised = " ".join(content.split())
        assert (
            '<input type="hidden" name="edit"> <button type="submit">Edit</button>'
            not in normalised
        )

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
        assert 'name="confirm"' in content

    def assert_notebook_header_present(self, content, notebook):
        assert '<div class="header primary notebook">' in content
        assert f'<h1>{html.escape(notebook.name)}</h1>' in content

    def assert_edit_page_form_present(self, content):
        assert "<form" in content
        assert "<textarea" in content
        assert 'type="file"' in content
        assert 'type="submit"' in content
        assert 'action="/notebooks/delete-page"' in content

    def assert_versions_present(self, content, param_name, page, current=None):
        assert f'name="{param_name}"' in content
        normalised = " ".join(content.split())
        if current is None:
            current = page.latest_version
        for version in page.history():
            option_value = f'<option value="{version.number}"'
            assert option_value in normalised
            if version == current:
                assert f'<option value="{version.number}" selected>' in normalised

    def assert_versions_absent(self, content, param_name):
        assert param_name not in content
