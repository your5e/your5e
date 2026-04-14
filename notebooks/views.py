from http import HTTPStatus

from django.core.exceptions import ValidationError
from django.db.models import OuterRef, Subquery
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import get_object_or_404, redirect, render
from django.template.response import TemplateResponse
from django.urls import reverse
from django.views import View
from django.views.generic import TemplateView
from django.views.generic.edit import FormView

from campaigns.models import Campaign, CampaignNotebook
from campaigns.permissions import CampaignPermissions
from notebooks.forms import CollaboratorForm, NotebookCreateForm, PageForm
from notebooks.mime import guess_mime_type
from notebooks.models import Notebook, NotebookPermission
from notebooks.permissions import NotebookPermissions
from users.models import User
from wikis.models import Page, Version

MAX_UPLOAD_SIZE = 2 * 1024 * 1024


class NotebookFromURLMixin:
    """Provides get_object() from URL kwargs (username, slug)."""

    def get_object(self):
        owner = get_object_or_404(User, username=self.kwargs['username'])
        return get_object_or_404(Notebook, owner=owner, slug=self.kwargs['slug'])


class NotebookFromPOSTMixin:
    """Provides get_object() from POST body (notebook pk)."""

    def get_object(self):
        return get_object_or_404(Notebook, pk=self.request.POST.get("notebook"))


class NotebookContextMixin:
    """
    Provides common notebook context.
    Requires self.object to be set (a Notebook instance).
    """

    def get_base_url(self):
        return self.object.get_absolute_url()

    def get_create_page_url(self):
        return reverse("notebook_create_page", kwargs={
            "username": self.object.owner.username,
            "slug": self.object.slug,
        })


class NotebookSettingsMixin(NotebookContextMixin):
    def get_context_data(self, **kwargs):
        collaborators = NotebookPermission.objects.filter(
            notebook=self.object
        ).select_related("user")
        return {
            "notebook": self.object,
            "collaborators": collaborators,
            "visibility_choices": Notebook.Visibility.choices,
            "create_page_url": self.get_create_page_url(),
            **kwargs,
        }


class NotebookEditMixin(NotebookContextMixin):
    def get_edit_context(self, path, filename, version=None):
        if version:
            source = version
        else:
            source = Version(path=path, filename=filename)
        is_index = path == "index" or path.endswith("/index")

        if is_index:
            breadcrumbs = self.object.breadcrumbs_for(source)[:-1]
            parts = filename.split("/")
            if len(parts) >= 2:
                editing_name = parts[-2]
            else:
                editing_name = self.object.name
        else:
            breadcrumbs = self.object.breadcrumbs_for(source)
            editing_name = source.display_name

        return {
            "notebook": self.object,
            "breadcrumbs": breadcrumbs,
            "editing_name": editing_name,
            "editing_url": self.object.get_absolute_url() + path,
            "create_page_url": self.get_create_page_url(),
        }


