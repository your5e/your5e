from http import HTTPStatus

import pytest

from users.tests import UserMixin

from . import NotebookMixin


@pytest.mark.django_db
class TestNotebookView(NotebookMixin):
    @UserMixin.as_user("wendy")
    def test_owner_sees_management_controls(self, client):
        response = client.get("/notebooks/wendy/heros-legendes/")
        assert response.status_code == HTTPStatus.OK
        content = response.content.decode()
        self.assert_index_content_present(content, self.wendys_notebook)
        self.assert_can_manage(content)

    @UserMixin.as_user("susan")
    def test_editor_does_not_see_management_controls(self, client):
        response = client.get("/notebooks/wendy/heros-legendes/")
        content = response.content.decode()
        self.assert_index_content_present(content, self.wendys_notebook)
        self.assert_cannot_manage(content)

    @UserMixin.as_user("mary")
    def test_viewer_does_not_see_management_controls(self, client):
        response = client.get("/notebooks/wendy/heros-legendes/")
        content = response.content.decode()
        self.assert_index_content_present(content, self.wendys_notebook)
        self.assert_cannot_manage(content)

    @UserMixin.as_user("hugh")
    def test_non_collaborator_cannot_view_notebook(self, client):
        response = client.get("/notebooks/wendy/heros-legendes/")
        assert response.status_code == HTTPStatus.FORBIDDEN
        self.assert_index_content_absent(
            response.content.decode(),
            self.wendys_notebook,
        )

    def test_anonymous_cannot_view_notebook(self, client):
        response = client.get("/notebooks/wendy/heros-legendes/")
        assert response.status_code == HTTPStatus.UNAUTHORIZED
        self.assert_index_content_absent(
            response.content.decode(),
            self.wendys_notebook,
        )

    @UserMixin.as_user("susan")
    def test_notebook_shows_owner_link(self, client):
        response = client.get("/notebooks/wendy/heros-legendes/")
        content = response.content.decode()
        header = content.split("<h2>")[0]
        assert 'href="/profile/wendy/">wendy</a>' in header

    @UserMixin.as_user("wendy")
    def test_notebook_shows_campaign_link(self, client):
        from campaigns.models import Campaign, CampaignNotebook
        campaign = Campaign.objects.create(owner=self.wendy, name="The Great Quest")
        CampaignNotebook.objects.create(
            campaign=campaign,
            notebook=self.wendys_notebook,
            linked_by=self.wendy,
        )
        response = client.get("/notebooks/wendy/heros-legendes/")
        content = response.content.decode()
        assert 'href="/campaigns/wendy/the-great-quest/"' in content
        assert "The Great Quest" in content

    @UserMixin.as_user("wendy")
    def test_notebook_shows_multiple_campaign_links(self, client):
        from campaigns.models import Campaign, CampaignNotebook
        campaign = Campaign.objects.create(owner=self.wendy, name="The Great Quest")
        CampaignNotebook.objects.create(
            campaign=campaign,
            notebook=self.wendys_notebook,
            linked_by=self.wendy,
        )
        second_campaign = Campaign.objects.create(
            owner=self.susan,
            name="Side Adventure",
        )
        second_campaign.players.add(self.wendy)
        CampaignNotebook.objects.create(
            campaign=second_campaign,
            notebook=self.wendys_notebook,
            linked_by=self.susan,
        )
        response = client.get("/notebooks/wendy/heros-legendes/")
        content = response.content.decode()
        assert "The Great Quest" in content
        assert "Side Adventure" in content

    @UserMixin.as_user("wendy")
    def test_subfolder_index_shows_breadcrumbs_with_display_names(self, client):
        response = client.get(
            "/notebooks/wendy/heros-legendes/world-regions/northern-kingdoms/"
        )
        assert response.status_code == HTTPStatus.OK
        content = response.content.decode()
        assert ">World Regions</a>" in content
        assert ">Northern Kingdoms</a>" in content
        breadcrumb_section = content.split("breadcrumb")[1].split("</nav>")[0]
        assert "world-regions" not in breadcrumb_section
        assert "northern-kingdoms" not in breadcrumb_section

    @UserMixin.as_user("wendy")
    def test_recent_pages_shows_full_path(self, client):
        from wikis.models import Page
        page = Page.objects.create(wiki=self.wendys_notebook)
        page.update(
            filename="Quests/Dragon Hunt.md",
            mime_type="text/markdown",
            data=b"# Dragon Hunt",
            created_by=self.wendy,
        )
        response = client.get("/notebooks/wendy/heros-legendes/")
        content = response.content.decode()
        assert "Recent" in content
        base = "/notebooks/wendy/heros-legendes/"
        assert f'href="{base}quests/dragon-hunt">Quests/Dragon Hunt</a>' in content
