import functools
from http import HTTPStatus

import pytest
from rest_framework.test import APIClient

from users.models import AuthToken
from users.tests import UserMixin


class ApiMixin(UserMixin):
    @pytest.fixture
    def api_client(self):
        return APIClient()

    @classmethod
    def as_api_user(cls, attr_name):
        def decorator(test_method):
            @functools.wraps(test_method)
            def wrapper(self, api_client, *args, **kwargs):
                _, token = AuthToken.objects.create(user=getattr(self, attr_name))
                api_client.credentials(HTTP_AUTHORIZATION=f"Token {token}")
                return test_method(self, api_client, *args, **kwargs)
            return wrapper
        return decorator


@pytest.mark.django_db
class TestPing(ApiMixin):
    def test_ping_without_token_returns_unauthorized(self, api_client):
        response = api_client.get("/api/ping")
        assert response.status_code == HTTPStatus.UNAUTHORIZED
        assert response.json() == {"error": "Authentication required."}

    def test_ping_with_invalid_token_returns_unauthorized(self, api_client):
        api_client.credentials(HTTP_AUTHORIZATION="Token invalid-token")
        response = api_client.get("/api/ping")
        assert response.status_code == HTTPStatus.UNAUTHORIZED
        assert response.json() == {"error": "Invalid token."}

    def test_ping_with_valid_token_returns_username(self, api_client):
        _, token = AuthToken.objects.create(user=self.wendy)
        api_client.credentials(HTTP_AUTHORIZATION=f"Token {token}")
        response = api_client.get("/api/ping")
        assert response.status_code == HTTPStatus.OK
        assert response.json() == {"username": "wendy"}
