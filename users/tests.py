import functools
import re
from http import HTTPStatus

import pytest
from django.db import IntegrityError

from users.backends import EmailOrUserBackend
from users.models import ProfileLink, User, get_sentinel_user


class UserMixin:
    @pytest.fixture(autouse=True)
    def setup_users(self, db):
        self.wendy = User.objects.create_user(
            username="wendy",
            email="wendy@example.com",
            password="testpass",
            name="Wendy Testaburger",
            short_name="Wendy",
            description="Bio for Wendy",
            is_public=False,
        )
        self.susan = User.objects.create_user(
            username="susan",
            email="susan@example.com",
            password="testpass",
            name="Susan Test",
            short_name="Susan",
            description="Bio for Susan",
            is_public=True,
        )
        self.susan_link = ProfileLink.objects.create(
            user=self.susan,
            url="https://mastodon.social/@susan",
            label="Mastodon",
        )
        self.mary = User.objects.create_user(
            username="mary",
            email="mary@example.com",
            password="testpass",
            name="Mary Test",
            short_name="Mary",
            description="Bio for Mary",
            is_public=False,
        )
        self.hugh = User.objects.create_user(
            username="hugh",
            email="hugh@example.com",
            password="testpass",
            name="Hugh Test",
            short_name="Hugh",
            description="Bio for Hugh",
            is_public=False,
        )

    @classmethod
    def as_user(cls, attr_name):
        def decorator(test_method):
            @functools.wraps(test_method)
            def wrapper(self, client, *args, **kwargs):
                client.force_login(getattr(self, attr_name))
                return test_method(self, client, *args, **kwargs)
            return wrapper
        return decorator


@pytest.mark.django_db
class TestUser(UserMixin):
    def test_email_must_be_unique(self):
        with pytest.raises(IntegrityError):
            User.objects.create_user(
                username="other",
                email="wendy@example.com",
                password="testpass",
            )

    def test_str_uses_short_name_first(self):
        assert str(self.wendy) == "Wendy"

    def test_str_uses_name_when_no_short_name(self):
        self.wendy.short_name = ""
        assert str(self.wendy) == "Wendy Testaburger"

    def test_str_uses_username_when_no_name_or_short_name(self):
        self.wendy.short_name = ""
        self.wendy.name = ""
        assert str(self.wendy) == "wendy"

    def test_sentinel_user_is_inactive(self):
        sentinel = get_sentinel_user()
        assert sentinel.username == "(deleted)"
        assert sentinel.is_active is False

    def test_sentinel_user_is_reused(self):
        first = get_sentinel_user()
        second = get_sentinel_user()
        assert first.pk == second.pk

    def test_create_user_requires_username(self):
        with pytest.raises(ValueError, match="Username is required"):
            User.objects.create_user(
                username="",
                email="test@example.com",
                password="testpass",
            )

    def test_create_user_requires_email(self):
        with pytest.raises(ValueError, match="Email is required"):
            User.objects.create_user(
                username="testuser",
                email="",
                password="testpass",
            )


@pytest.mark.django_db
class TestEmailOrUserBackend(UserMixin):
    def test_authenticate_with_username(self):
        backend = EmailOrUserBackend()
        user = backend.authenticate(
            None,
            username="wendy",
            password="testpass",
        )
        assert user == self.wendy

    def test_authenticate_with_email(self):
        backend = EmailOrUserBackend()
        user = backend.authenticate(
            None,
            username="wendy@example.com",
            password="testpass"
        )
        assert user == self.wendy

    def test_authenticate_wrong_password(self):
        backend = EmailOrUserBackend()
        user = backend.authenticate(
            None,
            username="wendy",
            password="wrong",
        )
        assert user is None

    def test_authenticate_nonexistent_user(self):
        backend = EmailOrUserBackend()
        user = backend.authenticate(
            None,
            username="nobody",
            password="testpass",
        )
        assert user is None

    def test_authenticate_inactive_user(self):
        self.wendy.is_active = False
        self.wendy.save()
        backend = EmailOrUserBackend()
        user = backend.authenticate(
            None,
            username="wendy",
            password="testpass",
        )
        assert user is None


