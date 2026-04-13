import os

from config.settings.base import *  # noqa: F401, F403

ROOT_URLCONF = "config.urls.api"
WSGI_APPLICATION = "config.wsgi.api.application"

WEB_BASE_URL = os.environ["WEB_BASE_URL"]
