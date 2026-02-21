from datetime import timedelta

import pytest
from django.core.exceptions import ValidationError
from django.utils import timezone

from users.models import get_sentinel_user
from users.tests import UserMixin
from wikis.models import Content, Page, Wiki


class WikiMixin(UserMixin):
    @pytest.fixture(autouse=True)
    def setup_wiki(self, db, setup_users):
        self.wiki = Wiki.objects.create()
        self.page = Page.objects.create(wiki=self.wiki)
        self.version = self.page.update(
            filename="document.txt",
            mime_type="text/plain",
            data=b"Test content",
            created_by=self.wendy,
        )
        self.page_with_shared_content = Page.objects.create(wiki=self.wiki)
        self.page_with_shared_content.update(
            filename="shared.txt",
            mime_type="text/plain",
            data=b"Test content",
            created_by=self.wendy,
        )
        self.page_with_history = Page.objects.create(wiki=self.wiki)
        for data in [b"First revision", b"Second revision", b"Third revision"]:
            self.page_with_history.update(
                filename="history.txt",
                mime_type="text/plain",
                data=data,
                created_by=self.wendy,
            )
        self.markdown_pages = []
        for filename in [
            "Rules/Combat.md",
            "Rules/Status/Exhaustion.md",
            "Rules/Status/Conditions/Blinded.md",
            "Characters/Theron Blackwood.md",
        ]:
            page = Page.objects.create(wiki=self.wiki)
            page.update(
                filename=filename,
                mime_type="text/markdown",
                data=f"Content of {filename}".encode(),
                created_by=self.wendy,
            )
            self.markdown_pages.append(page)


@pytest.mark.django_db
class TestContent(WikiMixin):
    def test_content_primary_key_is_hash_of_data(self):
        assert self.version.content.pk == self.version.content.hash
        assert self.version.content.hash == (
            "9d9595c5d94fb65b824f56e9999527dba9542481580d69feb89056aabaa0aa87"
        )

    def test_content_is_shared_between_wikis(self):
        count_before = Content.objects.count()
        wiki_b = Wiki.objects.create()
        page_b = Page.objects.create(wiki=wiki_b)
        page_b.update(
            filename="doc.txt",
            mime_type="text/plain",
            data=b"Test content",
            created_by=self.wendy,
        )
        assert Content.objects.count() == count_before

    def test_content_delete_raises_error(self):
        orphaned = Content.objects.create(hash="abc123", data=b"orphaned")
        with pytest.raises(RuntimeError):
            orphaned.delete()


@pytest.mark.django_db
class TestVersion(WikiMixin):
    def test_validate_filename_rejects_trailing_slash(self):
        self.version.filename = "invalid/"
        with pytest.raises(ValidationError):
            self.version.validate_filename()

    def test_validate_filename_rejects_parent_traversal(self):
        self.version.filename = "foo/../bar.txt"
        with pytest.raises(ValidationError):
            self.version.validate_filename()

    @pytest.mark.parametrize("char", list("[]#^|\\:*\"<>?"))
    def test_validate_filename_rejects_forbidden_characters(self, char):
        self.version.filename = f"file{char}name.txt"
        with pytest.raises(ValidationError):
            self.version.validate_filename()

    def test_validate_filename_allows_unicode_and_spaces(self):
        self.version.filename = "Héros & Légendes/Épée du Crépuscule.md"
        self.version.validate_filename()

    def test_generate_path_transliterates_and_lowercases(self):
        self.version.filename = "Héros & Légendes/Épée du Crépuscule.md"
        assert self.version.generate_path() == "heros-legendes/epee-du-crepuscule"

    def test_generate_path_preserves_non_md_extensions(self):
        self.version.filename = "Maps/World Map.png"
        assert self.version.generate_path() == "maps/world-map.png"

    def test_duplicate_paths_rejected_within_wiki(self):
        page_b = Page.objects.create(wiki=self.wiki)
        with pytest.raises(ValidationError):
            page_b.update(
                filename="Document.txt",
                mime_type="text/plain",
                data=b"Other content",
                created_by=self.wendy,
            )

    def test_same_path_allowed_in_different_wikis(self):
        wiki_b = Wiki.objects.create()
        page_b = Page.objects.create(wiki=wiki_b)
        page_b.update(
            filename="document.txt",
            mime_type="text/plain",
            data=b"Test content",
            created_by=self.wendy,
        )
        assert page_b.version_set.first().path == "document.txt"

    def test_render_markdown_returns_html(self):
        page = Page.objects.create(wiki=self.wiki)
        version = page.update(
            filename="test.md",
            mime_type="text/markdown",
            data=b"# Heading",
            created_by=self.wendy,
        )
        assert "<h1>Heading</h1>" in version.render()

    def test_render_non_markdown_returns_bytes(self):
        assert self.version.render() == b"Test content"

    def test_display_name_markdown(self):
        page = Page.objects.create(wiki=self.wiki)
        version = page.update(
            filename="Guides/Combat Tactics.md",
            mime_type="text/markdown",
            data=b"# Combat Tactics",
            created_by=self.wendy,
        )
        assert version.display_name == "Combat Tactics"

    def test_display_name_markdown_uppercase(self):
        self.version.filename = "Notes/Session Log.MD"
        assert self.version.display_name == "Session Log"

    def test_display_name_attachment(self):
        self.version.filename = "Maps/World Map.png"
        assert self.version.display_name == "World Map.png"


