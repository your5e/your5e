import mimetypes
from http import HTTPStatus

from django.core.exceptions import ValidationError
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views import View

from campaigns.models import Campaign, CampaignNotebook
from campaigns.permissions import CampaignPermissions
from notebooks.forms import CollaboratorForm, NotebookCreateForm, PageForm
from notebooks.models import Notebook, NotebookPermission
from notebooks.permissions import NotebookPermissions
from users.models import User
from wikis.models import Page, Version

MIME_TYPE_FALLBACKS = {
    ".md": "text/markdown",
    ".markdown": "text/markdown",
}
DEFAULT_MIME_TYPE = "application/octet-stream"
MAX_UPLOAD_SIZE = 2 * 1024 * 1024


class NotebookReadMixin:
    def get_object(self):
        owner = get_object_or_404(User, username=self.kwargs['username'])
        return get_object_or_404(Notebook, owner=owner, slug=self.kwargs['slug'])


class NotebookWriteMixin:
    def get_object(self):
        return get_object_or_404(Notebook, pk=self.request.POST.get("notebook"))


class NotebookSettingsMixin:
    def get_context_data(self, **kwargs):
        collaborators = NotebookPermission.objects.filter(
            notebook=self.object
        ).select_related("user")
        create_page_url = reverse("notebook_create_page", kwargs={
            "username": self.object.owner.username,
            "slug": self.object.slug,
        })
        return {
            "notebook": self.object,
            "collaborators": collaborators,
            "visibility_choices": Notebook.Visibility.choices,
            "create_page_url": create_page_url,
            **kwargs,
        }


class NotebookEditMixin:
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

        create_page_url = reverse("notebook_create_page", kwargs={
            "username": self.object.owner.username,
            "slug": self.object.slug,
        })

        return {
            "notebook": self.object,
            "breadcrumbs": breadcrumbs,
            "editing_name": editing_name,
            "editing_url": self.object.get_absolute_url() + path,
            "create_page_url": create_page_url,
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


class NotebookView(NotebookReadMixin, View):
    @NotebookPermissions.view_required
    def get(self, request, username, slug, path=""):
        contents = self.object.contents_in(path)

        # index.md is rendered inline, exclude from the file list
        index_path = (path + "/index").lstrip("/")
        files = [
            f for f in contents["files"]
                if f.path != index_path
        ]

        index_exists = False
        try:
            index_page = self.object.get_page(path=index_path)
            index_exists = True
        except Page.DoesNotExist:
            index_page = None

        # an index only "exists" if there is content below
        if not files and not contents["folders"] and not index_exists:
            context = {"notebook": self.object, "path": path}
            if NotebookPermissions.can_edit(self.object, request.user):
                filename = self.object.suggest_filename(index_path)
                context["form"] = PageForm(initial={"filename": filename})
                context["form_action"] = reverse("notebook_page", kwargs={
                    "username": username,
                    "slug": slug,
                    "path": index_path,
                })
            return render(
                request,
                "notebooks/not_found.html",
                context,
                status=HTTPStatus.NOT_FOUND,
            )

        if path:
            representative = self.object.latest_versions().filter(
                path__startswith=path + "/"
            ).first()
            path_depth = len(path.split("/"))
            breadcrumbs = self.object.breadcrumbs_for(representative)[:path_depth + 1]
            current_page = breadcrumbs[-1]["name"]
        else:
            current_page = ""
            breadcrumbs = [
                {"name": self.object.name, "url": self.object.get_absolute_url()},
            ]

        create_page_url = reverse("notebook_create_page", kwargs={
            "username": self.object.owner.username,
            "slug": self.object.slug,
        })
        if path:
            create_page_url += f"?folder={path}"

        context = {
            "notebook": self.object,
            "folders": contents["folders"],
            "files": files,
            "index_exists": index_exists,
            "breadcrumbs": breadcrumbs,
            "current_page": current_page,
            "create_base": self.object.get_absolute_url() + (path + "/").lstrip("/"),
            "create_page_url": create_page_url,
        }

        if not path:
            context["recent_pages"] = (
                self.object.latest_versions().order_by("-created_at")[:5]
            )

        if index_page:
            try:
                index_version = index_page.get_version(
                    request.GET.get("index_version")
                )
            except Page.DoesNotExist:
                return HttpResponse(status=HTTPStatus.NOT_FOUND)
            context["index_content"] = index_version.render(
                base_url=self.object.get_absolute_url()
            )
            context["index_version"] = index_version
            context["index_history"] = index_page.history()

        return render(request, "notebooks/notebook.html", context)


class NotebookSettingsView(NotebookSettingsMixin, NotebookReadMixin, View):
    @NotebookPermissions.owner_required
    def get(self, request, username, slug):
        breadcrumbs = [
            {"name": self.object.name, "url": self.object.get_absolute_url()},
            {"name": "Settings"},
        ]
        return render(
            request,
            "notebooks/settings.html",
            self.get_context_data(breadcrumbs=breadcrumbs),
        )


class NotebookDeletedPagesView(NotebookReadMixin, View):
    @NotebookPermissions.edit_required
    def get(self, request, username, slug):
        deleted_pages = self.object.deleted_pages()
        create_page_url = reverse("notebook_create_page", kwargs={
            "username": self.object.owner.username,
            "slug": self.object.slug,
        })
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
                "create_page_url": create_page_url,
                "breadcrumbs": breadcrumbs,
            },
        )


