from django.contrib import admin
from django.contrib.auth.views import LogoutView
from django.urls import path
from django.views.generic import RedirectView

from notebooks.views import (
    NotebookCollaboratorsView,
    NotebookRenameView,
    NotebookUploadView,
    NotebookView,
    NotebookVisibilityView,
)
from users.views import (
    PasswordChangeView,
    ProfileLinksView,
    ProfileNotebooksView,
    ProfileRedirectView,
    ProfileView,
    ProfileVisibilityView,
    UserLoginView,
)

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", RedirectView.as_view(url="/login/")),

    path(
        route="login",
        name="login",
        view=UserLoginView.as_view(),
    ),
    path(
        route="logout",
        name="logout",
        view=LogoutView.as_view(next_page="/"),
    ),

    path(
        route="profile/",
        name="profile_redirect",
        view=ProfileRedirectView.as_view(),
    ),
    path(
        route="profile/<str:username>/",
        name="profile",
        view=ProfileView.as_view(),
    ),
    path(
        route="profile/<str:username>/links",
        name="profile_links",
        view=ProfileLinksView.as_view(),
    ),
    path(
        route="profile/<str:username>/visibility",
        name="profile_visibility",
        view=ProfileVisibilityView.as_view(),
    ),
    path(
        route="profile/<str:username>/password",
        name="password_change",
        view=PasswordChangeView.as_view(),
    ),
    path(
        route="profile/<str:username>/notebooks",
        name="profile_notebooks",
        view=ProfileNotebooksView.as_view(),
    ),

    path(
        route="notebooks/rename",
        name="notebook_rename",
        view=NotebookRenameView.as_view(),
    ),
    path(
        route="notebooks/visibility",
        name="notebook_visibility",
        view=NotebookVisibilityView.as_view(),
    ),
    path(
        route="notebooks/collaborators",
        name="notebook_collaborators",
        view=NotebookCollaboratorsView.as_view(),
    ),
    path(
        route="notebooks/upload",
        name="notebook_upload",
        view=NotebookUploadView.as_view(),
    ),
    path(
        route="notebooks/<str:username>/<str:slug>/",
        name="notebook",
        view=NotebookView.as_view(),
    ),
]
