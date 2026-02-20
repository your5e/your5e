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
    if user == notebook.owner:
        return "owner"
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
    return get_permission(notebook, user) is not None


def can_edit(notebook, user):
    permission = get_permission(notebook, user)
    return permission in ("owner", NotebookPermission.Role.EDITOR)


class NotebookView(View):
    def get(self, request, username, slug, path=""):
        owner = get_object_or_404(User, username=username)
        notebook = get_object_or_404(Notebook, owner=owner, slug=slug)

        if not can_view(notebook, request.user):
            if not request.user.is_authenticated:
                return HttpResponse(status=HTTPStatus.UNAUTHORIZED)
            return HttpResponse(status=HTTPStatus.FORBIDDEN)

        is_owner = request.user == owner
        user_can_edit = can_edit(notebook, request.user)
        directory = "/" + path

        context = {
            "notebook": notebook,
            "is_owner": is_owner,
            "can_edit": user_can_edit,
            "folders": notebook.folders_in(directory),
            "files": notebook.files_in(directory),
        }

        if user_can_edit:
            context["deleted_pages"] = notebook.deleted_pages()

        try:
            index_path = path + "index.md" if path else "index.md"
            index_page = notebook.get_page(path=index_path)
            context["index_content"] = index_page.latest_version.content.data.decode()
        except Page.DoesNotExist:
            pass

        if is_owner:
            context["collaborators"] = NotebookPermission.objects.filter(
                notebook=notebook
            ).select_related("user")

        return render(request, "notebooks/notebook.html", context)


class NotebookUploadView(View):
    def post(self, request):
        if not request.user.is_authenticated:
            return HttpResponse(status=HTTPStatus.UNAUTHORIZED)

        notebook = get_object_or_404(Notebook, pk=request.POST.get("notebook"))

        if not can_edit(notebook, request.user):
            return HttpResponse(status=HTTPStatus.FORBIDDEN)

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

        page = Page.objects.create(wiki=notebook)
        page.update(
            filename=filename,
            mime_type=mime_type,
            data=uploaded_file.read(),
            created_by=request.user,
        )

        return redirect(notebook)


class NotebookRenameView(View):
    def post(self, request):
        if not request.user.is_authenticated:
            return HttpResponse(status=HTTPStatus.UNAUTHORIZED)

        notebook = get_object_or_404(Notebook, pk=request.POST.get("notebook"))

        if request.user != notebook.owner:
            return HttpResponse(status=HTTPStatus.FORBIDDEN)

        name = request.POST.get("name")
        if name:
            notebook.rename(name)

        return redirect(notebook)


class NotebookVisibilityView(View):
    def post(self, request):
        if not request.user.is_authenticated:
            return HttpResponse(status=HTTPStatus.UNAUTHORIZED)

        notebook = get_object_or_404(Notebook, pk=request.POST.get("notebook"))

        if request.user != notebook.owner:
            return HttpResponse(status=HTTPStatus.FORBIDDEN)

        visibility = request.POST.get("visibility")
        confirmed = request.POST.get("confirmed") == "true"

        if not confirmed:
            return render(request, "notebooks/confirm_visibility.html", {
                "notebook": notebook,
                "visibility": visibility,
            })

        notebook.visibility = visibility
        notebook.save()

        return redirect(notebook)


class NotebookCollaboratorsView(View):
    def post(self, request):
        if not request.user.is_authenticated:
            return HttpResponse(status=HTTPStatus.UNAUTHORIZED)

        notebook = get_object_or_404(Notebook, pk=request.POST.get("notebook"))

        if request.user != notebook.owner:
            return HttpResponse(status=HTTPStatus.FORBIDDEN)

        confirmed = request.POST.get("confirmed") == "true"

        if "username" in request.POST:
            return self.handle_add(request, notebook, confirmed)
        elif "remove" in request.POST:
            return self.handle_remove(request, notebook, confirmed)
        elif "change_role" in request.POST:
            return self.handle_change_role(request, notebook, confirmed)

        return redirect(notebook)

    def handle_add(self, request, notebook, confirmed):
        username = request.POST.get("username")
        role = request.POST.get("role")
        user = get_object_or_404(User, username=username)

        if not confirmed:
            return render(request, "notebooks/confirm_collaborator.html", {
                "notebook": notebook,
                "action": "add",
                "target_user": user,
                "role": role,
            })

        NotebookPermission.objects.create(
            notebook=notebook,
            user=user,
            role=role,
        )

        return redirect(notebook)

    def handle_remove(self, request, notebook, confirmed):
        user_pk = request.POST.get("remove")
        user = get_object_or_404(User, pk=user_pk)

        if not confirmed:
            return render(request, "notebooks/confirm_collaborator.html", {
                "notebook": notebook,
                "action": "remove",
                "target_user": user,
            })

        NotebookPermission.objects.filter(
            notebook=notebook,
            user=user,
        ).delete()

        return redirect(notebook)

    def handle_change_role(self, request, notebook, confirmed):
        user_pk = request.POST.get("change_role")
        role = request.POST.get("role")
        user = get_object_or_404(User, pk=user_pk)

        if not confirmed:
            return render(request, "notebooks/confirm_collaborator.html", {
                "notebook": notebook,
                "action": "change_role",
                "target_user": user,
                "role": role,
            })

        NotebookPermission.objects.filter(
            notebook=notebook,
            user=user,
        ).update(role=role)

        return redirect(notebook)