class NotebookCreateView(View):
    def get_pending_collaborators(self, pending_pks, pending_roles):
        users = User.objects.in_bulk(pending_pks)
        return [
            (users[int(pk)], role)
            for pk, role in zip(pending_pks, pending_roles, strict=True)
            if int(pk) in users
        ]

    def get_context(
        self,
        form,
        collaborator_form,
        pending_pks,
        pending_roles,
        error=None,
        campaign_id=None,
    ):
        return {
            "form": form,
            "collaborator_form": collaborator_form,
            "pending_collaborators": self.get_pending_collaborators(
                pending_pks, pending_roles
            ),
            "error": error,
            "campaign_id": campaign_id,
        }

    def get(self, request):
        if not request.user.is_authenticated:
            return HttpResponse(status=HTTPStatus.UNAUTHORIZED)

        form = NotebookCreateForm()
        collaborator_form = CollaboratorForm()
        context = self.get_context(form, collaborator_form, [], [])
        return render(request, "notebooks/create.html", context)

    def post(self, request):
        if not request.user.is_authenticated:
            return HttpResponse(status=HTTPStatus.UNAUTHORIZED)

        pending_pks = request.POST.getlist("pending_pk")
        pending_roles = request.POST.getlist("pending_role")
        campaign_id = request.POST.get("campaign")

        for pk in request.POST.getlist("prepopulate_collaborator"):
            if pk not in pending_pks:
                pending_pks.append(pk)
                pending_roles.append(NotebookPermission.Role.VIEWER)

        actions = ("add_collaborator", "remove_collaborator", "create")
        is_initial = not any(action in request.POST for action in actions)
        if is_initial:
            form = NotebookCreateForm(initial={"name": request.POST.get("name")})
        else:
            form = NotebookCreateForm(request.POST)
        collaborator_form = CollaboratorForm()
        error = None

        if "add_collaborator" in request.POST:
            collaborator_form = CollaboratorForm(request.POST)
            if collaborator_form.is_valid():
                username = collaborator_form.cleaned_data["collaborator_username"]
                role = collaborator_form.cleaned_data["collaborator_role"]
                try:
                    user = User.objects.get(username=username)
                    if str(user.pk) not in pending_pks:
                        pending_pks.append(str(user.pk))
                        pending_roles.append(role)
                    collaborator_form = CollaboratorForm()
                except User.DoesNotExist:
                    error = f"User '{username}' not found"

            context = self.get_context(
                form,
                collaborator_form,
                pending_pks,
                pending_roles,
                error,
                campaign_id,
            )
            return render(request, "notebooks/create.html", context)

        if "remove_collaborator" in request.POST:
            remove_pk = request.POST.get("remove_collaborator")
            try:
                idx = pending_pks.index(remove_pk)
                pending_pks.pop(idx)
                pending_roles.pop(idx)
            except ValueError:
                pass
            context = self.get_context(
                form,
                collaborator_form,
                pending_pks,
                pending_roles,
                campaign_id=campaign_id,
            )
            return render(request, "notebooks/create.html", context)

        if "create" in request.POST:
            if not form.is_valid():
                context = self.get_context(
                    form,
                    collaborator_form,
                    pending_pks,
                    pending_roles,
                    campaign_id=campaign_id,
                )
                return render(request, "notebooks/create.html", context)

            notebook = Notebook.objects.create(
                name=form.cleaned_data["name"],
                owner=request.user,
                visibility=form.cleaned_data["visibility"],
            )

            for user, role in self.get_pending_collaborators(
                pending_pks, pending_roles
            ):
                NotebookPermission.objects.create(
                    notebook=notebook,
                    user=user,
                    role=role,
                )

            if campaign_id:
                campaign = Campaign.objects.filter(pk=campaign_id).first()
                if campaign and CampaignPermissions.can_view(campaign, request.user):
                    CampaignNotebook.objects.create(
                        campaign=campaign,
                        notebook=notebook,
                        linked_by=request.user,
                    )

            description = form.cleaned_data["description"]
            index_page = Page.objects.create(wiki=notebook)
            index_page.update(
                filename="index.md",
                mime_type="text/markdown",
                data=(description).encode("utf-8"),
                created_by=request.user,
            )

            return redirect(notebook)

        context = self.get_context(
            form,
            collaborator_form,
            pending_pks,
            pending_roles,
            campaign_id=campaign_id,
        )
        return render(request, "notebooks/create.html", context)