class NotebookPageCreateView(NotebookEditMixin, NotebookReadMixin, View):
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


class NotebookUploadView(NotebookWriteMixin, View):
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

        mime_type, _ = mimetypes.guess_type(filename)
        if mime_type is None:
            if "." in filename:
                ext = "." + filename.rsplit(".", 1)[-1].lower()
            else:
                ext = ""
            mime_type = MIME_TYPE_FALLBACKS.get(ext, DEFAULT_MIME_TYPE)

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


class NotebookRenameView(NotebookWriteMixin, View):
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


class NotebookVisibilityView(NotebookWriteMixin, View):
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


class NotebookDeleteView(NotebookWriteMixin, View):
    @NotebookPermissions.owner_required
    def post(self, request):
        if "confirm" in request.POST or not self.object.has_content():
            owner_username = self.object.owner.username
            self.object.delete()
            return redirect("profile", username=owner_username)

        breadcrumbs = [
            {"name": self.object.name, "url": self.object.get_absolute_url()},
            {"name": "delete"},
        ]
        return render(request, "notebooks/confirm_delete_notebook.html", {
            "notebook": self.object,
            "breadcrumbs": breadcrumbs,
        })


class NotebookPageDeleteView(NotebookWriteMixin, View):
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


class NotebookPageRestoreView(View):
    def get_page_and_notebook(self, request):
        page_uuid = request.GET.get("page") or request.POST.get("page")
        page = get_object_or_404(Page, uuid=page_uuid)
        notebook = page.wiki.notebook
        return page, notebook

    def check_permission(self, request, notebook):
        if not request.user.is_authenticated:
            return HttpResponse(status=HTTPStatus.UNAUTHORIZED)
        if not NotebookPermissions.can_edit(notebook, request.user):
            return HttpResponse(status=HTTPStatus.FORBIDDEN)
        return None

    def get_page_url(self, notebook, page):
        return reverse("notebook_page", kwargs={
            "username": notebook.owner.username,
            "slug": notebook.slug,
            "path": page.latest_version.path,
        })

    def get_restore_context(self, notebook, page, form):
        breadcrumbs = notebook.breadcrumbs_for(page.latest_version)
        breadcrumbs.append({"name": "restore"})
        create_page_url = reverse("notebook_create_page", kwargs={
            "username": notebook.owner.username,
            "slug": notebook.slug,
        })
        return {
            "notebook": notebook,
            "page": page,
            "form": form,
            "breadcrumbs": breadcrumbs,
            "create_page_url": create_page_url,
        }

    def get(self, request):
        from notebooks.forms import RestoreForm

        page, notebook = self.get_page_and_notebook(request)
        if not page.deleted_at:
            return redirect(self.get_page_url(notebook, page))

        denied = self.check_permission(request, notebook)
        if denied:
            return denied

        form = RestoreForm()
        return render(
            request,
            "notebooks/restore.html",
            self.get_restore_context(notebook, page, form),
        )

    def post(self, request):
        from notebooks.forms import RestoreForm

        page, notebook = self.get_page_and_notebook(request)
        if not page.deleted_at:
            return redirect(self.get_page_url(notebook, page))

        denied = self.check_permission(request, notebook)
        if denied:
            return denied

        form = RestoreForm(request.POST)
        if not form.is_valid():
            return render(
                request,
                "notebooks/restore.html",
                self.get_restore_context(notebook, page, form),
                status=HTTPStatus.BAD_REQUEST,
            )

        filename = form.cleaned_data.get("filename") or None
        try:
            page.restore(filename=filename)
        except ValidationError as e:
            for message in e.messages:
                form.add_error("filename", message)
            return render(
                request,
                "notebooks/restore.html",
                self.get_restore_context(notebook, page, form),
                status=HTTPStatus.CONFLICT,
            )

        return redirect(notebook)


