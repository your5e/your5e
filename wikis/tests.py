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

        self.image_page = Page.objects.create(wiki=self.wiki)
        self.image_page.update(
            filename="Maps/World.png",
            mime_type="image/png",
            data=b"PNG data",
            created_by=self.wendy,
        )

        self.page_with_links = Page.objects.create(wiki=self.wiki)
        self.page_with_links.update(
            filename="Rules/Status/Index.md",
            mime_type="text/markdown",
            data=b"\n".join([
                b"[Relative](./exhaustion)",
                b"[Parent](../combat)",
                b"[Bare](conditions)",
                b"[Absolute](/characters)",
                b"[External](https://example.com)",
                b"[Anchor](#section)",
            ]),
            created_by=self.wendy,
        )

        self.page_with_wikilinks = Page.objects.create(wiki=self.wiki)
        self.page_with_wikilinks.update(
            filename="Index.md",
            mime_type="text/markdown",
            data=b"\n".join([
                b"[[Combat]]",
                b"[[combat]]",
                b"[[Theron Blackwood]]",
                b"[[Combat|fighting]]",
                b"[[Combat.md]]",
                b"[[Nonexistent Page]]",
                b"![[World.png]]",
                b"![[World.png|300]]",
                b"![[World.png|640x480]]",
            ]),
            created_by=self.wendy,
        )

        self.page_with_underscore = Page.objects.create(wiki=self.wiki)
        self.page_with_underscore.update(
            filename="getting_started.md",
            mime_type="text/markdown",
            data=b"# Getting Started",
            created_by=self.wendy,
        )

        self.wiki.refresh_from_db()
        self.last_updated_after_setup = self.wiki.last_updated


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

    def test_generate_path_strips_apostrophes(self):
        self.version.filename = "Baker's Dozen.md"
        assert self.version.generate_path() == "bakers-dozen"
        self.version.filename = "Baker\u2019s Dozen.md"
        assert self.version.generate_path() == "bakers-dozen"

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

    def test_render_resolves_markdown_links(self):
        html = self.page_with_links.latest_version.render(
            base_url="/notebooks/wendy/notes"
        )
        assert html == (
            '<p><a href="/notebooks/wendy/notes/rules/status/exhaustion">Relative</a>\n'
            '<a href="/notebooks/wendy/notes/rules/combat">Parent</a>\n'
            '<a href="/notebooks/wendy/notes/rules/status/conditions">Bare</a>\n'
            '<a href="/notebooks/wendy/notes/characters">Absolute</a>\n'
            '<a href="https://example.com">External</a>\n'
            '<a href="#section">Anchor</a></p>'
        )

    def test_render_resolves_wikilinks(self):
        html = self.page_with_wikilinks.latest_version.render(
            base_url="/notebooks/wendy/notes"
        )
        assert html == (
            '<p><a href="/notebooks/wendy/notes/rules/combat">Combat</a>\n'
            '<a href="/notebooks/wendy/notes/rules/combat">combat</a>\n'
            '<a href="/notebooks/wendy/notes/characters/theron-blackwood">'
            'Theron Blackwood</a>\n'
            '<a href="/notebooks/wendy/notes/rules/combat">fighting</a>\n'
            '<a href="/notebooks/wendy/notes/rules/combat">Combat.md</a>\n'
            '<a href="/notebooks/wendy/notes/nonexistent-page">Nonexistent Page</a>\n'
            '<img src="/notebooks/wendy/notes/maps/world.png">\n'
            '<img src="/notebooks/wendy/notes/maps/world.png" width="300">\n'
            '<img src="/notebooks/wendy/notes/maps/world.png" width="640" '
            'height="480"></p>'
        )

    def test_render_wikilink_shortest_path_wins(self):
        Page.objects.create(wiki=self.wiki).update(
            filename="Rules/Advanced/Combat.md",
            mime_type="text/markdown",
            data=b"Advanced combat rules.",
            created_by=self.wendy,
        )
        html = self.page_with_wikilinks.latest_version.render(
            base_url="/notebooks/wendy/notes"
        )
        # Still resolves to rules/combat, not rules/advanced/combat
        assert html == (
            '<p><a href="/notebooks/wendy/notes/rules/combat">Combat</a>\n'
            '<a href="/notebooks/wendy/notes/rules/combat">combat</a>\n'
            '<a href="/notebooks/wendy/notes/characters/theron-blackwood">'
            'Theron Blackwood</a>\n'
            '<a href="/notebooks/wendy/notes/rules/combat">fighting</a>\n'
            '<a href="/notebooks/wendy/notes/rules/combat">Combat.md</a>\n'
            '<a href="/notebooks/wendy/notes/nonexistent-page">Nonexistent Page</a>\n'
            '<img src="/notebooks/wendy/notes/maps/world.png">\n'
            '<img src="/notebooks/wendy/notes/maps/world.png" width="300">\n'
            '<img src="/notebooks/wendy/notes/maps/world.png" width="640" '
            'height="480"></p>'
        )

    def test_render_wikilink_matches_underscore_filename(self):
        page = Page.objects.create(wiki=self.wiki)
        page.update(
            filename="Linking Page.md",
            mime_type="text/markdown",
            data=b"[[Getting Started]]",
            created_by=self.wendy,
        )
        html = page.latest_version.render(base_url="/wiki")
        assert 'href="/wiki/getting-started"' in html


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
        self.wiki.refresh_from_db()
        assert self.wiki.last_updated > self.last_updated_after_setup

    def test_update_with_no_changes_does_not_create_version(self):
        self.page.update(
            filename="document.txt",
            mime_type="text/plain",
            data=b"Test content",
            created_by=self.wendy,
        )
        assert self.page.version_set.count() == 1
        self.wiki.refresh_from_db()
        assert self.wiki.last_updated == self.last_updated_after_setup

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
        self.wiki.refresh_from_db()
        assert self.wiki.last_updated > self.last_updated_after_setup

    def test_restore_clears_deleted_at(self):
        self.page.soft_delete()
        assert self.page.deleted_at is not None
        self.wiki.refresh_from_db()
        before_restore = self.wiki.last_updated

        self.page.restore()
        assert self.page.deleted_at is None
        self.wiki.refresh_from_db()
        assert self.wiki.last_updated > before_restore

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
        self.wiki.refresh_from_db()
        assert self.wiki.last_updated > self.last_updated_after_setup

    def test_delete_keeps_shared_content(self):
        content_hash = self.version.content.hash
        self.page.delete()
        assert Content.objects.filter(hash=content_hash).exists()

    def test_delete_version_does_not_break_history(self):
        self.page_with_history.delete_version(2)
        assert [v.number for v in self.page_with_history.history()] == [1, 3]
        self.wiki.refresh_from_db()
        assert self.wiki.last_updated > self.last_updated_after_setup

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
        self.wiki.refresh_from_db()
        assert self.wiki.last_updated > self.last_updated_after_setup

    def test_get_version_returns_latest_when_no_number(self):
        version = self.page_with_history.get_version()
        assert version.number == 3

    def test_get_version_returns_specific_version(self):
        version = self.page_with_history.get_version(number=2)
        assert version.number == 2
        assert version.content.data == b"Second revision"

    def test_get_version_raises_for_nonexistent_version(self):
        with pytest.raises(Page.DoesNotExist):
            self.page_with_history.get_version(number=99)

    def test_get_version_raises_for_invalid_version_string(self):
        with pytest.raises(Page.DoesNotExist):
            self.page_with_history.get_version(number="invalid")


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
            self.image_page.latest_version,
            self.page_with_links.latest_version,
            self.page_with_wikilinks.latest_version,
            self.page_with_underscore.latest_version,
        ]

    def test_all_pages_excludes_deleted(self):
        self.page.soft_delete()
        assert len(self.wiki.all_pages()) == 10

    def test_deleted_pages(self):
        self.page.soft_delete()
        self.page_with_history.soft_delete()
        assert self.wiki.deleted_pages() == [
            self.page.latest_version,
            self.page_with_history.latest_version,
        ]

    def test_changes_since(self):
        before = timezone.now()
        self.page.update(
            filename="document.txt",
            mime_type="text/plain",
            data=b"Updated content",
            created_by=self.wendy,
        )
        self.page_with_history.update(
            filename="history.txt",
            mime_type="text/plain",
            data=b"Updated history",
            created_by=self.wendy,
        )
        assert list(self.wiki.changes_since(before)) == [
            self.page_with_history,
            self.page,
        ]

    def test_changes_since_includes_deleted_pages(self):
        before = timezone.now()
        self.page.update(
            filename="document.txt",
            mime_type="text/plain",
            data=b"Updated content",
            created_by=self.wendy,
        )
        self.page_with_history.soft_delete()
        assert list(self.wiki.changes_since(before)) == [
            self.page_with_history,
            self.page,
        ]

    def test_changes_since_excludes_unchanged_pages(self):
        after = timezone.now()
        assert list(self.wiki.changes_since(after)) == []

    def test_contents_in_root(self):
        contents = self.wiki.contents_in("/")
        assert [f.display_name for f in contents["files"]] == [
            "Index",
            "document.txt",
            "getting_started",
            "history.txt",
            "shared.txt",
        ]
        assert [(f.name, f.href) for f in contents["folders"]] == [
            ("Characters", "characters"),
            ("Maps", "maps"),
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
        assert [(f.name, f.href) for f in contents["folders"]] == [
            ("Maps", "maps"),
            ("Rules", "rules"),
        ]
        contents = self.wiki.contents_in("/rules/")
        assert contents["files"] == []

    def test_contents_in_folder_prefers_display_name_over_slug(self):
        page_a = Page.objects.create(wiki=self.wiki)
        page_a.update(
            filename="magic-items/index.md",
            mime_type="text/markdown",
            data=b"Index",
            created_by=self.wendy,
        )
        page_b = Page.objects.create(wiki=self.wiki)
        page_b.update(
            filename="Magic Items/Bag of Holding.md",
            mime_type="text/markdown",
            data=b"A bag",
            created_by=self.wendy,
        )
        contents = self.wiki.contents_in("/")
        folder_names = [f.name for f in contents["folders"]]
        assert "Magic Items" in folder_names
        assert "magic-items" not in folder_names

    def test_contents_in_folder_prefers_display_name_regardless_of_order(self):
        page_a = Page.objects.create(wiki=self.wiki)
        page_a.update(
            filename="Magic Items/Bag of Holding.md",
            mime_type="text/markdown",
            data=b"A bag",
            created_by=self.wendy,
        )
        page_b = Page.objects.create(wiki=self.wiki)
        page_b.update(
            filename="magic-items/index.md",
            mime_type="text/markdown",
            data=b"Index",
            created_by=self.wendy,
        )
        contents = self.wiki.contents_in("/")
        folder_names = [f.name for f in contents["folders"]]
        assert "Magic Items" in folder_names
        assert "magic-items" not in folder_names

    def test_suggest_filename_titlecases_path(self):
        assert self.wiki.suggest_filename("rumours") == "Rumours"

    def test_suggest_filename_titlecases_nested_path(self):
        assert self.wiki.suggest_filename("magic-items/bag-of-holding") == \
            "Magic Items/Bag Of Holding"

    def test_suggest_filename_preserves_existing_folder(self):
        page = Page.objects.create(wiki=self.wiki)
        page.update(
            filename="magic-items/index.md",
            mime_type="text/markdown",
            data=b"# Magic Items",
            created_by=self.wendy,
        )
        assert self.wiki.suggest_filename("magic-items/bag-of-holding") == \
            "magic-items/Bag Of Holding"

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