class NotebookIndexView(NotebookContextMixin, NotebookFromURLMixin, TemplateView):
    template_name = "notebooks/notebook.html"
    not_found_template = "notebooks/not_found.html"

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        self.path = kwargs.get("path", "")

    @NotebookPermissions.view_required
    def get(self, request, *args, **kwargs):
        contents = self.get_contents()
        index_page = self.get_index_page()

        if self.is_empty_folder(contents, index_page):
            return self.handle_not_found()

        if index_page:
            index_version = self.get_index_version(index_page)
            if index_version is None:
                return HttpResponse(status=HTTPStatus.NOT_FOUND)
        else:
            index_version = None

        context = self.get_context_data(contents, index_page, index_version)
        return self.render_to_response(context)

    def get_index_path(self):
        return (self.path + "/index").lstrip("/")

    def get_index_page(self):
        try:
            return self.object.get_page(path=self.get_index_path())
        except Page.DoesNotExist:
            return None

    def get_index_version(self, index_page):
        try:
            return index_page.get_version(self.request.GET.get("index_version"))
        except Page.DoesNotExist:
            return None

    def get_contents(self):
        contents = self.object.contents_in(self.path)
        index_path = self.get_index_path()
        files = [f for f in contents["files"] if f.path != index_path]
        return {
            "folders": contents["folders"],
            "files": files,
        }

    def is_empty_folder(self, contents, index_page):
        return (
            not contents["files"]
            and not contents["folders"]
            and index_page is None
        )

    def get_breadcrumbs(self):
        if self.path:
            representative = self.object.latest_versions().filter(
                path__startswith=self.path + "/"
            ).first()
            path_depth = len(self.path.split("/"))
            return self.object.breadcrumbs_for(representative)[:path_depth + 1]
        return [{"name": self.object.name, "url": self.get_base_url()}]

    def get_current_page(self, breadcrumbs):
        if self.path:
            return breadcrumbs[-1]["name"]
        return ""

    def get_recent_pages(self):
        if self.path:
            return None
        return self.object.latest_versions().order_by("-created_at")[:5]

    def get_create_page_url(self):
        url = reverse("notebook_create_page", kwargs={
            "username": self.object.owner.username,
            "slug": self.object.slug,
        })
        if self.path:
            url += f"?folder={self.path}"
        return url

    def get_context_data(self, contents, index_page, index_version):
        breadcrumbs = self.get_breadcrumbs()

        context = {
            "notebook": self.object,
            "folders": contents["folders"],
            "files": contents["files"],
            "index_exists": index_page is not None,
            "breadcrumbs": breadcrumbs,
            "current_page": self.get_current_page(breadcrumbs),
            "create_base": (
                self.get_base_url() + (self.path + "/").lstrip("/")
            ),
            "create_page_url": self.get_create_page_url(),
        }

        context["recent_pages"] = self.get_recent_pages()

        if index_version:
            context["index_content"] = index_version.render(
                base_url=self.get_base_url()
            )
            context["index_version"] = index_version
            context["index_history"] = index_page.history()

        return context

    def handle_not_found(self):
        kwargs = dict(self.kwargs)
        kwargs["path"] = self.get_index_path()
        return NotebookPageEditView.as_view()(
            self.request, *self.args, **kwargs
        )


class NotebookSettingsView(NotebookSettingsMixin, NotebookFromURLMixin, TemplateView):
    template_name = "notebooks/settings.html"

    @NotebookPermissions.view_required
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["breadcrumbs"] = [
            {"name": self.object.name, "url": self.object.get_absolute_url()},
            {"name": "Settings"},
        ]
        context["is_owner"] = self.object.owner == self.request.user
        return context


class NotebookDeletedPagesView(NotebookContextMixin, NotebookFromURLMixin, View):
    @NotebookPermissions.edit_required
    def get(self, request, username, slug):
        deleted_pages = self.object.deleted_pages()
        breadcrumbs = [
            {"name": self.object.name, "url": self.object.get_absolute_url()},
            {"name": "Deleted pages"},
        ]
        return render(
            request,
            "notebooks/deleted.html",
            {
                "notebook": self.object,
                "deleted_pages": deleted_pages,
                "create_page_url": self.get_create_page_url(),
                "breadcrumbs": breadcrumbs,
            },
        )


class NotebookPageCreateView(NotebookEditMixin, NotebookFromURLMixin, View):
    @NotebookPermissions.edit_required
    def get(self, request, username, slug):
        folder = request.GET.get("folder", "")

        # find a unique "new-page" path
        base_path = (folder + "/new-page").lstrip("/")
        path = base_path
        counter = 2
        while True:
            try:
                self.object.get_page(path=path)
                path = f"{base_path}-{counter}"
                counter += 1
            except Page.DoesNotExist:
                break

        filename = self.object.suggest_filename(path)
        form = PageForm(initial={"filename": filename})

        context = self.get_edit_context(path, filename)
        context["breadcrumbs"].append({"name": "create"})
        context.update({
            "page": None,
            "version": None,
            "form": form,
            "history": [],
            "form_action": reverse("notebook_page", kwargs={
                "username": username,
                "slug": slug,
                "path": path,
            }),
        })

        return render(request, "notebooks/edit.html", context)


class NotebookUploadView(NotebookFromPOSTMixin, View):
    @NotebookPermissions.edit_required
    def post(self, request):
        uploaded_file = request.FILES.get("file")
        form_filename = request.POST.get("filename")
        if form_filename:
            filename = form_filename
        else:
            filename = uploaded_file.name

        if uploaded_file.size > MAX_UPLOAD_SIZE:
            return HttpResponse(status=HTTPStatus.BAD_REQUEST)

        mime_type = guess_mime_type(filename)

        try:
            page = self.object.get_page(filename=filename)
        except Page.DoesNotExist:
            page = Page.objects.create(wiki=self.object)

        page.update(
            filename=filename,
            mime_type=mime_type,
            data=uploaded_file.read(),
            created_by=request.user,
        )

        return redirect(self.object)


