import functools

import pytest
from django.db import IntegrityError

from users.backends import EmailOrUserBackend
from users.models import User, get_sentinel_user


class UserMixin:
    @pytest.fixture(autouse=True)
    def setup_users(self, db):
        self.wendy = User.objects.create_user(
            username="wendy",
            email="wendy@example.com",
            password="testpass",
            name="Wendy Testaburger",
            short_name="Wendy",
        )

    @staticmethod
    def as_wendy(test_method):
        @functools.wraps(test_method)
        def wrapper(self, client, *args, **kwargs):
            client.force_login(self.wendy)
            return test_method(self, client, *args, **kwargs)
        return wrapper


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
