from datetime import UTC, datetime
from urllib.parse import urlparse
from uuid import UUID

from django.db.models import Max, Q
from django.db.models.functions import Coalesce, Greatest
from django.http import Http404, HttpResponse
from django.shortcuts import get_object_or_404
from django.urls import reverse
from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from rest_framework.generics import ListAPIView
from rest_framework.pagination import CursorPagination
from rest_framework.response import Response

from api.views import AuthenticatedAPIView
from notebooks.models import Notebook, NotebookPermission
from notebooks.views import NotebookPermissions
from users.models import User

PAGE_SIZE = 50


class BasePagination(CursorPagination):
    page_size = PAGE_SIZE

    def paginate_queryset(self, queryset, request, view=None):
        self.total_results = queryset.count()
        return super().paginate_queryset(queryset, request, view)

    def get_paginated_response(self, data):
        return Response({
            "next": self.get_next_link(),
            "previous": self.get_previous_link(),
            "results": data,
            "total_results": self.total_results,
        })

    def get_next_link(self):
        url = super().get_next_link()
        if url:
            parsed = urlparse(url)
            return parsed.path + "?" + parsed.query
        return None

    def get_previous_link(self):
        url = super().get_previous_link()
        if url:
            parsed = urlparse(url)
            return parsed.path + "?" + parsed.query
        return None


class NotebookPagination(BasePagination):
    ordering = ["-last_updated", "-pk"]


class NotebookSerializer(serializers.ModelSerializer):
    owner = serializers.CharField(source="owner.username")
    url = serializers.SerializerMethodField()
    html_url = serializers.SerializerMethodField()
    last_updated = serializers.DateTimeField(format="%Y-%m-%dT%H:%M:%SZ")
    copied_from = serializers.SerializerMethodField()
    editable = serializers.SerializerMethodField()

    class Meta:
        model = Notebook
        fields = [
            "name",
            "slug",
            "owner",
            "visibility",
            "url",
            "html_url",
            "last_updated",
            "copied_from",
            "editable",
        ]

    def get_url(self, obj):
        return reverse("api_notebook_pages", kwargs={
            "username": obj.owner.username,
            "slug": obj.slug,
        })

    def get_html_url(self, obj):
        request = self.context["request"]
        return request.build_absolute_uri(obj.get_absolute_url())

    def get_copied_from(self, obj):
        if obj.copied_from:
            return obj.copied_from.slug
        return None

    def get_editable(self, obj):
        return NotebookPermissions.can_edit(obj, self.context["request"].user)


class NotebookAPIView(AuthenticatedAPIView, ListAPIView):
    serializer_class = NotebookSerializer
    pagination_class = NotebookPagination

    def get_shared_notebook_ids(self):
        return (
            NotebookPermission.objects
                .filter(user=self.request.user)
                .values_list("notebook_id", flat=True)
        )


class NotebookListView(NotebookAPIView):
    def get_queryset(self):
        user = self.request.user
        return (
            Notebook.objects
                .filter(
                    Q(owner=user)
                    | Q(pk__in=self.get_shared_notebook_ids())
                    | Q(visibility=Notebook.Visibility.INTERNAL)
                    | Q(visibility=Notebook.Visibility.PUBLIC)
                )
                .select_related("owner")
                .distinct()
        )


class NotebookPublicView(NotebookAPIView):
    def get_queryset(self):
        return (
            Notebook.objects
                .filter(visibility=Notebook.Visibility.PUBLIC)
                .select_related("owner")
        )


class NotebookInternalView(NotebookAPIView):
    def get_queryset(self):
        return (
            Notebook.objects
                .filter(visibility=Notebook.Visibility.INTERNAL)
                .select_related("owner")
        )


class NotebookPrivateView(NotebookAPIView):
    def get_queryset(self):
        user = self.request.user
        return (
            Notebook.objects
                .filter(visibility=Notebook.Visibility.PRIVATE)
                .filter(
                    Q(owner=user)
                    | Q(pk__in=self.get_shared_notebook_ids())
                )
                .select_related("owner")
                .distinct()
        )


class NotebookUserView(NotebookAPIView):
    def get_queryset(self):
        owner = get_object_or_404(User, username=self.kwargs["username"])
        user = self.request.user

        if user == owner:
            return (
                Notebook.objects
                    .filter(owner=owner)
                    .select_related("owner")
            )

        return (
            Notebook.objects
                .filter(owner=owner)
                .filter(
                    Q(pk__in=self.get_shared_notebook_ids())
                    | Q(visibility=Notebook.Visibility.INTERNAL)
                    | Q(visibility=Notebook.Visibility.PUBLIC)
                )
                .select_related("owner")
                .distinct()
        )