@pytest.mark.django_db
class TestProfileView(UserMixin):
    def test_profile_redirect_when_logged_out(self, client):
        response = client.get("/profile/")
        assert response.status_code == HTTPStatus.FOUND
        assert response.url == "/login?next=/profile/"

    @UserMixin.as_user("wendy")
    def test_profile_redirect_when_logged_in(self, client):
        response = client.get("/profile/")
        assert response.status_code == HTTPStatus.FOUND
        assert response.url == "/profile/wendy/"

    @UserMixin.as_user("wendy")
    def test_profile_shows_user_details(self, client):
        response = client.get("/profile/wendy/")
        assert response.status_code == HTTPStatus.OK
        assert "Wendy Testaburger" in response.content.decode()

    @UserMixin.as_user("wendy")
    def test_own_profile_shows_edit_form(self, client):
        response = client.get("/profile/wendy/")
        assert response.status_code == HTTPStatus.OK
        assert "Save</button>" in response.content.decode()

    @UserMixin.as_user("wendy")
    def test_other_profile_no_edit_form(self, client):
        response = client.get("/profile/susan/")
        assert response.status_code == HTTPStatus.OK
        assert "Save</button>" not in response.content.decode()

    @UserMixin.as_user("wendy")
    def test_non_public_profile_hides_details(self, client):
        response = client.get("/profile/mary/")
        content = response.content.decode()
        assert "mary" in content
        assert "Mary Test" not in content
        assert "Bio for Mary" not in content

    @UserMixin.as_user("wendy")
    def test_public_profile_shows_details(self, client):
        response = client.get("/profile/susan/")
        content = response.content.decode()
        assert "Susan Test" in content
        assert "Bio for Susan" in content

    @UserMixin.as_user("wendy")
    def test_public_profile_shows_links_with_rel_me(self, client):
        response = client.get("/profile/susan/")
        content = response.content.decode()
        assert re.search(
            r'<a [^>]*href="https://mastodon.social/@susan"[^>]*rel="me"[^>]*>',
            content,
        ) or re.search(
            r'<a [^>]*rel="me"[^>]*href="https://mastodon.social/@susan"[^>]*>',
            content,
        ), "Expected anchor with href and rel='me'"

    @UserMixin.as_user("wendy")
    def test_owner_sees_full_profile_even_when_not_public(self, client):
        response = client.get("/profile/wendy/")
        content = response.content.decode()
        assert "Wendy Testaburger" in content
        assert "Bio for Wendy" in content

    @UserMixin.as_user("wendy")
    def test_profile_form_includes_description(self, client):
        response = client.get("/profile/wendy/")
        content = response.content.decode()
        assert 'name="description"' in content

    @UserMixin.as_user("wendy")
    def test_profile_shows_visibility_button(self, client):
        response = client.get("/profile/wendy/")
        content = response.content.decode()
        assert "Make profile public" in content

    @UserMixin.as_user("wendy")
    def test_toggle_profile_visibility(self, client):
        assert self.wendy.is_public is False
        response = client.post(
            "/profile/wendy/visibility", {"public": "true"}
        )
        assert response.status_code == HTTPStatus.FOUND
        self.wendy.refresh_from_db()
        assert self.wendy.is_public is True

    def test_anonymous_sees_public_profile(self, client):
        response = client.get("/profile/susan/")
        content = response.content.decode()
        assert response.status_code == HTTPStatus.OK
        assert "Susan Test" in content
        assert "Bio for Susan" in content

    def test_anonymous_sees_only_username_for_non_public(self, client):
        response = client.get("/profile/mary/")
        content = response.content.decode()
        assert response.status_code == HTTPStatus.OK
        assert "mary" in content
        assert "Mary Test" not in content
        assert "Bio for Mary" not in content

    @UserMixin.as_user("wendy")
    def test_add_profile_link(self, client):
        response = client.post(
            "/profile/wendy/links", {
                "url": "https://example.com/@wendy",
                "label": "Website",
            }
        )
        assert response.status_code == HTTPStatus.FOUND
        assert response.url == "/profile/wendy/"
        link = ProfileLink.objects.get(user=self.wendy)
        assert link.url == "https://example.com/@wendy"
        assert link.label == "Website"

    @UserMixin.as_user("wendy")
    def test_delete_profile_link(self, client):
        link = ProfileLink.objects.create(
            user=self.wendy,
            url="https://example.com/@wendy",
            label="Website",
        )
        response = client.post(
            "/profile/wendy/links", {
                "delete": link.id,
            }
        )
        assert response.status_code == HTTPStatus.FOUND
        assert response.url == "/profile/wendy/"
        assert ProfileLink.objects.filter(user=self.wendy).count() == 0

    @UserMixin.as_user("wendy")
    def test_update_own_profile(self, client):
        response = client.post(
            "/profile/wendy/", {
                "name": "Wendy Test",
                "short_name": "W",
            }
        )
        assert response.status_code == HTTPStatus.FOUND
        self.wendy.refresh_from_db()
        assert self.wendy.name == "Wendy Test"
        assert self.wendy.short_name == "W"

    @UserMixin.as_user("wendy")
    def test_cannot_update_other_profile(self, client):
        response = client.post(
            "/profile/susan/", {
                "name": "Hacked",
                "short_name": "H",
            }
        )
        assert response.status_code == HTTPStatus.FORBIDDEN
        self.susan.refresh_from_db()
        assert self.susan.name == "Susan Test"

    def test_anonymous_cannot_update_profile(self, client):
        response = client.post(
            "/profile/wendy/", {
                "name": "Hacked",
                "short_name": "H",
            }
        )
        assert response.status_code == HTTPStatus.UNAUTHORIZED
        self.wendy.refresh_from_db()
        assert self.wendy.name == "Wendy Testaburger"


@pytest.mark.django_db
class TestLogin(UserMixin):
    def test_login_redirects_to_profile(self, client):
        response = client.post(
            "/login", {
                "username": "wendy",
                "password": "testpass",
            }
        )
        assert response.status_code == HTTPStatus.FOUND
        assert response.url == "/profile/wendy/"
