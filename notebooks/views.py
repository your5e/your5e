import mimetypes
from http import HTTPStatus

from django.core.exceptions import ValidationError
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views import View

from notebooks.forms import PageForm
from notebooks.models import Notebook, NotebookPermission
from users.models import User
from wikis.models import Page

MIME_TYPE_FALLBACKS = {
    ".md": "text/markdown",
    ".markdown": "text/markdown",
}
DEFAULT_MIME_TYPE = "application/octet-stream"
MAX_UPLOAD_SIZE = 2 * 1024 * 1024


class NotebookPermissions:
    @staticmethod
    def get_permission(notebook, user):
        if not user.is_authenticated:
            return None
        try:
            permission = NotebookPermission.objects.get(notebook=notebook, user=user)
            return permission.role
        except NotebookPermission.DoesNotExist:
            return None

    @staticmethod
    def can_view(notebook, user):
        if notebook.visibility == Notebook.Visibility.PUBLIC:
            return True
        if notebook.visibility == Notebook.Visibility.SITE:
            return user.is_authenticated
        if user.is_authenticated and user == notebook.owner:
            return True
        return NotebookPermissions.get_permission(notebook, user) is not None

    @staticmethod
    def can_edit(notebook, user):
        if user.is_authenticated and user == notebook.owner:
            return True
        return (
            NotebookPermissions.get_permission(notebook, user)
            == NotebookPermission.Role.EDITOR
        )

    @staticmethod
    def check_edit(notebook, user):
        if not user.is_authenticated:
            return HttpResponse(status=HTTPStatus.UNAUTHORIZED)
        if not NotebookPermissions.can_edit(notebook, user):
            return HttpResponse(status=HTTPStatus.FORBIDDEN)
        return None

    @staticmethod
    def view_required(method):
        def wrapper(self, request, *args, **kwargs):
            self.object = self.get_object()
            if not NotebookPermissions.can_view(self.object, request.user):
                if not request.user.is_authenticated:
                    return HttpResponse(status=HTTPStatus.UNAUTHORIZED)
                return HttpResponse(status=HTTPStatus.FORBIDDEN)
            return method(self, request, *args, **kwargs)
        return wrapper

    @staticmethod
    def edit_required(method):
        def wrapper(self, request, *args, **kwargs):
            self.object = self.get_object()
            if error := NotebookPermissions.check_edit(self.object, request.user):
                return error
            return method(self, request, *args, **kwargs)
        return wrapper

    @staticmethod
    def owner_required(method):
        def wrapper(self, request, *args, **kwargs):
            self.object = self.get_object()
            if not request.user.is_authenticated:
                return HttpResponse(status=HTTPStatus.UNAUTHORIZED)
            if request.user != self.object.owner:
                return HttpResponse(status=HTTPStatus.FORBIDDEN)
            return method(self, request, *args, **kwargs)
        return wrapper


class NotebookReadMixin:
    def get_object(self):
        owner = get_object_or_404(User, username=self.kwargs['username'])
        return get_object_or_404(Notebook, owner=owner, slug=self.kwargs['slug'])


class NotebookWriteMixin:
    def get_object(self):
        return get_object_or_404(Notebook, pk=self.request.POST.get("notebook"))


class NotebookView(NotebookReadMixin, View):
    @NotebookPermissions.view_required
    def get(self, request, username, slug, path=""):
        is_owner = request.user == self.object.owner
        user_can_edit = NotebookPermissions.can_edit(self.object, request.user)
        contents = self.object.contents_in(path)

        # index.md is rendered inline, exclude from the file list
        index_path = (path + "/index").lstrip("/")
        files = [f for f in contents["files"] if f.path != index_path]

        index_exists = False
        try:
            index_page = self.object.get_page(path=index_path)
            index_exists = True
        except Page.DoesNotExist:
            index_page = None

        # an index only "exists" if there is content below
        if not files and not contents["folders"] and not index_exists:
            context = {"notebook": self.object, "path": path}
            if user_can_edit:
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

        context = {
            "notebook": self.object,
            "is_owner": is_owner,
            "can_edit": user_can_edit,
            "folders": contents["folders"],
            "files": files,
            "index_exists": index_exists,
        }

        if user_can_edit:
            context["deleted_pages"] = self.object.deleted_pages()

        if index_page:
            index_version_number = request.GET.get("index_version")
            if index_version_number:
                try:
                    index_version = index_page.version_set.get(
                        number=int(index_version_number)
                    )
                except (ValueError, index_page.version_set.model.DoesNotExist):
                    return HttpResponse(status=HTTPStatus.NOT_FOUND)
            else:
                index_version = index_page.latest_version
            context["index_content"] = index_version.render(
                base_url=self.object.get_absolute_url()
            )
            context["index_version"] = index_version
            context["index_history"] = index_page.history()

        if is_owner:
            context["collaborators"] = NotebookPermission.objects.filter(
                notebook=self.object
            ).select_related("user")

        return render(request, "notebooks/notebook.html", context)


class NotebookUploadView(NotebookWriteMixin, View):
    @NotebookPermissions.edit_required
    def post(self, request):
        uploaded_file = request.FILES.get("file")
        filename = request.POST.get("filename") or uploaded_file.name

        if uploaded_file.size > MAX_UPLOAD_SIZE:
            return HttpResponse(status=HTTPStatus.BAD_REQUEST)

        mime_type, _ = mimetypes.guess_type(filename)
        if mime_type is None:
            if "." in filename:
                ext = "." + filename.rsplit(".", 1)[-1].lower()
            else:
                ext = ""
            mime_type = MIME_TYPE_FALLBACKS.get(ext, DEFAULT_MIME_TYPE)

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
        if name:
            self.object.rename(name)

        return redirect(self.object)


