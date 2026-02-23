import mimetypes
from http import HTTPStatus

from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views import View

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
                context["suggested_filename"] = self.object.suggest_filename(index_path)
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
                context["suggested_filename"] = self.object.suggest_filename(path)
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

            return render(request, "notebooks/edit.html", {
                "notebook": self.object,
                "page": page,
                "version": version,
                "content": content,
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
        except Page.DoesNotExist:
            return self.create_page(request, username, slug, path)

        version = page.latest_version
        mime_type = version.mime_type

        if "file" in request.FILES:
            uploaded_file = request.FILES["file"]
            if uploaded_file.size > MAX_UPLOAD_SIZE:
                return HttpResponse(status=HTTPStatus.BAD_REQUEST)
            data = uploaded_file.read()
        else:
            data = request.POST.get("content", "").encode("utf-8")

        page.update(
            filename=version.filename,
            mime_type=mime_type,
            data=data,
            created_by=request.user,
        )

        if path.endswith("/index") or path == "index":
            folder_path = path.removesuffix("/index").removesuffix("index")
            if folder_path:
                url = reverse("notebook_directory", kwargs={
                    "username": username,
                    "slug": slug,
                    "path": folder_path,
                })
            else:
                url = reverse("notebook", kwargs={
                    "username": username,
                    "slug": slug,
                })
            return redirect(url)

        url = reverse("notebook_page", kwargs={
            "username": username,
            "slug": slug,
            "path": path,
        })
        return redirect(url)

    def create_page(self, request, username, slug, path):
        filename = request.POST.get("filename", "").strip()
        if not filename:
            return HttpResponse(status=HTTPStatus.BAD_REQUEST)

        content = request.POST.get("content", "")
        if not content:
            if path.endswith("/index"):
                folder_path = path.removesuffix("/index")
                url = reverse("notebook_directory", kwargs={
                    "username": username,
                    "slug": slug,
                    "path": folder_path,
                })
                return redirect(url)
            return redirect(request.path)

        if "/" not in filename:
            directory = "/".join(path.split("/")[:-1])
            if directory:
                filename = f"{directory}/{filename}"

        if not filename.endswith(".md"):
            filename = f"{filename}.md"

        page = Page.objects.create(wiki=self.object)
        page.update(
            filename=filename,
            mime_type="text/markdown",
            data=content.encode("utf-8"),
            created_by=request.user,
        )

        page_path = page.latest_version.path
        if page_path.endswith("/index"):
            folder_path = page_path.removesuffix("/index")
            url = reverse("notebook_directory", kwargs={
                "username": username,
                "slug": slug,
                "path": folder_path,
            })
        else:
            url = reverse("notebook_page", kwargs={
                "username": username,
                "slug": slug,
                "path": page_path,
            })
        return redirect(url)