@pytest.mark.django_db
class TestPage(WikiMixin):
    def test_update(self):
        self.page.update(
            filename="renamed.txt",
            mime_type="text/plain",
            data=b"Version 2",
            created_by=self.wendy,
        )
        versions = list(self.page.version_set.order_by("number"))
        assert len(versions) == 2
        assert versions[0].number == 1
        assert versions[0].path == "document.txt"
        assert versions[1].number == 2
        assert versions[1].path == "renamed.txt"

    def test_update_with_no_changes_does_not_create_version(self):
        self.page.update(
            filename="document.txt",
            mime_type="text/plain",
            data=b"Test content",
            created_by=self.wendy,
        )
        assert self.page.version_set.count() == 1

    def test_rename_with_identical_content_creates_version(self):
        count_before = Content.objects.count()
        self.page.update(
            filename="renamed.txt",
            mime_type="text/plain",
            data=b"Test content",
            created_by=self.wendy,
        )
        assert self.page.version_set.count() == 2
        assert Content.objects.count() == count_before

    def test_version_numbers_independent_per_page(self):
        page_b = Page.objects.create(wiki=self.wiki)
        page_b.update(
            filename="other.txt",
            mime_type="text/plain",
            data=b"Test content",
            created_by=self.wendy,
        )
        assert self.page.version_set.first().number == 1
        assert page_b.version_set.first().number == 1

    def test_soft_delete_sets_deleted_at(self):
        assert self.page.deleted_at is None
        self.page.soft_delete()
        assert self.page.deleted_at is not None
        assert Page.objects.filter(pk=self.page.pk).exists()

    def test_version_reassigned_to_sentinel_on_user_delete(self):
        self.wendy.delete()
        self.version.refresh_from_db()
        assert self.version.created_by == get_sentinel_user()

    def test_rename_frees_path_for_new_page(self):
        self.page.update(
            filename="renamed.txt",
            mime_type="text/plain",
            data=b"Version 2",
            created_by=self.wendy,
        )
        new_page = Page.objects.create(wiki=self.wiki)
        new_page.update(
            filename="document.txt",
            mime_type="text/plain",
            data=b"New page content",
            created_by=self.wendy,
        )
        assert new_page.version_set.first().path == "document.txt"

    def test_history_returns_versions_ordered_by_number(self):
        history = self.page_with_history.history()
        assert len(history) == 3
        assert [v.number for v in history] == [1, 2, 3]

    def test_revert_creates_new_version_with_old_content(self):
        reverted = self.page_with_history.revert(
            version_number=1, reverted_by=self.wendy
        )
        assert reverted.number == 4
        assert reverted.filename == "history.txt"
        assert reverted.content.data == b"First revision"

    def test_revert_to_current_version_does_not_create_version(self):
        reverted = self.page_with_history.revert(
            version_number=3, reverted_by=self.wendy
        )
        assert reverted.number == 3
        assert self.page_with_history.version_set.count() == 3

    def test_revert_to_nonexistent_version_raises(self):
        with pytest.raises(ValueError):
            self.page_with_history.revert(version_number=99, reverted_by=self.wendy)

    def test_delete_removes_orphaned_content(self):
        content_hash = self.page_with_history.version_set.get(number=1).content.hash
        self.page_with_history.delete()
        assert not Content.objects.filter(hash=content_hash).exists()

    def test_delete_keeps_shared_content(self):
        content_hash = self.version.content.hash
        self.page.delete()
        assert Content.objects.filter(hash=content_hash).exists()

    def test_delete_version_does_not_break_history(self):
        self.page_with_history.delete_version(2)
        assert [v.number for v in self.page_with_history.history()] == [1, 3]

    def test_delete_version_nonexistent_raises(self):
        with pytest.raises(ValueError):
            self.page_with_history.delete_version(99)

    def test_delete_version_removes_orphaned_content(self):
        content_hash = self.page_with_history.version_set.get(number=2).content.hash
        self.page_with_history.delete_version(2)
        assert not Content.objects.filter(hash=content_hash).exists()

    def test_delete_version_keeps_shared_content(self):
        content_hash = self.version.content.hash
        self.page_with_shared_content.delete_version(1)
        assert Content.objects.filter(hash=content_hash).exists()

    def test_delete_middle_version_still_increments_correctly(self):
        self.page_with_history.delete_version(2)
        new_version = self.page_with_history.update(
            filename="history.txt",
            mime_type="text/plain",
            data=b"Fourth revision",
            created_by=self.wendy,
        )
        assert new_version.number == 4

    def test_delete_only_version_removes_page(self):
        page_id = self.page.pk
        self.page.delete_version(1)
        assert not Page.objects.filter(pk=page_id).exists()


