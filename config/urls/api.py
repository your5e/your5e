from django.urls import path

from api.notebooks.views import (
    NotebookInternalView,
    NotebookPagesView,
    NotebookPrivateView,
    NotebookPublicView,
    NotebookUserView,
    PageContentView,
)
from api.notebooks.views import (
    NotebookListView as ApiNotebookListView,
)
from api.views import HealthView, PingView

urlpatterns = [
    path(
        route="v1/health",
        name="api_health",
        view=HealthView.as_view(),
    ),
    path(
        route="v1/ping",
        name="api_ping",
        view=PingView.as_view(),
    ),
    path(
        route="v1/notebooks/",
        name="api_notebooks",
        view=ApiNotebookListView.as_view(),
    ),
    path(
        route="v1/notebooks/public",
        name="api_notebooks_public",
        view=NotebookPublicView.as_view(),
    ),
    path(
        route="v1/notebooks/internal",
        name="api_notebooks_internal",
        view=NotebookInternalView.as_view(),
    ),
    path(
        route="v1/notebooks/private",
        name="api_notebooks_private",
        view=NotebookPrivateView.as_view(),
    ),
    path(
        route="v1/notebooks/<str:username>/",
        name="api_notebooks_user",
        view=NotebookUserView.as_view(),
    ),
    path(
        route="v1/notebooks/<str:username>/<str:slug>/",
        name="api_notebook_pages",
        view=NotebookPagesView.as_view(),
    ),
    path(
        route="v1/notebooks/<str:username>/<str:slug>/<str:uuid>",
        name="api_page_content",
        view=PageContentView.as_view(),
    ),
]
