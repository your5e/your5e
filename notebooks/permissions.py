from http import HTTPStatus

from django.http import HttpResponse

from notebooks.models import Notebook, NotebookPermission


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
        if notebook.visibility == Notebook.Visibility.INTERNAL:
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
            if not request.user.is_authenticated:
                return HttpResponse(status=HTTPStatus.UNAUTHORIZED)
            if not NotebookPermissions.can_edit(self.object, request.user):
                return HttpResponse(status=HTTPStatus.FORBIDDEN)
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
