from http import HTTPStatus

from django.contrib.auth.views import redirect_to_login
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views import View

from campaigns.forms import CampaignForm
from campaigns.models import Campaign, CampaignNotebook
from campaigns.permissions import CampaignPermissions
from notebooks.models import Notebook
from notebooks.permissions import NotebookPermissions
from notebooks.views import NotebookIndexView, NotebookPageEditView, NotebookPageView
from users.models import User, get_sentinel_user


class CampaignObjectMixin:
    def get_object(self):
        owner = get_object_or_404(User, username=self.kwargs["username"])
        return get_object_or_404(Campaign, owner=owner, slug=self.kwargs["slug"])


class CampaignSettingsView(CampaignObjectMixin, View):
    def get(self, request, username, slug):
        self.object = self.get_object()
        if not request.user.is_authenticated:
            return HttpResponse(status=HTTPStatus.UNAUTHORIZED)
        if not CampaignPermissions.is_owner(self.object, request.user):
            return HttpResponse(status=HTTPStatus.FORBIDDEN)

        other_players = [p for p in self.object.get_players() if p != self.object.owner]

        breadcrumbs = [
            {"name": self.object.name, "url": self.object.get_absolute_url()},
            {"name": "Settings"},
        ]
        return render(request, "campaigns/settings.html", {
            "campaign": self.object,
            "players": other_players,
            "breadcrumbs": breadcrumbs,
        })


