import pytest


@pytest.fixture(autouse=True)
def use_api_settings(settings):
    settings.ROOT_URLCONF = "config.urls.api"
    settings.WEB_BASE_URL = "http://localhost:5843"
