from django.contrib import admin
from django.contrib.auth.views import LogoutView
from django.urls import path
from django.views.generic import RedirectView

from users.views import (
    PasswordChangeView,
    ProfileLinksView,
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
]