class NotebookRenameView(NotebookFromPOSTMixin, View):
    @NotebookPermissions.owner_required
    def post(self, request):
        name = request.POST.get("name")
        confirm = request.POST.get("confirm") == "true"

        if not name:
            return redirect(self.object)

        if name == self.object.name:
            return redirect(
                "notebook_settings",
                username=self.object.owner.username,
                slug=self.object.slug,
            )

        if not confirm:
            return render(request, "notebooks/confirm_rename.html", {
                "notebook": self.object,
                "name": name,
            })

        self.object.rename(name)
        return redirect(self.object)


class NotebookVisibilityView(NotebookFromPOSTMixin, View):
    @NotebookPermissions.owner_required
    def post(self, request):
        visibility = request.POST.get("visibility")
        confirm = request.POST.get("confirm") == "true"

        if not confirm:
            return render(request, "notebooks/confirm_visibility.html", {
                "notebook": self.object,
                "visibility": visibility,
            })

        self.object.visibility = visibility
        self.object.save()

        return redirect(self.object)


class NotebookDeleteView(NotebookFromPOSTMixin, View):
    @NotebookPermissions.owner_required
    def post(self, request):
        if "confirm" in request.POST or not self.object.has_content():
            owner_username = self.object.owner.username
            try:
                self.object.delete()
            except ValueError:
                return HttpResponse(status=HTTPStatus.FORBIDDEN)
            return redirect("profile", username=owner_username)

        breadcrumbs = [
            {"name": self.object.name, "url": self.object.get_absolute_url()},
            {"name": "delete"},
        ]
        return render(request, "notebooks/confirm_delete_notebook.html", {
            "notebook": self.object,
            "breadcrumbs": breadcrumbs,
        })


class NotebookPageDeleteView(NotebookFromPOSTMixin, View):
    @NotebookPermissions.edit_required
    def post(self, request):
        page = get_object_or_404(Page, pk=request.POST.get("page"))
        confirm = request.POST.get("confirm") == "true"

        if not confirm:
            return render(request, "notebooks/confirm_delete.html", {
                "notebook": self.object,
                "page": page,
            })

        page.soft_delete()

        return HttpResponseRedirect(
            self.object.get_folder_url(page.latest_version.path),
            status=HTTPStatus.SEE_OTHER,
        )


class NotebookPageRestoreView(NotebookContextMixin, View):
    def get_object(self):
        page_uuid = self.request.GET.get("page") or self.request.POST.get("page")
        self.page = get_object_or_404(Page, uuid=page_uuid)
        return self.page.wiki.notebook

    def get_page_url(self):
        return reverse("notebook_page", kwargs={
            "username": self.object.owner.username,
            "slug": self.object.slug,
            "path": self.page.latest_version.path,
        })

    def get_restore_context(self, form):
        breadcrumbs = self.object.breadcrumbs_for(self.page.latest_version)
        breadcrumbs.append({"name": "restore"})
        return {
            "notebook": self.object,
            "page": self.page,
            "form": form,
            "breadcrumbs": breadcrumbs,
            "create_page_url": self.get_create_page_url(),
        }

    @NotebookPermissions.edit_required
    def get(self, request):
        from notebooks.forms import RestoreForm

        if not self.page.deleted_at:
            return redirect(self.get_page_url())

        form = RestoreForm()
        return render(
            request,
            "notebooks/restore.html",
            self.get_restore_context(form),
        )

    @NotebookPermissions.edit_required
    def post(self, request):
        from notebooks.forms import RestoreForm

        if not self.page.deleted_at:
            return redirect(self.get_page_url())

        form = RestoreForm(request.POST)
        if not form.is_valid():
            return render(
                request,
                "notebooks/restore.html",
                self.get_restore_context(form),
                status=HTTPStatus.BAD_REQUEST,
            )

        filename = form.cleaned_data.get("filename") or None
        try:
            self.page.restore(filename=filename)
        except ValidationError as e:
            for message in e.messages:
                form.add_error("filename", message)
            return render(
                request,
                "notebooks/restore.html",
                self.get_restore_context(form),
                status=HTTPStatus.CONFLICT,
            )

        return redirect(self.object)