class PageSerializer(serializers.Serializer):
    uuid = serializers.UUIDField()
    path = serializers.SerializerMethodField()
    filename = serializers.SerializerMethodField()
    mime_type = serializers.SerializerMethodField()
    version = serializers.SerializerMethodField()
    created_by = serializers.SerializerMethodField()
    updated_at = serializers.SerializerMethodField()
    deleted_at = serializers.DateTimeField(format="%Y-%m-%dT%H:%M:%SZ")
    content_hash = serializers.SerializerMethodField()

    def get_path(self, obj):
        return obj.latest_version.path

    def get_filename(self, obj):
        return obj.latest_version.filename

    def get_mime_type(self, obj):
        return obj.latest_version.mime_type

    def get_version(self, obj):
        return obj.latest_version.number

    def get_created_by(self, obj):
        return obj.latest_version.created_by.username

    def get_updated_at(self, obj):
        if obj.deleted_at:
            return None
        return obj.latest_version.created_at.strftime("%Y-%m-%dT%H:%M:%SZ")

    def get_content_hash(self, obj):
        return obj.latest_version.content.hash


class PagePagination(BasePagination):
    ordering = ["-last_modified", "-pk"]


def parse_timestamp(value):
    if value.isdigit():
        return datetime.fromtimestamp(int(value), tz=UTC)
    try:
        return datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=UTC)
    except ValueError as err:
        raise ValidationError({"since": "Invalid timestamp format"}) from err


class NotebookAccessMixin:
    def get_notebook(self):
        owner = get_object_or_404(User, username=self.kwargs["username"])
        notebook = Notebook.objects.filter(
            owner=owner,
            slug=self.kwargs["slug"],
        ).first()

        if not notebook:
            raise Http404

        if not NotebookPermissions.can_view(notebook, self.request.user):
            raise Http404

        return notebook


class NotebookPagesView(NotebookAccessMixin, AuthenticatedAPIView, ListAPIView):
    serializer_class = PageSerializer
    pagination_class = PagePagination
    notebook = None

    def list(self, request, *args, **kwargs):
        self.notebook = self.get_notebook()
        response = super().list(request, *args, **kwargs)
        response.data["editable"] = NotebookPermissions.can_edit(
            self.notebook, request.user
        )
        return response

    def get_queryset(self):
        notebook = self.notebook

        since = self.request.query_params.get("since")
        if since:
            return notebook.changes_since(parse_timestamp(since))

        return (
            notebook.page_set
                .annotate(
                    latest_version_created=Max("version__created_at"),
                    last_modified=Greatest(
                        Coalesce("deleted_at", "latest_version_created"),
                        "latest_version_created",
                    ),
                )
        )


class PageContentView(NotebookAccessMixin, AuthenticatedAPIView):
    def get(self, request, username, slug, uuid):
        notebook = self.get_notebook()

        try:
            page_uuid = UUID(uuid)
        except ValueError:
            raise Http404 from None

        page = notebook.page_set.filter(
            uuid=page_uuid,
            deleted_at__isnull=True,
        ).first()

        if not page:
            raise Http404

        version_number = request.query_params.get("version")
        try:
            version = page.get_version(version_number)
        except page.DoesNotExist:
            raise Http404 from None

        return HttpResponse(
            version.content.data,
            content_type=version.mime_type,
        )

    def put(self, request, username, slug, uuid):
        notebook = self.get_notebook()

        if not NotebookPermissions.can_edit(notebook, request.user):
            return Response(status=403)

        try:
            page_uuid = UUID(uuid)
        except ValueError:
            raise Http404 from None

        page = notebook.page_set.filter(uuid=page_uuid).first()

        if not page:
            raise Http404

        previous_hash = page.latest_version.content.hash

        if page.deleted_at:
            page.restore()

        version = page.update(
            filename=page.latest_version.filename,
            mime_type=request.content_type,
            data=request.body,
            created_by=request.user,
        )

        return Response({
            "uuid": str(page.uuid),
            "path": version.path,
            "filename": version.filename,
            "mime_type": version.mime_type,
            "version": version.number,
            "created_by": version.created_by.username,
            "updated_at": version.created_at.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "content_hash": version.content.hash,
            "previous_hash": previous_hash,
        })
