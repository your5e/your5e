import pytest
from django.core.exceptions import ValidationError

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


@pytest.mark.django_db
class TestContent(WikiMixin):
    def test_content_primary_key_is_hash_of_data(self):
        assert self.version.content.pk == self.version.content.hash
        assert self.version.content.hash == (
            "9d9595c5d94fb65b824f56e9999527dba9542481580d69feb89056aabaa0aa87"
        )

    def test_content_is_shared_between_wikis(self):
        wiki_b = Wiki.objects.create()
        page_b = Page.objects.create(wiki=wiki_b)
        page_b.update(
            filename="doc.txt",
            mime_type="text/plain",
            data=b"Test content",
            created_by=self.wendy,
        )
        assert Content.objects.count() == 1


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
        assert self.version.generate_path() == "heros-legendes/epee-du-crepuscule.md"

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
        self.page.update(
            filename="renamed.txt",
            mime_type="text/plain",
            data=b"Test content",
            created_by=self.wendy,
        )
        assert self.page.version_set.count() == 2
        assert Content.objects.count() == 1

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
