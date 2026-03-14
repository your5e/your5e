from http import HTTPStatus

from django.contrib.auth.views import redirect_to_login
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views import View

from campaigns.forms import (
    CampaignDescriptionForm,
    CampaignForm,
    CampaignRenameForm,
)
from campaigns.models import Campaign, CampaignNotebook
from notebooks.models import Notebook
from notebooks.views import NotebookPermissions
from users.models import User, get_sentinel_user
from users.views import ProfileObjectMixin


class CampaignPermissions:
    @staticmethod
    def can_view(campaign, user):
        if not user.is_authenticated:
            return False
        return campaign.players.filter(pk=user.pk).exists()

    @staticmethod
    def is_owner(campaign, user):
        return user.is_authenticated and campaign.owner == user

    @staticmethod
    def is_unclaimed(campaign):
        return campaign.owner == get_sentinel_user()

    @staticmethod
    def can_unlink_notebook(link, campaign, user):
        return (
            campaign.owner == user
            or link.notebook.owner == user
            or link.linked_by == user
        )

    @staticmethod
    def view_required(method):
        def wrapper(self, request, *args, **kwargs):
            self.object = self.get_object()
            if not request.user.is_authenticated:
                return HttpResponse(status=HTTPStatus.UNAUTHORIZED)
            if not CampaignPermissions.can_view(self.object, request.user):
                return HttpResponse(status=HTTPStatus.FORBIDDEN)
            return method(self, request, *args, **kwargs)
        return wrapper


class CampaignObjectMixin:
    def get_object(self):
        owner = get_object_or_404(User, username=self.kwargs["username"])
        return get_object_or_404(Campaign, owner=owner, slug=self.kwargs["slug"])


class CampaignView(CampaignObjectMixin, View):
    def get_visible_notebooks(self, user):
        links = self.object.campaign_notebooks.select_related(
            "notebook", "notebook__owner", "linked_by"
        )
        visible = []
        for link in links:
            if NotebookPermissions.can_view(link.notebook, user):
                visible.append(link)
        return visible

    def get_linkable_notebooks(self, user):
        already_linked = self.object.campaign_notebooks.values_list(
            "notebook_id", flat=True
        )
        owned = Notebook.objects.filter(owner=user).exclude(pk__in=already_linked)
        public = Notebook.objects.filter(
            visibility=Notebook.Visibility.PUBLIC
        ).exclude(pk__in=already_linked).exclude(owner=user)
        return list(owned) + list(public)

    @CampaignPermissions.view_required
    def get(self, request, *args, **kwargs):
        is_owner = CampaignPermissions.is_owner(self.object, request.user)
        is_unclaimed = CampaignPermissions.is_unclaimed(self.object)
        visible_notebooks = self.get_visible_notebooks(request.user)
        linkable_notebooks = self.get_linkable_notebooks(request.user)
        players = list(self.object.players.all())

        player_set = set(players)
        notebook_data = []
        notebook_count = len(visible_notebooks)
        for index, link in enumerate(visible_notebooks):
            notebook = link.notebook
            is_notebook_owner = notebook.owner == request.user
            editors = []
            viewers = []
            cannot_see = []

            for perm in notebook.notebookpermission_set.select_related("user"):
                if perm.user not in player_set:
                    continue
                if perm.role == "editor":
                    editors.append(perm.user)
                else:
                    viewers.append(perm.user)

            if is_notebook_owner:
                for player in players:
                    if not NotebookPermissions.can_view(notebook, player):
                        cannot_see.append(player)

            notebook_data.append({
                "link": link,
                "notebook": notebook,
                "editors": editors,
                "viewers": viewers,
                "cannot_see": cannot_see,
                "can_remove": CampaignPermissions.can_unlink_notebook(
                    link, self.object, request.user
                ),
                "is_notebook_owner": is_notebook_owner,
                "is_first": index == 0,
                "is_last": index == notebook_count - 1,
            })

        other_players = [
            p for p in players
                if p != request.user
        ]

        return render(request, "campaigns/campaign.html", {
            "campaign": self.object,
            "is_owner": is_owner,
            "is_unclaimed": is_unclaimed,
            "players": players,
            "other_players": other_players,
            "notebook_data": notebook_data,
            "linkable_notebooks": linkable_notebooks,
        })

    @CampaignPermissions.view_required
    def post(self, request, *args, **kwargs):
        is_owner = CampaignPermissions.is_owner(self.object, request.user)
        is_unclaimed = CampaignPermissions.is_unclaimed(self.object)

        if "claim" in request.POST:
            if not is_unclaimed:
                return HttpResponse(status=HTTPStatus.FORBIDDEN)
            self.object.owner = request.user
            self.object.save()
            return redirect(self.object)

        if "leave" in request.POST:
            return HttpResponse(status=HTTPStatus.FORBIDDEN)

        if not is_owner:
            return HttpResponse(status=HTTPStatus.FORBIDDEN)

        if "name" in request.POST:
            form = CampaignRenameForm(request.POST, instance=self.object)
            if form.is_valid():
                campaign = form.save(commit=False)
                campaign.slug = campaign.generate_unique_slug()
                campaign.save()
        elif "description" in request.POST:
            form = CampaignDescriptionForm(request.POST, instance=self.object)
            if form.is_valid():
                form.save()
        elif "regenerate_join_slug" in request.POST:
            self.object.join_slug = self.object.generate_join_slug()
            self.object.save()
        elif "remove_player" in request.POST:
            player_id = request.POST["remove_player"]
            if str(self.object.owner.pk) == player_id:
                return HttpResponse(status=HTTPStatus.FORBIDDEN)
            self.object.players.remove(player_id)

        return redirect(
            "campaign",
            username=self.object.owner.username,
            slug=self.object.slug,
        )