class CampaignView(CampaignObjectMixin, View):
    def get_visible_notebooks(self, user):
        links = self.object.campaign_notebooks.filter(
            is_wiki=False
        ).select_related(
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
        players = self.object.get_players()

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
                "can_move_up": not link.is_wiki and index > 0,
                "can_move_down": not link.is_wiki and index < notebook_count - 1,
            })

        other_players = [
            p for p in players
                if p != request.user
        ]

        return render(request, "campaigns/campaign.html", {
            "campaign": self.object,
            "description_html": self.object.description_html(),
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
            form = CampaignForm(request.POST, instance=self.object)
            if form.is_valid():
                campaign = form.save(commit=False)
                campaign.slug = campaign.generate_unique_slug()
                campaign.save()
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

        if not CampaignPermissions.can_view(self.object, request.user):
            return HttpResponse(status=HTTPStatus.FORBIDDEN)

        is_owner = CampaignPermissions.is_owner(self.object, request.user)

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

            confirm = request.POST.get("confirm") == "true"
            if not confirm:
                wiki_link = self.object.campaign_notebooks.filter(is_wiki=True).first()
                if wiki_link:
                    try:
                        wiki_link.notebook.get_page(path=notebook.slug)
                        return render(request, "campaigns/confirm_link.html", {
                            "campaign": self.object,
                            "notebook": notebook,
                            "collision_path": notebook.slug,
                        })
                    except wiki_link.notebook.page_set.model.DoesNotExist:
                        pass

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
                if swap and swap.is_wiki:
                    return HttpResponse(status=HTTPStatus.FORBIDDEN)
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
            if link and link.is_wiki:
                return HttpResponse(status=HTTPStatus.FORBIDDEN)
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
        is_member = CampaignPermissions.can_view(self.object, request.user)
        return render(request, "campaigns/join.html", {
            "campaign": self.object,
            "is_member": is_member,
            "players": list(self.object.players.all()),
            "description_html": self.object.description_html(),
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
        breadcrumbs = [
            {"name": self.object.name, "url": self.object.get_absolute_url()},
            {"name": "Leave"},
        ]
        return render(request, "campaigns/leave.html", {
            "campaign": self.object,
            "is_owner": is_owner,
            "breadcrumbs": breadcrumbs,
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
        if "confirm" in request.POST or not self.object.has_content():
            self.object.delete()
            return redirect("profile", username=request.user.username)
        breadcrumbs = [
            {"name": self.object.name, "url": self.object.get_absolute_url()},
            {"name": "Delete"},
        ]
        return render(request, "campaigns/delete.html", {
            "campaign": self.object,
            "breadcrumbs": breadcrumbs,
        })


class CampaignCreateView(View):
    def get(self, request):
        if not request.user.is_authenticated:
            return redirect_to_login(request.path)
        return render(request, "campaigns/create.html", {
            "form": CampaignForm(),
        })

    def post(self, request):
        if not request.user.is_authenticated:
            return redirect_to_login(request.path)
        form = CampaignForm(request.POST)
        if form.is_valid():
            campaign = form.save(commit=False)
            campaign.owner = request.user
            campaign.save()
            return redirect(campaign)
        return render(request, "campaigns/create.html", {
            "form": form,
        })


class CampaignListView(View):
    def get(self, request):
        if not request.user.is_authenticated:
            return redirect_to_login(request.path)
        my_campaigns = Campaign.objects.filter(owner=request.user).prefetch_related(
            "players"
        )
        other_campaigns = Campaign.objects.filter(
            players=request.user
        ).exclude(owner=request.user).prefetch_related("players", "owner")
        return render(request, "campaigns/list.html", {
            "my_campaigns": my_campaigns,
            "other_campaigns": other_campaigns,
            "form": CampaignForm(),
        })


class CampaignWikiMixin:
    """
    Mixin for campaign wiki views.
    Resolves notebook from campaign path, handles permissions.
    """

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        owner = get_object_or_404(User, username=kwargs["username"])
        self.campaign = get_object_or_404(Campaign, owner=owner, slug=kwargs["slug"])
        self.wiki_path = kwargs.get("path", "")

    def get_object(self):
        notebook, self.notebook_path = self.resolve_notebook()
        self.path = self.notebook_path
        return notebook

    def resolve_notebook(self):
        if not self.wiki_path:
            wiki_link = self.campaign.campaign_notebooks.filter(is_wiki=True).first()
            return wiki_link.notebook, ""

        first_segment = self.wiki_path.split("/")[0]
        notebook_link = self.campaign.campaign_notebooks.filter(
            slug=first_segment, is_wiki=False
        ).select_related("notebook").first()

        if notebook_link:
            remainder = "/".join(self.wiki_path.split("/")[1:])
            return notebook_link.notebook, remainder

        wiki_link = self.campaign.campaign_notebooks.filter(is_wiki=True).first()
        return wiki_link.notebook, self.wiki_path

    def is_wiki_notebook(self):
        return self.object.campaign_notebooks.filter(
            campaign=self.campaign, is_wiki=True
        ).exists()

    def check_permissions(self, request):
        if not request.user.is_authenticated:
            return HttpResponse(status=HTTPStatus.UNAUTHORIZED)
        if not CampaignPermissions.can_view(self.campaign, request.user):
            return HttpResponse(status=HTTPStatus.FORBIDDEN)
        if not self.is_wiki_notebook():
            if not NotebookPermissions.can_view(self.object, request.user):
                return HttpResponse(status=HTTPStatus.FORBIDDEN)
        return None

    def get_base_url(self):
        return reverse("campaign_wiki", kwargs={
            "username": self.campaign.owner.username,
            "slug": self.campaign.slug,
        })

    def get_wiki_path_for_notebook_path(self, notebook_path):
        if self.is_wiki_notebook():
            return notebook_path
        notebook_link = self.campaign.campaign_notebooks.filter(
            notebook=self.object
        ).first()
        return notebook_link.slug + "/" + notebook_path

    def get_notebook_base_url(self):
        return self.get_base_url() + self.get_wiki_path_for_notebook_path("")

    def get_folder_url(self, path):
        wiki_path = self.get_wiki_path_for_notebook_path(path)
        folder_path = wiki_path.rsplit("/", 1)[0] + "/"
        return self.get_base_url() + folder_path

    def get_breadcrumbs(self):
        breadcrumbs = [
            {"name": self.campaign.name, "url": self.campaign.get_absolute_url()},
            {"name": "Wiki", "url": self.get_base_url()},
        ]

        if not self.is_wiki_notebook():
            notebook_link = self.campaign.campaign_notebooks.filter(
                notebook=self.object
            ).first()
            breadcrumbs.append({
                "name": self.object.name,
                "url": self.get_base_url() + notebook_link.slug + "/",
            })

        if hasattr(self, 'version') and self.version:
            base_url = self.get_notebook_base_url()
            path_parts = self.version.path.split("/")
            filename_parts = self.version.filename.split("/")

            for i in range(len(path_parts)):
                is_last = i == len(path_parts) - 1
                if is_last:
                    name = self.version.display_name
                    url = base_url + "/".join(path_parts)
                else:
                    name = filename_parts[i]
                    url = base_url + "/".join(path_parts[:i + 1]) + "/"
                breadcrumbs.append({"name": name, "url": url})

        return breadcrumbs


class CampaignWikiView(CampaignWikiMixin, NotebookIndexView):
    template_name = "campaigns/wiki.html"

    def dispatch(self, request, *args, **kwargs):
        self.object = self.get_object()
        error = self.check_permissions(request)
        if error:
            return error
        return super(NotebookIndexView, self).dispatch(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        contents = self.get_contents()
        index_page = self.get_index_page()

        if self.is_empty_folder(contents, index_page):
            return HttpResponse(status=HTTPStatus.NOT_FOUND)

        if index_page:
            index_version = self.get_index_version(index_page)
            if index_version is None:
                return HttpResponse(status=HTTPStatus.NOT_FOUND)
        else:
            index_version = None

        context = self.get_context_data(contents, index_page, index_version)
        return self.render_to_response(context)

    def get_context_data(self, contents, index_page, index_version):
        context = super().get_context_data(contents, index_page, index_version)
        context.update({
            "campaign": self.campaign,
            "notebook": self.object,
            "is_wiki_notebook": self.is_wiki_notebook(),
            "base_url": self.get_base_url(),
        })
        return context


class CampaignWikiPageView(CampaignWikiMixin, NotebookPageView):
    template_name = "campaigns/wiki_page.html"

    def dispatch(self, request, *args, **kwargs):
        self.object = self.get_object()
        error = self.check_permissions(request)
        if error:
            return error

        if not self.path or self.path.endswith("/"):
            return CampaignWikiView.as_view()(request, *args, **kwargs)

        if request.method == "POST" or "edit" in request.GET:
            return CampaignWikiPageEditView.as_view()(request, *args, **kwargs)

        return super(NotebookPageView, self).dispatch(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        self.page = self.get_page()
        self.version_number = request.GET.get("version")

        if self.page is None:
            return CampaignWikiPageEditView.as_view()(request, *args, **kwargs)

        try:
            self.version = self.page.get_version(self.version_number)
        except self.object.page_set.model.DoesNotExist:
            return HttpResponse(status=HTTPStatus.NOT_FOUND)

        if self.version.mime_type != "text/markdown":
            return HttpResponse(
                self.version.content.data,
                content_type=self.version.mime_type,
            )

        context = self.get_context_data()
        return self.render_to_response(context)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            "campaign": self.campaign,
            "notebook": self.object,
            "is_wiki_notebook": self.is_wiki_notebook(),
            "base_url": self.get_base_url(),
        })
        return context


class CampaignWikiPageEditView(CampaignWikiMixin, NotebookPageEditView):
    template_name = "campaigns/wiki_edit.html"

    def dispatch(self, request, *args, **kwargs):
        self.object = self.get_object()
        error = self.check_permissions(request)
        if error:
            return error

        self.path = self.notebook_path
        kwargs["path"] = self.notebook_path
        kwargs["username"] = self.object.owner.username
        kwargs["slug"] = self.object.slug
        return NotebookPageEditView.dispatch(self, request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            "campaign": self.campaign,
            "notebook": self.object,
            "is_wiki_notebook": self.is_wiki_notebook(),
            "base_url": self.get_base_url(),
            "form_action": reverse("campaign_wiki_page", kwargs={
                "username": self.campaign.owner.username,
                "slug": self.campaign.slug,
                "path": self.wiki_path,
            }),
            "breadcrumbs": self.get_breadcrumbs(),
        })
        return context

    def get_breadcrumbs(self):
        breadcrumbs = super().get_breadcrumbs()

        if not self.version:
            page_name = self.notebook_path.split("/")[-1]
            if not page_name:
                page_name = "new"
            breadcrumbs.append({
                "name": page_name,
                "url": self.get_base_url() + self.wiki_path,
            })

        if self.page:
            breadcrumbs.append({"name": "edit"})
        else:
            breadcrumbs.append({"name": "create"})
        return breadcrumbs

    def get_success_redirect(self, new_version):
        new_path = new_version.path
        wiki_path = self.get_wiki_path_for_notebook_path(new_path)

        if new_path.endswith("/index") or new_path == "index":
            return redirect(self.get_base_url() + wiki_path.rsplit("/", 1)[0] + "/")

        return redirect(reverse("campaign_wiki_page", kwargs={
            "username": self.campaign.owner.username,
            "slug": self.campaign.slug,
            "path": wiki_path,
        }))