class NotebookCollaboratorsView(NotebookSettingsMixin, NotebookFromPOSTMixin, View):
    @NotebookPermissions.owner_required
    def post(self, request):
        confirm = request.POST.get("confirm") == "true"

        if "username" in request.POST:
            return self.handle_add(request, confirm)
        elif "remove" in request.POST:
            return self.handle_remove(request, confirm)
        elif "change_role" in request.POST:
            return self.handle_change_role(request, confirm)

        return redirect(self.object)

    def render_settings_with_error(self, request, error):
        return render(
            request,
            "notebooks/settings.html",
            self.get_context_data(error=error, is_owner=True),
        )

    def handle_add(self, request, confirm):
        username = request.POST.get("username")
        role = request.POST.get("role")

        if not username:
            return self.render_settings_with_error(request, "No username provided")

        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            return self.render_settings_with_error(
                request, f"User '{username}' not found"
            )

        if not confirm:
            return render(request, "notebooks/confirm_collaborator.html", {
                "notebook": self.object,
                "action": "add",
                "target_user": user,
                "role": role,
            })

        NotebookPermission.objects.create(
            notebook=self.object,
            user=user,
            role=role,
        )

        return redirect(self.object)

    def handle_remove(self, request, confirm):
        user_pk = request.POST.get("remove")
        user = get_object_or_404(User, pk=user_pk)

        wiki_link = CampaignNotebook.objects.filter(
            notebook=self.object, is_wiki=True
        ).first()
        if wiki_link and wiki_link.campaign.players.filter(pk=user.pk).exists():
            return HttpResponse(status=HTTPStatus.FORBIDDEN)

        if not confirm:
            return render(request, "notebooks/confirm_collaborator.html", {
                "notebook": self.object,
                "action": "remove",
                "target_user": user,
            })

        NotebookPermission.objects.filter(
            notebook=self.object,
            user=user,
        ).delete()

        return redirect(self.object)

    def handle_change_role(self, request, confirm):
        user_pk = request.POST.get("change_role")
        role = request.POST.get("role")
        user = get_object_or_404(User, pk=user_pk)

        if role == NotebookPermission.Role.VIEWER:
            wiki_link = CampaignNotebook.objects.filter(
                notebook=self.object, is_wiki=True
            ).first()
            if wiki_link and wiki_link.campaign.players.filter(pk=user.pk).exists():
                return HttpResponse(status=HTTPStatus.FORBIDDEN)

        if not confirm:
            return render(request, "notebooks/confirm_collaborator.html", {
                "notebook": self.object,
                "action": "change_role",
                "target_user": user,
                "role": role,
            })

        NotebookPermission.objects.filter(
            notebook=self.object,
            user=user,
        ).update(role=role)

        return redirect(self.object)


class NotebookPageMixin(NotebookFromURLMixin):

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        self.path = kwargs.get("path", "")

    def get_page(self):
        try:
            return self.object.get_page(path=self.path)
        except Page.DoesNotExist:
            return None


