from http import HTTPStatus

from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views import View

from notebooks.models import Notebook, NotebookPermission
from users.models import User


class NotebookView(View):
    def get(self, request, username, slug):
        owner = get_object_or_404(User, username=username)
        notebook = get_object_or_404(Notebook, owner=owner, slug=slug)

        is_owner = request.user == owner
        context = {
            "notebook": notebook,
            "is_owner": is_owner,
        }

        if is_owner:
            context["collaborators"] = NotebookPermission.objects.filter(
                notebook=notebook
            ).select_related("user")

        return render(request, "notebooks/notebook.html", context)


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
