from urllib.parse import urlparse

from django.db.models import Q
from django.shortcuts import get_object_or_404
from rest_framework import serializers
from rest_framework.generics import ListAPIView
from rest_framework.pagination import CursorPagination
from rest_framework.response import Response

from api.views import AuthenticatedAPIView
from notebooks.models import Notebook, NotebookPermission
from users.models import User

PAGE_SIZE = 50


class NotebookPagination(CursorPagination):
    page_size = PAGE_SIZE
    ordering = ["-last_updated", "-pk"]

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


class NotebookSerializer(serializers.ModelSerializer):
    owner = serializers.CharField(source="owner.username")
    url = serializers.CharField(source="get_absolute_url")
    last_updated = serializers.DateTimeField(format="%Y-%m-%dT%H:%M:%SZ")
    copied_from = serializers.SerializerMethodField()

    class Meta:
        model = Notebook
        fields = [
            "name",
            "slug",
            "owner",
            "visibility",
            "url",
            "last_updated",
            "copied_from",
        ]

    def get_copied_from(self, obj):
        if obj.copied_from:
            return obj.copied_from.slug
        return None


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