class NotebookPageEditView(NotebookEditMixin, NotebookPageMixin, FormView):
    template_name = "notebooks/edit.html"
    form_class = PageForm

    @NotebookPermissions.view_required
    def dispatch(self, request, *args, **kwargs):
        self.page = self.get_page()

        if not NotebookPermissions.can_edit(self.object, request.user):
            if request.method == "GET" and self.page is None:
                return TemplateResponse(
                    request,
                    "notebooks/not_found.html",
                    {"notebook": self.object, "path": self.path},
                    status=HTTPStatus.NOT_FOUND,
                )
            return NotebookPermissions.forbidden_response(request)

        if self.page:
            self.version = self.page.latest_version
            self.mime_type = self.version.mime_type
        else:
            self.version = None
            self.mime_type = "text/markdown"
        return super().dispatch(request, *args, **kwargs)

    def get_initial(self):
        if self.page:
            content = self.version.content.data
            if self.version.mime_type.startswith("text/"):
                content = content.decode("utf-8")
            else:
                content = ""
            filename = self.version.filename
            if filename.lower().endswith(".md"):
                filename = filename[:-3]
            return {"filename": filename, "content": content}
        return {"filename": self.object.suggest_filename(self.path)}

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["form_action"] = reverse("notebook_page", kwargs={
            "username": self.kwargs["username"],
            "slug": self.kwargs["slug"],
            "path": self.path,
        })
        if self.page:
            edit_context = self.get_edit_context(
                self.version.path, self.version.filename, self.version
            )
            edit_context["breadcrumbs"].append({"name": "edit"})
            context.update(edit_context)
            context["page"] = self.page
            context["version"] = self.version
            context["history"] = self.page.history()
        else:
            filename = self.object.suggest_filename(self.path)
            edit_context = self.get_edit_context(self.path, filename)
            edit_context["breadcrumbs"].append({"name": "create"})
            context.update(edit_context)
            context["page"] = None
            context["version"] = None
            context["history"] = []
        return context

    def render_to_response(self, context, **response_kwargs):
        if self.page is None and self.request.method == "GET":
            response_kwargs["status"] = HTTPStatus.NOT_FOUND
        return super().render_to_response(context, **response_kwargs)

    def form_valid(self, form):
        filename = self.get_filename(form)
        if filename is None:
            form.add_error("filename", "Filename is required")
            return self.form_invalid(form)

        content = form.cleaned_data.get("content", "")
        if not content and self.page is None:
            return self.handle_empty_create()

        return self.save_page(form, filename, content)

    def form_invalid(self, form):
        return self.render_to_response(
            self.get_context_data(form=form),
            status=HTTPStatus.BAD_REQUEST,
        )

    def get_filename(self, form):
        filename = form.cleaned_data["filename"].strip()
        if filename:
            if "/" not in filename:
                directory = "/".join(self.path.split("/")[:-1])
                if directory:
                    filename = f"{directory}/{filename}"
            if self.mime_type == "text/markdown":
                if not filename.lower().endswith(".md"):
                    filename = f"{filename}.md"
            return filename
        if self.version:
            return self.version.filename
        return None

    def get_folder_url(self, path):
        return self.object.get_folder_url(path)

    def handle_empty_create(self):
        if self.path.endswith("/index"):
            return redirect(self.get_folder_url(self.path))
        return redirect(self.request.path)

    def save_page(self, form, filename, content):
        data = content.encode("utf-8")
        page = self.page

        if page is None:
            page = Page.objects.create(wiki=self.object)

        try:
            new_version = page.update(
                filename=filename,
                mime_type=self.mime_type,
                data=data,
                created_by=self.request.user,
            )
        except ValidationError as e:
            return self.handle_validation_error(e, form, page)

        return self.get_success_redirect(new_version)

    def handle_validation_error(self, error, form, page):
        self.page = page
        self.version = page.latest_version
        for message in error.messages:
            if "already exists" in message:
                conflict_path = (
                    message
                    .removeprefix("Path '")
                    .removesuffix("' already exists.")
                )
                context = self.get_context_data(form=form)
                context["conflict_filename"] = form.cleaned_data["filename"]
                context["conflict_url"] = reverse("notebook_page", kwargs={
                    "username": self.kwargs["username"],
                    "slug": self.kwargs["slug"],
                    "path": conflict_path,
                })
                return self.render_to_response(context, status=HTTPStatus.CONFLICT)
            form.add_error(None, message)
        return self.render_to_response(
            self.get_context_data(form=form),
            status=HTTPStatus.CONFLICT,
        )

    def get_success_redirect(self, new_version):
        new_path = new_version.path
        if new_path.endswith("/index") or new_path == "index":
            return redirect(self.object.get_folder_url(new_path))
        return redirect(reverse("notebook_page", kwargs={
            "username": self.kwargs["username"],
            "slug": self.kwargs["slug"],
            "path": new_path,
        }))


class NotebookPageView(NotebookContextMixin, NotebookPageMixin, TemplateView):
    template_name = "notebooks/page.html"
    not_found_template = "notebooks/not_found.html"

    @NotebookPermissions.view_required
    def dispatch(self, request, *args, **kwargs):
        if self.path.endswith(".md"):
            return self.redirect_md_extension()

        if request.method == "POST" or "edit" in request.GET:
            return NotebookPageEditView.as_view()(request, *args, **kwargs)

        return super().dispatch(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        self.page = self.get_page()
        self.version_number = request.GET.get("version")

        if self.page is None:
            return self.handle_not_found()

        try:
            self.version = self.page.get_version(self.version_number)
        except Page.DoesNotExist:
            return HttpResponse(status=HTTPStatus.NOT_FOUND)

        if self.version.mime_type != "text/markdown":
            return HttpResponse(
                self.version.content.data,
                content_type=self.version.mime_type,
            )

        return super().get(request, *args, **kwargs)

    def get_breadcrumbs(self):
        return self.object.breadcrumbs_for(self.version)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            "notebook": self.object,
            "page": self.version,
            "breadcrumbs": self.get_breadcrumbs(),
            "content": self.version.render(base_url=self.get_base_url()),
            "history": self.page.history(),
            "is_old_version": self.version.number != self.page.latest_version.number,
            "create_page_url": self.get_create_page_url(),
        })
        return context

    def redirect_md_extension(self):
        url = reverse("notebook_page", kwargs={
            "username": self.kwargs["username"],
            "slug": self.kwargs["slug"],
            "path": self.path[:-3],
        })
        return redirect(url, permanent=True)

    def handle_not_found(self):
        return NotebookPageEditView.as_view()(
            self.request, *self.args, **self.kwargs
        )