class NotebookCollaboratorsView(NotebookSettingsMixin, NotebookWriteMixin, View):
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

    def handle_add(self, request, confirm):
        username = request.POST.get("username")
        role = request.POST.get("role")

        if not username:
            return render(
                request,
                "notebooks/settings.html",
                self.get_context_data(error="No username provided"),
            )

        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            return render(
                request,
                "notebooks/settings.html",
                self.get_context_data(error=f"User '{username}' not found"),
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


class NotebookPageView(NotebookEditMixin, NotebookReadMixin, View):
    @NotebookPermissions.view_required
    def get(self, request, username, slug, path):
        if path.endswith(".md"):
            url = reverse("notebook_page", kwargs={
                "username": username,
                "slug": slug,
                "path": path[:-3],
            })
            return redirect(url, permanent=True)

        try:
            page = self.object.get_page(path=path)
        except Page.DoesNotExist:
            if not NotebookPermissions.can_edit(self.object, request.user):
                return render(
                    request,
                    "notebooks/not_found.html",
                    {"notebook": self.object, "path": path},
                    status=HTTPStatus.NOT_FOUND,
                )

            filename = self.object.suggest_filename(path)
            form = PageForm(initial={"filename": filename})

            context = self.get_edit_context(path, filename)
            context["breadcrumbs"].append({"name": "create"})
            context.update({
                "page": None,
                "version": None,
                "form": form,
                "history": [],
            })
            return render(
                request,
                "notebooks/edit.html",
                context,
                status=HTTPStatus.NOT_FOUND,
            )

        if "edit" in request.GET:
            if not request.user.is_authenticated:
                return HttpResponse(status=HTTPStatus.UNAUTHORIZED)
            if not NotebookPermissions.can_edit(self.object, request.user):
                return HttpResponse(status=HTTPStatus.FORBIDDEN)

            version = page.latest_version
            content = version.content.data
            if version.mime_type.startswith("text/"):
                content = content.decode("utf-8")
            else:
                content = ""

            filename = version.filename
            if filename.lower().endswith(".md"):
                filename = filename[:-3]

            form = PageForm(initial={"filename": filename, "content": content})

            context = self.get_edit_context(version.path, version.filename, version)
            context["breadcrumbs"].append({"name": "edit"})
            context.update({
                "page": page,
                "version": version,
                "form": form,
                "history": page.history(),
            })
            return render(request, "notebooks/edit.html", context)

        history = page.history()
        version_number = request.GET.get("version")
        try:
            version = page.get_version(version_number)
        except Page.DoesNotExist:
            return HttpResponse(status=HTTPStatus.NOT_FOUND)
        is_old_version = version_number is not None

        content = version.render(base_url=self.object.get_absolute_url())

        if isinstance(content, str):
            breadcrumbs = self.object.breadcrumbs_for(version)

            create_page_url = reverse("notebook_create_page", kwargs={
                "username": self.object.owner.username,
                "slug": self.object.slug,
            })
            return render(request, "notebooks/page.html", {
                "notebook": self.object,
                "page": version,
                "breadcrumbs": breadcrumbs,
                "content": content,
                "history": history,
                "is_old_version": is_old_version,
                "create_page_url": create_page_url,
            })
        return HttpResponse(content, content_type=version.mime_type)

    @NotebookPermissions.edit_required
    def post(self, request, username, slug, path):
        try:
            page = self.object.get_page(path=path)
            version = page.latest_version
            mime_type = version.mime_type
            default_filename = version.filename
            current_page = version.display_name
        except Page.DoesNotExist:
            page = None
            version = None
            mime_type = "text/markdown"
            default_filename = None
            current_page = path

        form = PageForm(request.POST)
        create_page_url = reverse("notebook_create_page", kwargs={
            "username": self.object.owner.username,
            "slug": self.object.slug,
        })
        if not form.is_valid():
            return render(
                request,
                "notebooks/edit.html",
                {
                    "notebook": self.object,
                    "page": page,
                    "version": version,
                    "form": form,
                    "current_page": current_page,
                    "create_page_url": create_page_url,
                },
                status=HTTPStatus.BAD_REQUEST,
            )

        filename = form.cleaned_data["filename"].strip()
        if filename:
            if "/" not in filename:
                directory = "/".join(path.split("/")[:-1])
                if directory:
                    filename = f"{directory}/{filename}"
            if mime_type == "text/markdown":
                if not filename.lower().endswith(".md"):
                    filename = f"{filename}.md"
        elif default_filename:
            filename = default_filename
        else:
            form.add_error("filename", "Filename is required")
            return render(
                request,
                "notebooks/edit.html",
                {
                    "notebook": self.object,
                    "page": page,
                    "version": version,
                    "form": form,
                    "current_page": current_page,
                    "create_page_url": create_page_url,
                },
                status=HTTPStatus.BAD_REQUEST,
            )

        content = form.cleaned_data.get("content", "")
        if not content and page is None:
            if path.endswith("/index"):
                return redirect(self.object.get_folder_url(path))
            return redirect(request.path)
        data = content.encode("utf-8")

        if page is None:
            page = Page.objects.create(wiki=self.object)

        try:
            new_version = page.update(
                filename=filename,
                mime_type=mime_type,
                data=data,
                created_by=request.user,
            )
        except ValidationError as e:
            context = {
                "notebook": self.object,
                "page": page,
                "version": page.latest_version,
                "form": form,
                "current_page": current_page,
                "create_page_url": create_page_url,
            }
            for message in e.messages:
                if "already exists" in message:
                    conflict_path = (
                        message
                        .removeprefix("Path '")
                        .removesuffix("' already exists.")
                    )
                    context["conflict_filename"] = form.cleaned_data["filename"]
                    context["conflict_url"] = reverse("notebook_page", kwargs={
                        "username": username,
                        "slug": slug,
                        "path": conflict_path,
                    })
                else:
                    form.add_error(None, message)
            return render(
                request,
                "notebooks/edit.html",
                context,
                status=HTTPStatus.CONFLICT,
            )

        new_path = new_version.path
        if new_path.endswith("/index") or new_path == "index":
            return redirect(self.object.get_folder_url(new_path))

        url = reverse("notebook_page", kwargs={
            "username": username,
            "slug": slug,
            "path": new_path,
        })
        return redirect(url)


class NotebookListView(View):
    def get(self, request):
        if not request.user.is_authenticated:
            return HttpResponse(status=HTTPStatus.UNAUTHORIZED)

        my_notebooks = Notebook.objects.filter(owner=request.user).order_by(
            "name"
        ).prefetch_related("campaign_notebooks__campaign")
        other_notebooks = Notebook.objects.filter(
            notebookpermission__user=request.user
        ).exclude(owner=request.user).distinct().order_by("name").prefetch_related(
            "campaign_notebooks__campaign", "owner"
        )

        return render(request, "notebooks/list.html", {
            "my_notebooks": my_notebooks,
            "other_notebooks": other_notebooks,
        })
