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

from notebooks.models import Notebook
from users.forms import ProfileForm, ProfileLinkForm
from users.models import AuthToken, ProfileLink, User


class ProfileObjectMixin(SingleObjectMixin):
    model = User
    slug_field = "username"
    slug_url_kwarg = "username"

    @staticmethod
    def owner_required(method):
        def wrapper(self, request, *args, **kwargs):
            self.object = self.get_object()
            if not request.user.is_authenticated:
                return HttpResponse(status=HTTPStatus.UNAUTHORIZED)
            if request.user != self.object:
                return HttpResponse(status=HTTPStatus.FORBIDDEN)
            return method(self, request, *args, **kwargs)
        return wrapper


class UserLoginView(LoginView):
    template_name = "users/login.html"

    def get_success_url(self):
        return reverse("profile", kwargs={"username": self.request.user.username})


class ProfileRedirectView(LoginRequiredMixin, View):
    def get(self, request):
        return redirect("profile", username=request.user.username)


class ProfileView(ProfileObjectMixin, DetailView):
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
            context["notebooks"] = Notebook.objects.filter(owner=self.object)
            context["shared_notebooks"] = Notebook.objects.filter(
                notebookpermission__user=self.object
            )
            context["tokens"] = AuthToken.objects.filter(user=self.object)
            context["token_created"] = self.request.session.pop("token_created", None)
        if context["show_details"]:
            context["profile_links"] = self.object.profile_links.all()

        return context

    @ProfileObjectMixin.owner_required
    def post(self, request, username):
        form = ProfileForm(request.POST, instance=self.object)
        if form.is_valid():
            form.save()
            return redirect("profile", username=username)

        return self.render_to_response(self.get_context_data(form=form))


class ProfileLinksView(ProfileObjectMixin, View):
    @ProfileObjectMixin.owner_required
    def post(self, request, *args, **kwargs):
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


class ProfileVisibilityView(ProfileObjectMixin, View):
    @ProfileObjectMixin.owner_required
    def post(self, request, *args, **kwargs):
        self.object.is_public = request.POST.get("public") == "true"
        self.object.save()

        return redirect("profile", username=self.object.username)


class ProfileNotebooksView(ProfileObjectMixin, View):
    @ProfileObjectMixin.owner_required
    def post(self, request, *args, **kwargs):
        name = request.POST.get("notebook_name")
        if name:
            Notebook.objects.create(name=name, owner=self.object)

        return redirect("profile", username=self.object.username)


class ProfileTokensView(ProfileObjectMixin, View):
    @ProfileObjectMixin.owner_required
    def post(self, request, *args, **kwargs):
        if "delete" in request.POST:
            AuthToken.objects.filter(
                pk=request.POST["delete"],
                user=self.object,
            ).delete()
        else:
            instance, token = AuthToken.objects.create(
                user=self.object,
                name=request.POST.get("name", ""),
            )
            request.session["token_created"] = token

        return redirect("profile", username=self.object.username)


class PasswordChangeView(ProfileObjectMixin, DjangoPasswordChangeView):
    template_name = "users/password_change.html"

    @ProfileObjectMixin.owner_required
    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)

    def get_success_url(self):
        return reverse("profile", kwargs={"username": self.object.username})
