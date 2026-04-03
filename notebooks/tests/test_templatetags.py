from datetime import timedelta

import pytest
from django.contrib.auth.models import AnonymousUser
from django.utils import timezone

from campaigns.models import Campaign, CampaignNotebook
from campaigns.tests import LinkedCampaignNotebooksMixin
from notebooks.templatetags.dates import smart_date
from notebooks.templatetags.notebook_permissions import (
    can_edit,
    can_manage,
    is_wiki_and_player_in_that_campaign,
)
from notebooks.tests import NotebookMixin


@pytest.mark.django_db
class TestSmartDate:
    def test_less_than_one_minute(self):
        now = timezone.now()
        dt = now - timedelta(seconds=55)
        assert smart_date(dt) == "just now"

    def test_one_minute_ago(self):
        now = timezone.now()
        dt = now - timedelta(minutes=1)
        assert smart_date(dt) == "1 minute ago"

    def test_minutes_ago(self):
        now = timezone.now()
        dt = now - timedelta(minutes=5)
        assert smart_date(dt) == "5 minutes ago"

    def test_one_hour_ago(self):
        now = timezone.now()
        dt = now - timedelta(hours=1)
        assert smart_date(dt) == "1 hour ago"

    def test_hours_ago(self):
        now = timezone.now()
        dt = now - timedelta(hours=3)
        assert smart_date(dt) == "3 hours ago"

    def test_one_day_ago(self):
        now = timezone.now()
        dt = now - timedelta(days=1)
        assert smart_date(dt) == "1 day ago"

    def test_days_ago(self):
        now = timezone.now()
        dt = now - timedelta(days=4)
        assert smart_date(dt) == "4 days ago"

    def test_over_week_same_year(self):
        now = timezone.now()
        dt = now - timedelta(days=10)
        expected = dt.strftime("%-d %b")
        assert smart_date(dt) == expected

    def test_over_week_different_year(self):
        now = timezone.now()
        dt = now.replace(year=now.year - 1)
        expected = dt.strftime("%-d %b %Y")
        assert smart_date(dt) == expected


@pytest.mark.django_db
class TestCanEdit(NotebookMixin):
    def test_owner_can_edit(self):
        assert can_edit(self.wendys_notebook, self.wendy) is True

    def test_editor_can_edit(self):
        assert can_edit(self.wendys_notebook, self.susan) is True

    def test_viewer_cannot_edit(self):
        assert can_edit(self.wendys_notebook, self.mary) is False

    def test_user_without_permission_cannot_edit(self):
        assert can_edit(self.wendys_notebook, self.hugh) is False

    def test_anonymous_cannot_edit(self):
        assert can_edit(self.wendys_notebook, AnonymousUser()) is False


@pytest.mark.django_db
class TestCanManage(NotebookMixin):
    def test_owner_can_manage(self):
        assert can_manage(self.wendys_notebook, self.wendy) is True

    def test_editor_cannot_manage(self):
        assert can_manage(self.wendys_notebook, self.susan) is False

    def test_viewer_cannot_manage(self):
        assert can_manage(self.wendys_notebook, self.mary) is False

    def test_user_without_permission_cannot_manage(self):
        assert can_manage(self.wendys_notebook, self.hugh) is False

    def test_anonymous_cannot_manage(self):
        assert can_manage(self.wendys_notebook, AnonymousUser()) is False


@pytest.mark.django_db
class TestIsWikiAndPlayerInThatCampaign(LinkedCampaignNotebooksMixin):
    def test_campaign_player_on_wiki(self):
        assert is_wiki_and_player_in_that_campaign(self.wiki, self.susan) is True

    def test_campaign_owner_on_wiki(self):
        assert is_wiki_and_player_in_that_campaign(self.wiki, self.wendy) is True

    def test_non_player_on_wiki(self):
        assert is_wiki_and_player_in_that_campaign(self.wiki, self.hugh) is False

    def test_user_on_non_wiki_notebook(self):
        assert is_wiki_and_player_in_that_campaign(
            self.wendys_notebook, self.susan
        ) is False

    def test_user_on_shared_notebook(self):
        # wiki is the campaign wiki for owned_campaign
        # attach it to a second campaign as a regular notebook
        other_campaign = Campaign.objects.create(owner=self.hugh, name="Other")
        CampaignNotebook.objects.create(
            campaign=other_campaign,
            notebook=self.wiki,
            linked_by=self.hugh,
        )

        # mary is a player in both campaigns, owns neither
        self.owned_campaign.players.add(self.mary)
        other_campaign.players.add(self.mary)

        # she is a campaign player because she's in owned_campaign
        assert is_wiki_and_player_in_that_campaign(self.wiki, self.mary) is True

        # remove mary from owned_campaign, and even though she is a player in
        # a campaign _using_ the notebook, it is now not true that she is a player
        # in the campaign that the notebook is the wiki _for_
        self.owned_campaign.players.remove(self.mary)
        assert is_wiki_and_player_in_that_campaign(self.wiki, self.mary) is False
