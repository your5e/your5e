from http import HTTPStatus

from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.views import LoginView
from django.contrib.auth.views import PasswordChangeView as DjangoPasswordChangeView
from django.http import HttpResponse
from django.shortcuts import redirect
from django.urls import reverse
from django.views import View
from django.views.generic import DetailView
from django.views.generic.detail import SingleObjectMixin

from users.forms import ProfileForm, ProfileLinkForm
from users.models import ProfileLink, User


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
        context["show_details"] = (
            context["is_own_profile"] or self.object.is_public
        )
        if context["is_own_profile"]:
            context["form"] = kwargs.get("form", ProfileForm(instance=self.object))
            context["link_form"] = ProfileLinkForm()
        if context["show_details"]:
            context["profile_links"] = self.object.profile_links.all()

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


class ProfileLinksView(SingleObjectMixin, View):
    model = User
    slug_field = "username"
    slug_url_kwarg = "username"

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()

        if not request.user.is_authenticated:
            return HttpResponse(status=HTTPStatus.UNAUTHORIZED)
        if request.user != self.object:
            return HttpResponse(status=HTTPStatus.FORBIDDEN)

        if "delete" in request.POST:
            ProfileLink.objects.filter(
                id=request.POST["delete"],
                user=self.object,
            ).delete()
        else:
            form = ProfileLinkForm(request.POST)
            if form.is_valid():
                link = form.save(commit=False)
                link.user = self.object
                link.save()

        return redirect("profile", username=self.object.username)


class ProfileVisibilityView(SingleObjectMixin, View):
    model = User
    slug_field = "username"
    slug_url_kwarg = "username"

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()

        if not request.user.is_authenticated:
            return HttpResponse(status=HTTPStatus.UNAUTHORIZED)
        if request.user != self.object:
            return HttpResponse(status=HTTPStatus.FORBIDDEN)

        self.object.is_public = request.POST.get("public") == "true"
        self.object.save()

        return redirect("profile", username=self.object.username)


class PasswordChangeView(LoginRequiredMixin, DjangoPasswordChangeView):
    template_name = "users/password_change.html"

    def get_success_url(self):
        return reverse("profile", kwargs={"username": self.request.user.username})