@pytest.mark.django_db
class TestWiki(WikiMixin):
    def test_get_page_returns_page_by_filename(self):
        page = self.wiki.get_page(filename="document.txt")
        assert page == self.page

    def test_get_page_returns_page_by_path(self):
        page = self.wiki.get_page(path="rules/combat")
        assert page.latest_version.filename == "Rules/Combat.md"

    def test_get_page_raises_for_nonexistent_filename(self):
        with pytest.raises(Page.DoesNotExist):
            self.wiki.get_page(filename="nonexistent.txt")

    def test_get_page_does_not_match_old_filename(self):
        self.page.update(
            filename="renamed.txt",
            mime_type="text/plain",
            data=b"Test content",
            created_by=self.wendy,
        )
        with pytest.raises(Page.DoesNotExist):
            self.wiki.get_page(filename="document.txt")

    def test_all_pages_returns_latest_versions(self):
        assert self.wiki.all_pages() == [
            self.page.latest_version,
            self.page_with_shared_content.latest_version,
            self.page_with_history.latest_version,
            self.markdown_pages[0].latest_version,
            self.markdown_pages[1].latest_version,
            self.markdown_pages[2].latest_version,
            self.markdown_pages[3].latest_version,
        ]

    def test_all_pages_excludes_deleted(self):
        self.page.soft_delete()
        assert len(self.wiki.all_pages()) == 6

    def test_deleted_pages(self):
        self.page.soft_delete()
        self.page_with_history.soft_delete()
        assert self.wiki.deleted_pages() == [
            self.page.latest_version,
            self.page_with_history.latest_version,
        ]

    def test_changes_since_returns_pages_with_new_versions(self):
        before = timezone.now()
        self.page.update(
            filename="document.txt",
            mime_type="text/plain",
            data=b"Updated content",
            created_by=self.wendy,
        )
        assert self.wiki.changes_since(before) == [self.page]

    def test_changes_since_returns_deleted_pages(self):
        before = timezone.now()
        self.page.soft_delete()
        assert self.wiki.changes_since(before) == [self.page]

    def test_changes_since_excludes_unchanged_pages(self):
        after = timezone.now()
        assert self.wiki.changes_since(after) == []

    def test_contents_in_root(self):
        contents = self.wiki.contents_in("/")
        assert [f.display_name for f in contents["files"]] == [
            "document.txt",
            "history.txt",
            "shared.txt",
        ]
        assert [(f.name, f.href) for f in contents["folders"]] == [
            ("Characters", "characters"),
            ("Rules", "rules"),
        ]

    def test_contents_in_subdirectory(self):
        contents = self.wiki.contents_in("/rules/")
        assert [f.display_name for f in contents["files"]] == ["Combat"]
        assert [(f.name, f.href) for f in contents["folders"]] == [
            ("Status", "rules/status"),
        ]

    def test_contents_in_excludes_deleted(self):
        self.wiki.get_page(filename="Rules/Combat.md").soft_delete()
        self.wiki.get_page(filename="Characters/Theron Blackwood.md").soft_delete()
        contents = self.wiki.contents_in("/")
        assert [(f.name, f.href) for f in contents["folders"]] == [("Rules", "rules")]
        contents = self.wiki.contents_in("/rules/")
        assert contents["files"] == []

    def test_purge_deleted_removes_pages_before_cutoff(self):
        self.page.deleted_at = timezone.now() - timedelta(days=30)
        self.page.save()
        cutoff = timezone.now() - timedelta(days=7)
        self.wiki.purge_deleted(cutoff)
        assert not Page.objects.filter(pk=self.page.pk).exists()

    def test_purge_deleted_removes_orphaned_content(self):
        content_hash = self.page_with_history.version_set.get(number=1).content.hash
        self.page_with_history.deleted_at = timezone.now() - timedelta(days=30)
        self.page_with_history.save()
        cutoff = timezone.now() - timedelta(days=7)
        self.wiki.purge_deleted(cutoff)
        assert not Content.objects.filter(hash=content_hash).exists()

    def test_purge_deleted_keeps_shared_content(self):
        content_hash = self.version.content.hash
        self.page.deleted_at = timezone.now() - timedelta(days=30)
        self.page.save()
        cutoff = timezone.now() - timedelta(days=7)
        self.wiki.purge_deleted(cutoff)
        assert Content.objects.filter(hash=content_hash).exists()
