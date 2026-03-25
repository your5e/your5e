from http import HTTPStatus

from django.http import HttpResponse

from users.models import get_sentinel_user


class CampaignPermissions:
    @staticmethod
    def can_view(campaign, user):
        if not user.is_authenticated:
            return False
        return campaign.players.filter(pk=user.pk).exists()

    @staticmethod
    def is_owner(campaign, user):
        return user.is_authenticated and campaign.owner == user

    @staticmethod
    def is_unclaimed(campaign):
        return campaign.owner == get_sentinel_user()

    @staticmethod
    def can_unlink_notebook(link, campaign, user):
        return (
            campaign.owner == user
            or link.notebook.owner == user
            or link.linked_by == user
        )

    @staticmethod
    def view_required(method):
        def wrapper(self, request, *args, **kwargs):
            self.object = self.get_object()
            if not request.user.is_authenticated:
                return HttpResponse(status=HTTPStatus.UNAUTHORIZED)
            if not CampaignPermissions.can_view(self.object, request.user):
                return HttpResponse(status=HTTPStatus.FORBIDDEN)
            return method(self, request, *args, **kwargs)
        return wrapper
