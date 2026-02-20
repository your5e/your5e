from django.contrib import admin
from django.contrib.auth.views import LoginView, LogoutView
from django.urls import path
from django.views.generic import RedirectView

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", RedirectView.as_view(url="/login/")),

    path(
        route="login",
        name="login",
        view=LoginView.as_view(template_name="users/login.html"),
    ),
    path(
        route="logout",
        name="logout",
        view=LogoutView.as_view(next_page="/"),
    ),
]
