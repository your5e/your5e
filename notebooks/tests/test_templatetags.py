from datetime import timedelta

import pytest
from django.contrib.auth.models import AnonymousUser
from django.utils import timezone

from notebooks.templatetags.dates import smart_date
from notebooks.templatetags.notebook_permissions import can_edit, can_manage
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