class NotebookVisibilityView(NotebookWriteMixin, View):
    @NotebookPermissions.owner_required
    def post(self, request):
        visibility = request.POST.get("visibility")
        confirmed = request.POST.get("confirmed") == "true"

        if not confirmed:
            return render(request, "notebooks/confirm_visibility.html", {
                "notebook": self.object,
                "visibility": visibility,
            })

        self.object.visibility = visibility
        self.object.save()

        return redirect(self.object)


class NotebookPageDeleteView(NotebookWriteMixin, View):
    @NotebookPermissions.edit_required
    def post(self, request):
        page = get_object_or_404(Page, pk=request.POST.get("page"))
        confirmed = request.POST.get("confirmed") == "true"

        if not confirmed:
            return render(request, "notebooks/confirm_delete.html", {
                "notebook": self.object,
                "page": page,
            })

        page.soft_delete()

        return HttpResponseRedirect(
            self.object.get_folder_url(page.latest_version.path),
            status=HTTPStatus.SEE_OTHER,
        )


class NotebookCollaboratorsView(NotebookWriteMixin, View):
    @NotebookPermissions.owner_required
    def post(self, request):
        confirmed = request.POST.get("confirmed") == "true"

        if "username" in request.POST:
            return self.handle_add(request, confirmed)
        elif "remove" in request.POST:
            return self.handle_remove(request, confirmed)
        elif "change_role" in request.POST:
            return self.handle_change_role(request, confirmed)

        return redirect(self.object)

    def handle_add(self, request, confirmed):
        username = request.POST.get("username")
        role = request.POST.get("role")
        user = get_object_or_404(User, username=username)

        if not confirmed:
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

    def handle_remove(self, request, confirmed):
        user_pk = request.POST.get("remove")
        user = get_object_or_404(User, pk=user_pk)

        if not confirmed:
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

    def handle_change_role(self, request, confirmed):
        user_pk = request.POST.get("change_role")
        role = request.POST.get("role")
        user = get_object_or_404(User, pk=user_pk)

        if not confirmed:
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


class NotebookPageView(NotebookReadMixin, View):
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
            context = {"notebook": self.object, "path": path}
            if NotebookPermissions.can_edit(self.object, request.user):
                filename = self.object.suggest_filename(path)
                context["form"] = PageForm(initial={"filename": filename})
            return render(
                request,
                "notebooks/not_found.html",
                context,
                status=HTTPStatus.NOT_FOUND,
            )

        if "edit" in request.GET:
            if error := NotebookPermissions.check_edit(self.object, request.user):
                return error

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
            return render(request, "notebooks/edit.html", {
                "notebook": self.object,
                "page": page,
                "version": version,
                "form": form,
            })

        history = page.history()
        version_number = request.GET.get("version")
        if version_number:
            try:
                version = page.version_set.get(number=int(version_number))
            except (ValueError, page.version_set.model.DoesNotExist):
                return HttpResponse(status=HTTPStatus.NOT_FOUND)
            is_old_version = True
        else:
            version = page.latest_version
            is_old_version = False

        content = version.render(base_url=self.object.get_absolute_url())

        if isinstance(content, str):
            return render(request, "notebooks/page.html", {
                "notebook": self.object,
                "page": version,
                "content": content,
                "history": history,
                "is_old_version": is_old_version,
                "can_edit": NotebookPermissions.can_edit(self.object, request.user),
            })
        return HttpResponse(content, content_type=version.mime_type)

    @NotebookPermissions.edit_required
    def post(self, request, username, slug, path):
        try:
            page = self.object.get_page(path=path)
            version = page.latest_version
            mime_type = version.mime_type
            default_filename = version.filename
        except Page.DoesNotExist:
            page = None
            version = None
            mime_type = "text/markdown"
            default_filename = None

        form = PageForm(request.POST, request.FILES)
        if not form.is_valid():
            return render(
                request,
                "notebooks/edit.html",
                {
                    "notebook": self.object,
                    "page": page,
                    "version": version,
                    "form": form,
                },
                status=HTTPStatus.BAD_REQUEST,
            )

        filename = form.cleaned_data["filename"].strip()
        if filename:
            if "/" not in filename:
                directory = "/".join(path.split("/")[:-1])
                if directory:
                    filename = f"{directory}/{filename}"
            if mime_type == "text/markdown" and not filename.lower().endswith(".md"):
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
                },
                status=HTTPStatus.BAD_REQUEST,
            )

        if form.cleaned_data.get("file"):
            uploaded_file = form.cleaned_data["file"]
            if uploaded_file.size > MAX_UPLOAD_SIZE:
                form.add_error("file", "File too large (max 2MB)")
                return render(
                    request,
                    "notebooks/edit.html",
                    {
                        "notebook": self.object,
                        "page": page,
                        "version": version,
                        "form": form,
                    },
                    status=HTTPStatus.BAD_REQUEST,
                )
            data = uploaded_file.read()
        else:
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
            }
            for message in e.messages:
                if "already exists" in message:
                    conflict_path = message.split()[1]
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
