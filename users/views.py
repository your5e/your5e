from http import HTTPStatus

from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.views import LoginView
from django.contrib.auth.views import PasswordChangeView as DjangoPasswordChangeView
from django.http import HttpResponse
from django.shortcuts import redirect
from django.urls import reverse
from django.views import View
from django.views.generic import DetailView

from users.forms import ProfileForm
from users.models import User


class UserLoginView(LoginView):
    template_name = "users/login.html"

    def get_success_url(self):
        return reverse("profile", kwargs={"username": self.request.user.username})


class ProfileRedirectView(LoginRequiredMixin, View):
    def get(self, request):
        return redirect("profile", username=request.user.username)


class ProfileView(DetailView):
    model = User
    slug_field = "username"
    slug_url_kwarg = "username"
    template_name = "users/profile.html"
    context_object_name = "profile_user"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["is_own_profile"] = (
            self.request.user.is_authenticated
            and self.request.user == self.object
        )
        if context["is_own_profile"]:
            context["form"] = kwargs.get("form", ProfileForm(instance=self.object))

        return context

    def post(self, request, username):
        self.object = self.get_object()

        if not request.user.is_authenticated:
            return HttpResponse(status=HTTPStatus.UNAUTHORIZED)
        if request.user != self.object:
            return HttpResponse(status=HTTPStatus.FORBIDDEN)

        form = ProfileForm(request.POST, instance=self.object)
        if form.is_valid():
            form.save()
            return redirect("profile", username=username)

        return self.render_to_response(self.get_context_data(form=form))


class PasswordChangeView(LoginRequiredMixin, DjangoPasswordChangeView):
    template_name = "users/password_change.html"

    def get_success_url(self):
        return reverse("profile", kwargs={"username": self.request.user.username})
