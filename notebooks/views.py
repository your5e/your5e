import mimetypes
from http import HTTPStatus

from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
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


def get_permission(notebook, user):
    if not user.is_authenticated:
        return None
    try:
        permission = NotebookPermission.objects.get(notebook=notebook, user=user)
        return permission.role
    except NotebookPermission.DoesNotExist:
        return None


def can_view(notebook, user):
    if notebook.visibility == Notebook.Visibility.PUBLIC:
        return True
    if notebook.visibility == Notebook.Visibility.SITE:
        return user.is_authenticated
    if user.is_authenticated and user == notebook.owner:
        return True
    return get_permission(notebook, user) is not None


def can_edit(notebook, user):
    if user.is_authenticated and user == notebook.owner:
        return True
    return get_permission(notebook, user) == NotebookPermission.Role.EDITOR


def get_notebook_or_error(request, username, slug):
    owner = get_object_or_404(User, username=username)
    notebook = get_object_or_404(Notebook, owner=owner, slug=slug)

    if not can_view(notebook, request.user):
        if not request.user.is_authenticated:
            return None, HttpResponse(status=HTTPStatus.UNAUTHORIZED)
        return None, HttpResponse(status=HTTPStatus.FORBIDDEN)

    return notebook, None


class NotebookActionView(View):
    require_owner = True

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return HttpResponse(status=HTTPStatus.UNAUTHORIZED)

        self.notebook = get_object_or_404(Notebook, pk=request.POST.get("notebook"))

        if self.require_owner:
            if request.user != self.notebook.owner:
                return HttpResponse(status=HTTPStatus.FORBIDDEN)
        elif not can_edit(self.notebook, request.user):
            return HttpResponse(status=HTTPStatus.FORBIDDEN)

        return super().dispatch(request, *args, **kwargs)


class NotebookView(View):
    def get(self, request, username, slug, path=""):
        notebook, error = get_notebook_or_error(request, username, slug)
        if error:
            return error

        is_owner = request.user == notebook.owner
        user_can_edit = can_edit(notebook, request.user)
        directory = "/" + path
        contents = notebook.contents_in(directory)

        context = {
            "notebook": notebook,
            "is_owner": is_owner,
            "can_edit": user_can_edit,
            "folders": contents["folders"],
            "files": contents["files"],
        }

        if user_can_edit:
            context["deleted_pages"] = notebook.deleted_pages()

        try:
            if path:
                index_path = path + "/index"
            else:
                index_path = "index"
            index_page = notebook.get_page(path=index_path)
            context["index_content"] = index_page.latest_version.render()
        except Page.DoesNotExist:
            pass

        if is_owner:
            context["collaborators"] = NotebookPermission.objects.filter(
                notebook=notebook
            ).select_related("user")

        return render(request, "notebooks/notebook.html", context)


class NotebookUploadView(NotebookActionView):
    require_owner = False

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

        page = Page.objects.create(wiki=self.notebook)
        page.update(
            filename=filename,
            mime_type=mime_type,
            data=uploaded_file.read(),
            created_by=request.user,
        )

        return redirect(self.notebook)


class NotebookRenameView(NotebookActionView):
    def post(self, request):
        name = request.POST.get("name")
        if name:
            self.notebook.rename(name)

        return redirect(self.notebook)


class NotebookVisibilityView(NotebookActionView):
    def post(self, request):
        visibility = request.POST.get("visibility")
        confirmed = request.POST.get("confirmed") == "true"

        if not confirmed:
            return render(request, "notebooks/confirm_visibility.html", {
                "notebook": self.notebook,
                "visibility": visibility,
            })

        self.notebook.visibility = visibility
        self.notebook.save()

        return redirect(self.notebook)


class NotebookCollaboratorsView(NotebookActionView):
    def post(self, request):
        confirmed = request.POST.get("confirmed") == "true"

        if "username" in request.POST:
            return self.handle_add(request, confirmed)
        elif "remove" in request.POST:
            return self.handle_remove(request, confirmed)
        elif "change_role" in request.POST:
            return self.handle_change_role(request, confirmed)

        return redirect(self.notebook)

    def handle_add(self, request, confirmed):
        username = request.POST.get("username")
        role = request.POST.get("role")
        user = get_object_or_404(User, username=username)

        if not confirmed:
            return render(request, "notebooks/confirm_collaborator.html", {
                "notebook": self.notebook,
                "action": "add",
                "target_user": user,
                "role": role,
            })

        NotebookPermission.objects.create(
            notebook=self.notebook,
            user=user,
            role=role,
        )

        return redirect(self.notebook)

    def handle_remove(self, request, confirmed):
        user_pk = request.POST.get("remove")
        user = get_object_or_404(User, pk=user_pk)

        if not confirmed:
            return render(request, "notebooks/confirm_collaborator.html", {
                "notebook": self.notebook,
                "action": "remove",
                "target_user": user,
            })

        NotebookPermission.objects.filter(
            notebook=self.notebook,
            user=user,
        ).delete()

        return redirect(self.notebook)

    def handle_change_role(self, request, confirmed):
        user_pk = request.POST.get("change_role")
        role = request.POST.get("role")
        user = get_object_or_404(User, pk=user_pk)

        if not confirmed:
            return render(request, "notebooks/confirm_collaborator.html", {
                "notebook": self.notebook,
                "action": "change_role",
                "target_user": user,
                "role": role,
            })

        NotebookPermission.objects.filter(
            notebook=self.notebook,
            user=user,
        ).update(role=role)

        return redirect(self.notebook)


class NotebookPageView(View):
    def get(self, request, username, slug, path):
        notebook, error = get_notebook_or_error(request, username, slug)
        if error:
            return error

        if path.endswith(".md"):
            return redirect(f"/notebooks/{username}/{slug}/{path[:-3]}", permanent=True)

        try:
            page = notebook.get_page(path=path)
        except Page.DoesNotExist:
            return HttpResponse(status=HTTPStatus.NOT_FOUND)

        version = page.latest_version
        content = version.render()

        if isinstance(content, str):
            return render(request, "notebooks/page.html", {
                "notebook": notebook,
                "page": version,
                "content": content,
            })
        return HttpResponse(content, content_type=version.mime_type)