class CampaignNotebooksView(View):
    def get_object(self):
        return get_object_or_404(Campaign, pk=self.request.POST.get("campaign"))

    def post(self, request):
        self.object = self.get_object()

        if not request.user.is_authenticated:
            return HttpResponse(status=HTTPStatus.UNAUTHORIZED)

        is_member = self.object.players.filter(pk=request.user.pk).exists()
        if not is_member:
            return HttpResponse(status=HTTPStatus.FORBIDDEN)

        is_owner = self.object.owner == request.user

        if "link_notebook" in request.POST:
            notebook_id = request.POST["link_notebook"]
            notebook = Notebook.objects.filter(pk=notebook_id).first()
            if not notebook:
                return HttpResponse(status=HTTPStatus.BAD_REQUEST)

            can_link = (
                notebook.owner == request.user
                or notebook.visibility == Notebook.Visibility.PUBLIC
            )
            if not can_link:
                return HttpResponse(status=HTTPStatus.FORBIDDEN)

            if CampaignNotebook.objects.filter(
                campaign=self.object, notebook=notebook
            ).exists():
                return HttpResponse(status=HTTPStatus.BAD_REQUEST)

            CampaignNotebook.objects.create(
                campaign=self.object,
                notebook=notebook,
                linked_by=request.user,
            )

        elif "unlink_notebook" in request.POST:
            link_id = request.POST["unlink_notebook"]
            link = CampaignNotebook.objects.filter(
                pk=link_id, campaign=self.object
            ).select_related("notebook").first()
            if not link:
                return HttpResponse(status=HTTPStatus.BAD_REQUEST)

            if not CampaignPermissions.can_unlink_notebook(
                link, self.object, request.user
            ):
                return HttpResponse(status=HTTPStatus.FORBIDDEN)

            link.delete()

        elif "move_notebook_up" in request.POST:
            if not is_owner:
                return HttpResponse(status=HTTPStatus.FORBIDDEN)
            link_id = request.POST["move_notebook_up"]
            link = CampaignNotebook.objects.filter(
                pk=link_id, campaign=self.object
            ).first()
            if link:
                swap = CampaignNotebook.objects.filter(
                    campaign=self.object, order__lt=link.order
                ).order_by("-order").first()
                if swap:
                    link.order, swap.order = swap.order, link.order
                    link.save()
                    swap.save()

        elif "move_notebook_down" in request.POST:
            if not is_owner:
                return HttpResponse(status=HTTPStatus.FORBIDDEN)
            link_id = request.POST["move_notebook_down"]
            link = CampaignNotebook.objects.filter(
                pk=link_id, campaign=self.object
            ).first()
            if link:
                swap = CampaignNotebook.objects.filter(
                    campaign=self.object, order__gt=link.order
                ).order_by("order").first()
                if swap:
                    link.order, swap.order = swap.order, link.order
                    link.save()
                    swap.save()

        return redirect(self.object)


class CampaignJoinView(View):
    def get_object(self):
        return get_object_or_404(Campaign, join_slug=self.kwargs["join_slug"])

    def get(self, request, *args, **kwargs):
        self.object = self.get_object()
        if not request.user.is_authenticated:
            return redirect_to_login(request.path)
        is_member = self.object.players.filter(pk=request.user.pk).exists()
        return render(request, "campaigns/join.html", {
            "campaign": self.object,
            "is_member": is_member,
        })

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        if not request.user.is_authenticated:
            return redirect_to_login(request.path)
        self.object.players.add(request.user)
        return redirect(
            "campaign",
            username=self.object.owner.username,
            slug=self.object.slug,
        )


class CampaignLeaveView(View):
    def get_object(self, request):
        return get_object_or_404(Campaign, pk=request.POST.get("campaign"))

    def post(self, request):
        if not request.user.is_authenticated:
            return HttpResponse(status=HTTPStatus.UNAUTHORIZED)
        self.object = self.get_object(request)
        if not CampaignPermissions.can_view(self.object, request.user):
            return HttpResponse(status=HTTPStatus.FORBIDDEN)
        if "confirm" in request.POST:
            is_owner = CampaignPermissions.is_owner(self.object, request.user)
            if is_owner:
                self.object.owner = get_sentinel_user()
                self.object.save()
            self.object.players.remove(request.user)
            if not self.object.players.exists():
                self.object.delete()
            return redirect("profile", username=request.user.username)
        is_owner = CampaignPermissions.is_owner(self.object, request.user)
        return render(request, "campaigns/leave.html", {
            "campaign": self.object,
            "is_owner": is_owner,
        })


class CampaignDeleteView(View):
    def get_object(self, request):
        return get_object_or_404(Campaign, pk=request.POST.get("campaign"))

    def post(self, request):
        if not request.user.is_authenticated:
            return HttpResponse(status=HTTPStatus.UNAUTHORIZED)
        self.object = self.get_object(request)
        if not CampaignPermissions.is_owner(self.object, request.user):
            return HttpResponse(status=HTTPStatus.FORBIDDEN)
        if "confirm" in request.POST:
            self.object.delete()
            return redirect("profile", username=request.user.username)
        return render(request, "campaigns/delete.html", {
            "campaign": self.object,
        })


class ProfileCampaignsView(ProfileObjectMixin, View):
    @ProfileObjectMixin.owner_required
    def post(self, request, *args, **kwargs):
        if "delete" in request.POST or "leave" in request.POST:
            return HttpResponse(status=HTTPStatus.FORBIDDEN)
        form = CampaignForm(request.POST)
        if form.is_valid():
            campaign = form.save(commit=False)
            campaign.owner = self.object
            campaign.save()
            return redirect(campaign)
        return redirect("profile", username=self.object.username)