class NotebookDescriptionMixin:
    def get_notebook_descriptions(self, notebooks):
        index_versions = Version.objects.filter(
                page__wiki__in=notebooks,
                path="index",
                page__deleted_at__isnull=True,
                number=Subquery(
                    Version.objects.filter(page=OuterRef("page"))
                        .order_by("-number")
                        .values("number")[:1]
                )
            ).select_related("content", "page")

        descriptions = {}
        for version in index_versions:
            fm = version.frontmatter()
            if "notebook" in fm:
                descriptions[version.page.wiki_id] = fm["notebook"]

        return descriptions


class NotebookListView(NotebookDescriptionMixin, TemplateView):
    template_name = "notebooks/list.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        all_public = (
            Notebook.objects
                .filter(visibility=Notebook.Visibility.PUBLIC)
                .order_by("name")
                .select_related("owner")
        )

        all_public_list = []
        system_notebooks = []
        public_notebooks = []
        for nb in all_public:
            all_public_list.append(nb)
            if nb.owner.username == "your5e":
                system_notebooks.append(nb)
            else:
                public_notebooks.append(nb)

        if self.request.user.is_authenticated:
            shared_notebooks = (
                Notebook.objects
                    .filter(visibility=Notebook.Visibility.INTERNAL)
                    .order_by("name")
                    .select_related("owner")
            )

            all_notebooks = all_public_list + list(shared_notebooks)
        else:
            shared_notebooks = None
            all_notebooks = all_public_list

        descriptions = self.get_notebook_descriptions(all_notebooks)

        context["system_notebooks"] = [
            (nb, descriptions.get(nb.pk))
                for nb in system_notebooks
        ]
        context["public_notebooks"] = [
            (nb, descriptions.get(nb.pk))
                for nb in public_notebooks
        ]
        if shared_notebooks is not None:
            context["shared_notebooks"] = [
                (nb, descriptions.get(nb.pk))
                    for nb in shared_notebooks
            ]

        return context


class NotebookUserListView(NotebookDescriptionMixin, TemplateView):
    template_name = "notebooks/user_list.html"

    def dispatch(self, request, *args, **kwargs):
        self.owner = get_object_or_404(User, username=kwargs["username"])
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["owner"] = self.owner

        if self.request.user.is_authenticated:
            viewer = self.request.user
        else:
            viewer = None

        users_notebooks = (
            Notebook.visible_to(viewer, self.owner)
                .order_by("name")
                .select_related("owner")
        )

        if not self.request.user.is_authenticated:
            # anonymous only gets to see public notebooks
            users_notebooks = users_notebooks.filter(
                visibility=Notebook.Visibility.PUBLIC
            )

        users_notebooks_list = list(users_notebooks)

        if self.request.user == self.owner:
            shared_with_owner = (
                Notebook.objects
                    .filter(notebookpermission__user=self.owner)
                    .exclude(owner=self.owner)
                    .order_by("name")
                    .select_related("owner")
            )
            shared_with_owner_list = list(shared_with_owner)
            all_notebooks = users_notebooks_list + shared_with_owner_list
        else:
            shared_with_owner_list = None
            all_notebooks = users_notebooks_list

        descriptions = self.get_notebook_descriptions(all_notebooks)

        context["users_notebooks"] = [
            (nb, descriptions.get(nb.pk))
                for nb in users_notebooks_list
        ]
        if shared_with_owner_list is not None:
            context["shared_notebooks"] = [
                (nb, descriptions.get(nb.pk))
                    for nb in shared_with_owner_list
            ]

        return context
