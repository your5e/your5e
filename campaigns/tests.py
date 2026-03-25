import html
from http import HTTPStatus

import pytest
from django.db import IntegrityError

from campaigns.models import Campaign, CampaignNotebook
from notebooks.models import Notebook, NotebookPermission
from users.tests import UserMixin
from wikis.models import Page


class CampaignMixin(UserMixin):
    @pytest.fixture(autouse=True)
    def setup_campaigns(self, setup_users):
        self.owned_campaign = Campaign.objects.create(
            owner=self.wendy,
            name="The Old Forest",
            description="A **bold** adventure with *italic* flair.",
        )
        self.joined_campaign = Campaign.objects.create(
            owner=self.susan,
            name="River Crossing",
        )
        self.joined_campaign.players.add(self.wendy)
        self.other_campaign = Campaign.objects.create(
            owner=self.mary,
            name="The Eastern Road",
        )
        self.owned_campaign.players.add(self.susan)

        self.wendys_notebook = Notebook.objects.create(
            name="Wendy's Notes",
            owner=self.wendy,
            visibility=Notebook.Visibility.PRIVATE,
        )
        page = Page.objects.create(wiki=self.wendys_notebook)
        page.update(
            filename="index.md",
            mime_type="text/markdown",
            data=b"# Wendy's Notes",
            created_by=self.wendy,
        )
        self.susans_notebook = Notebook.objects.create(
            name="Susan's Guide",
            owner=self.susan,
            visibility=Notebook.Visibility.PUBLIC,
        )
        page = Page.objects.create(wiki=self.susans_notebook)
        page.update(
            filename="index.md",
            mime_type="text/markdown",
            data=b"# Susan's Guide",
            created_by=self.susan,
        )
        self.marys_notebook = Notebook.objects.create(
            name="Mary's Prayer",
            owner=self.mary,
            visibility=Notebook.Visibility.PRIVATE,
        )
        NotebookPermission.objects.create(
            notebook=self.marys_notebook,
            user=self.wendy,
            role=NotebookPermission.Role.EDITOR,
        )
        NotebookPermission.objects.create(
            notebook=self.marys_notebook,
            user=self.susan,
            role=NotebookPermission.Role.VIEWER,
        )
        self.hughs_notebook = Notebook.objects.create(
            name="Hugh's Secrets",
            owner=self.hugh,
            visibility=Notebook.Visibility.PRIVATE,
        )
        self.empty_notebook = Notebook.objects.create(
            name="Empty Notebook",
            owner=self.wendy,
            visibility=Notebook.Visibility.PRIVATE,
        )


class LinkedCampaignNotebooksMixin(CampaignMixin):
    @pytest.fixture(autouse=True)
    def setup_linked_notebooks(self, setup_campaigns):
        self.wendys_link = CampaignNotebook.objects.create(
            campaign=self.owned_campaign,
            notebook=self.wendys_notebook,
            linked_by=self.wendy,
        )
        self.susans_link = CampaignNotebook.objects.create(
            campaign=self.owned_campaign,
            notebook=self.susans_notebook,
            linked_by=self.susan,
        )
        self.marys_link = CampaignNotebook.objects.create(
            campaign=self.owned_campaign,
            notebook=self.marys_notebook,
            linked_by=self.wendy,
        )


@pytest.mark.django_db
class TestCampaign(CampaignMixin):
    def test_slug_generated_from_name(self):
        campaign = Campaign.objects.create(
            owner=self.wendy,
            name="Journey to the North",
        )
        assert campaign.slug == "journey-to-the-north"

    def test_slug_unique_per_owner(self):
        Campaign.objects.create(owner=self.wendy, name="Journey!")
        campaign2 = Campaign.objects.create(owner=self.wendy, name="Journey?")
        assert campaign2.slug == "journey-2"

    def test_slug_not_shared_across_owners(self):
        campaign1 = Campaign.objects.create(
            owner=self.wendy, name="Journey to the North"
        )
        campaign2 = Campaign.objects.create(
            owner=self.susan, name="Journey to the North"
        )
        assert campaign1.slug == "journey-to-the-north"
        assert campaign2.slug == "journey-to-the-north"

    def test_owner_added_to_players_on_create(self):
        campaign = Campaign.objects.create(
            owner=self.wendy,
            name="Journey to the North",
        )
        assert self.wendy in campaign.players.all()

    def test_join_slug_generated_on_create(self):
        campaign = Campaign.objects.create(
            owner=self.wendy,
            name="Journey to the North",
        )
        assert campaign.join_slug
        assert len(campaign.join_slug) >= 8

    def test_join_slug_unique_per_campaign(self):
        campaign1 = Campaign.objects.create(owner=self.wendy, name="First Campaign")
        campaign2 = Campaign.objects.create(owner=self.wendy, name="Second Campaign")
        assert campaign1.join_slug != campaign2.join_slug

    def test_has_content_false_for_owner_only(self):
        assert self.other_campaign.has_content() is False

    def test_has_content_true_with_other_players(self):
        self.owned_campaign.players.add(self.susan)
        assert self.owned_campaign.has_content() is True

    def test_has_content_false_with_empty_notebooks(self):
        CampaignNotebook.objects.create(
            campaign=self.other_campaign,
            notebook=self.empty_notebook,
            linked_by=self.mary,
        )
        assert self.other_campaign.has_content() is False

    def test_has_content_true_with_non_empty_notebooks(self):
        notebook = Notebook.objects.create(name="Notes", owner=self.wendy)
        page = Page.objects.create(wiki=notebook)
        page.update(
            filename="index.md",
            mime_type="text/markdown",
            data=b"# Notes",
            created_by=self.wendy,
        )
        CampaignNotebook.objects.create(
            campaign=self.owned_campaign,
            notebook=notebook,
            linked_by=self.wendy,
        )
        assert self.owned_campaign.has_content() is True

    def test_description_html_renders_markdown(self):
        assert "<strong>bold</strong>" in self.owned_campaign.description_html()
        assert "<em>italic</em>" in self.owned_campaign.description_html()

    def test_description_html_strips_html_tags(self):
        self.other_campaign.description = (
            "<div>block</div><b>bold</b><sup>super</sup><x>custom</x>"
        )
        assert self.other_campaign.description_html() == "<p>blockboldsupercustom</p>"

    def test_description_html_empty_when_no_description(self):
        assert self.other_campaign.description_html() == ""


@pytest.mark.django_db
class TestCampaignCreateView(UserMixin):
    def test_anonymous_get_redirected_to_login(self, client):
        response = client.get("/campaigns/create")
        assert response.status_code == HTTPStatus.FOUND
        assert response.url == "/login?next=/campaigns/create"

    def test_anonymous_post_redirected_to_login(self, client):
        response = client.post("/campaigns/create", {"name": "New Campaign"})
        assert response.status_code == HTTPStatus.FOUND
        assert response.url == "/login?next=/campaigns/create"

    @UserMixin.as_user("wendy")
    def test_shows_create_form(self, client):
        response = client.get("/campaigns/create")
        assert response.status_code == HTTPStatus.OK
        content = response.content.decode()
        assert 'name="name"' in content

    @UserMixin.as_user("wendy")
    def test_user_can_create_campaign(self, client):
        response = client.post("/campaigns/create", {"name": "New Campaign"})
        assert response.status_code == HTTPStatus.FOUND
        assert response.url == "/campaigns/wendy/new-campaign"
        assert Campaign.objects.filter(name="New Campaign", owner=self.wendy).exists()


@pytest.mark.django_db
class TestProfileViewCampaigns(CampaignMixin):
    @CampaignMixin.as_user("wendy")
    def test_shows_owned_campaigns(self, client):
        response = client.get("/profile/wendy/")
        content = response.content.decode()
        assert "The Old Forest" in content

    @CampaignMixin.as_user("wendy")
    def test_shows_joined_campaigns(self, client):
        response = client.get("/profile/wendy/")
        content = response.content.decode()
        assert "River Crossing" in content

    @CampaignMixin.as_user("wendy")
    def test_hides_unrelated_campaigns(self, client):
        response = client.get("/profile/wendy/")
        content = response.content.decode()
        assert "The Eastern Road" not in content


@pytest.mark.django_db
class TestCampaignSettingsView(CampaignMixin):
    @CampaignMixin.as_user("wendy")
    def test_owner_can_access_settings(self, client):
        self.owned_campaign.description = "A forest of old trees"
        self.owned_campaign.save()
        response = client.get("/campaigns/settings/wendy/the-old-forest")
        assert response.status_code == HTTPStatus.OK
        content = response.content.decode()
        assert 'name="name" value="The Old Forest"' in content
        assert 'name="description"' in content
        assert "A forest of old trees" in content
        assert f"/campaigns/join-{self.owned_campaign.join_slug}" in content
        assert 'name="regenerate_join_slug"' in content
        assert f'name="remove_player" value="{self.susan.pk}"' in content
        assert f'name="remove_player" value="{self.wendy.pk}"' not in content
        assert 'action="/campaigns/delete"' in content

    @CampaignMixin.as_user("susan")
    def test_player_cannot_access_settings(self, client):
        response = client.get("/campaigns/settings/wendy/the-old-forest")
        assert response.status_code == HTTPStatus.FORBIDDEN

    @CampaignMixin.as_user("mary")
    def test_non_member_cannot_access_settings(self, client):
        response = client.get("/campaigns/settings/wendy/the-old-forest")
        assert response.status_code == HTTPStatus.FORBIDDEN

    def test_anonymous_cannot_access_settings(self, client):
        response = client.get("/campaigns/settings/wendy/the-old-forest")
        assert response.status_code == HTTPStatus.UNAUTHORIZED


@pytest.mark.django_db
class TestCampaignView(CampaignMixin):
    @CampaignMixin.as_user("wendy")
    def test_owner_view(self, client):
        self.owned_campaign.players.add(self.susan)
        response = client.get("/campaigns/wendy/the-old-forest")
        content = response.content.decode()
        assert response.status_code == HTTPStatus.OK
        assert 'class="campaign-name">The Old Forest</p>' in content
        assert f"/campaigns/join-{self.owned_campaign.join_slug}" in content
        assert '<a href="/profile/wendy/">wendy</a>' in content
        assert "/campaigns/settings/wendy/the-old-forest" in content

    @CampaignMixin.as_user("wendy")
    def test_player_view(self, client):
        response = client.get("/campaigns/susan/river-crossing")
        content = response.content.decode()
        assert response.status_code == HTTPStatus.OK
        assert 'class="campaign-name">River Crossing</p>' in content
        assert '<a href="/profile/susan/">susan</a>' in content
        assert "/campaigns/settings/susan/river-crossing" not in content
        assert self.joined_campaign.join_slug in content

    @CampaignMixin.as_user("wendy")
    def test_member_sees_leave_button(self, client):
        response = client.get("/campaigns/susan/river-crossing")
        content = response.content.decode()
        assert 'action="/campaigns/leave"' in content

    @CampaignMixin.as_user("wendy")
    def test_non_player_forbidden(self, client):
        response = client.get("/campaigns/mary/the-eastern-road")
        assert response.status_code == HTTPStatus.FORBIDDEN

    def test_anonymous_unauthorised(self, client):
        response = client.get("/campaigns/wendy/the-old-forest")
        assert response.status_code == HTTPStatus.UNAUTHORIZED

    @CampaignMixin.as_user("wendy")
    def test_owner_can_edit(self, client):
        response = client.post(
            "/campaigns/wendy/the-old-forest",
            {"name": "The New Forest", "description": "A dark and mysterious forest."},
        )
        self.owned_campaign.refresh_from_db()
        assert response.status_code == HTTPStatus.FOUND
        assert response.url == "/campaigns/wendy/the-new-forest"
        assert self.owned_campaign.name == "The New Forest"
        assert self.owned_campaign.slug == "the-new-forest"
        assert self.owned_campaign.description == "A dark and mysterious forest."

    @CampaignMixin.as_user("wendy")
    def test_edit_slug_collision(self, client):
        Campaign.objects.create(owner=self.wendy, name="Journey!")
        response = client.post(
            "/campaigns/wendy/the-old-forest",
            {"name": "Journey?", "description": ""},
        )
        self.owned_campaign.refresh_from_db()
        assert response.url == "/campaigns/wendy/journey-2"
        assert self.owned_campaign.slug == "journey-2"

    @CampaignMixin.as_user("wendy")
    def test_owner_regenerate_join_slug(self, client):
        old_join_slug = self.owned_campaign.join_slug
        response = client.post(
            "/campaigns/wendy/the-old-forest",
            {"regenerate_join_slug": "true"},
        )
        self.owned_campaign.refresh_from_db()
        assert response.status_code == HTTPStatus.FOUND
        assert self.owned_campaign.join_slug != old_join_slug

    @CampaignMixin.as_user("wendy")
    def test_owner_remove_player(self, client):
        self.owned_campaign.players.add(self.susan)
        response = client.post(
            "/campaigns/wendy/the-old-forest",
            {"remove_player": self.susan.pk},
        )
        assert response.status_code == HTTPStatus.FOUND
        assert self.susan not in self.owned_campaign.players.all()

    @CampaignMixin.as_user("wendy")
    def test_owner_cannot_remove_self(self, client):
        response = client.post(
            "/campaigns/wendy/the-old-forest",
            {"remove_player": self.wendy.pk},
        )
        assert response.status_code == HTTPStatus.FORBIDDEN
        assert self.wendy in self.owned_campaign.players.all()

    @CampaignMixin.as_user("wendy")
    def test_cannot_leave_directly_from_campaign_page(self, client):
        response = client.post(
            "/campaigns/susan/river-crossing",
            {"leave": "true"},
        )
        assert response.status_code == HTTPStatus.FORBIDDEN
        assert self.wendy in self.joined_campaign.players.all()

    @CampaignMixin.as_user("wendy")
    def test_player_cannot_modify(self, client):
        old_join_slug = self.joined_campaign.join_slug
        client.post(
            "/campaigns/susan/river-crossing",
            {"name": "Hacked Name", "description": "Hacked"},
        )
        client.post(
            "/campaigns/susan/river-crossing",
            {"regenerate_join_slug": "true"},
        )
        client.post(
            "/campaigns/susan/river-crossing",
            {"remove_player": self.susan.pk},
        )
        self.joined_campaign.refresh_from_db()
        assert self.joined_campaign.name == "River Crossing"
        assert self.joined_campaign.description == ""
        assert self.joined_campaign.join_slug == old_join_slug
        assert self.susan in self.joined_campaign.players.all()

    @CampaignMixin.as_user("wendy")
    def test_description_rendered_as_markdown(self, client):
        response = client.get("/campaigns/wendy/the-old-forest")
        content = response.content.decode()
        assert '<div class="user-content">' in content
        assert "<strong>bold</strong>" in content
        assert "<em>italic</em>" in content


@pytest.mark.django_db
class TestCampaignJoinView(CampaignMixin):
    def test_anonymous_redirected_to_login(self, client):
        url = f"/campaigns/join-{self.other_campaign.join_slug}"
        response = client.get(url)
        assert response.status_code == HTTPStatus.FOUND
        assert response.url == f"/login?next={url}"

    @CampaignMixin.as_user("mary")
    def test_shows_confirmation_page(self, client):
        response = client.get(f"/campaigns/join-{self.owned_campaign.join_slug}")
        content = response.content.decode()
        normalised = " ".join(content.split())
        assert response.status_code == HTTPStatus.OK
        assert "The Old Forest" in content
        assert "Join" in content
        assert "<strong>bold</strong>" in normalised
        assert "<li> wendy (owner) </li>" in normalised
        assert "<li> susan </li>" in normalised

    @CampaignMixin.as_user("mary")
    def test_uses_header_stripe(self, client):
        response = client.get(f"/campaigns/join-{self.owned_campaign.join_slug}")
        content = response.content.decode()
        assert 'class="campaign-header"' in content
        assert 'class="campaign-name"' in content

    @CampaignMixin.as_user("mary")
    def test_non_member_does_not_see_leave_button(self, client):
        response = client.get(f"/campaigns/join-{self.owned_campaign.join_slug}")
        content = response.content.decode()
        assert 'action="/campaigns/leave"' not in content

    @CampaignMixin.as_user("wendy")
    def test_post_joins_campaign(self, client):
        response = client.post(f"/campaigns/join-{self.other_campaign.join_slug}")
        assert response.status_code == HTTPStatus.FOUND
        assert response.url == "/campaigns/mary/the-eastern-road"
        assert self.wendy in self.other_campaign.players.all()

    @CampaignMixin.as_user("wendy")
    def test_already_member_shows_link(self, client):
        response = client.get(f"/campaigns/join-{self.owned_campaign.join_slug}")
        content = response.content.decode()
        assert response.status_code == HTTPStatus.OK
        assert "already" in content.lower()
        assert "/campaigns/wendy/the-old-forest" in content

    def test_invalid_join_slug_returns_404(self, client):
        response = client.get("/campaigns/join-nonexistent")
        assert response.status_code == HTTPStatus.NOT_FOUND


@pytest.mark.django_db
class TestCampaignLeaveView(CampaignMixin):
    @CampaignMixin.as_user("wendy")
    def test_player_sees_confirmation_page(self, client):
        response = client.post(
            "/campaigns/leave",
            {"campaign": self.joined_campaign.pk},
        )
        content = response.content.decode()
        assert response.status_code == HTTPStatus.OK
        assert "River Crossing" in content
        assert "leave" in content.lower()

    @CampaignMixin.as_user("wendy")
    def test_player_can_leave(self, client):
        response = client.post(
            "/campaigns/leave",
            {"campaign": self.joined_campaign.pk, "confirm": "true"},
        )
        assert response.status_code == HTTPStatus.FOUND
        assert response.url == "/profile/wendy/"
        assert self.wendy not in self.joined_campaign.players.all()

    @CampaignMixin.as_user("wendy")
    def test_owner_can_leave_with_other_players(self, client):
        from users.models import get_sentinel_user
        self.owned_campaign.players.add(self.susan)
        response = client.post(
            "/campaigns/leave",
            {"campaign": self.owned_campaign.pk, "confirm": "true"},
        )
        self.owned_campaign.refresh_from_db()
        assert response.status_code == HTTPStatus.FOUND
        assert response.url == "/profile/wendy/"
        assert self.owned_campaign.owner == get_sentinel_user()
        assert self.wendy not in self.owned_campaign.players.all()

    @CampaignMixin.as_user("mary")
    def test_owner_leave_without_players_deletes_campaign(self, client):
        campaign_id = self.other_campaign.id
        response = client.post(
            "/campaigns/leave",
            {"campaign": self.other_campaign.pk, "confirm": "true"},
        )
        assert response.status_code == HTTPStatus.FOUND
        assert response.url == "/profile/mary/"
        assert not Campaign.objects.filter(id=campaign_id).exists()

    @CampaignMixin.as_user("mary")
    def test_non_player_cannot_access_leave(self, client):
        response = client.post(
            "/campaigns/leave",
            {"campaign": self.owned_campaign.pk},
        )
        assert response.status_code == HTTPStatus.FORBIDDEN

    def test_anonymous_cannot_access_leave(self, client):
        response = client.post(
            "/campaigns/leave",
            {"campaign": self.owned_campaign.pk},
        )
        assert response.status_code == HTTPStatus.UNAUTHORIZED


@pytest.mark.django_db
class TestCampaignDeleteView(CampaignMixin):
    @CampaignMixin.as_user("mary")
    def test_empty_campaign_deletes_immediately(self, client):
        campaign_id = self.other_campaign.id
        response = client.post(
            "/campaigns/delete",
            {"campaign": self.other_campaign.pk},
        )
        assert response.status_code == HTTPStatus.FOUND
        assert response.url == "/profile/mary/"
        assert not Campaign.objects.filter(id=campaign_id).exists()

    @CampaignMixin.as_user("wendy")
    def test_campaign_with_players_shows_confirmation(self, client):
        self.owned_campaign.players.add(self.susan)
        response = client.post(
            "/campaigns/delete",
            {"campaign": self.owned_campaign.pk},
        )
        content = response.content.decode()
        assert response.status_code == HTTPStatus.OK
        assert "The Old Forest" in content
        assert "delete" in content.lower()
        assert Campaign.objects.filter(id=self.owned_campaign.id).exists()

    @CampaignMixin.as_user("wendy")
    def test_campaign_with_content_can_delete_after_confirmation(self, client):
        self.owned_campaign.players.add(self.susan)
        campaign_id = self.owned_campaign.id
        response = client.post(
            "/campaigns/delete",
            {"campaign": self.owned_campaign.pk, "confirm": "true"},
        )
        assert response.status_code == HTTPStatus.FOUND
        assert response.url == "/profile/wendy/"
        assert not Campaign.objects.filter(id=campaign_id).exists()

    @CampaignMixin.as_user("wendy")
    def test_player_cannot_delete(self, client):
        response = client.post(
            "/campaigns/delete",
            {"campaign": self.joined_campaign.pk},
        )
        assert response.status_code == HTTPStatus.FORBIDDEN

    @CampaignMixin.as_user("mary")
    def test_non_player_cannot_delete(self, client):
        response = client.post(
            "/campaigns/delete",
            {"campaign": self.owned_campaign.pk},
        )
        assert response.status_code == HTTPStatus.FORBIDDEN

    def test_anonymous_cannot_delete(self, client):
        response = client.post(
            "/campaigns/delete",
            {"campaign": self.owned_campaign.pk},
        )
        assert response.status_code == HTTPStatus.UNAUTHORIZED

    @CampaignMixin.as_user("mary")
    def test_campaign_with_empty_notebooks_deletes_immediately(self, client):
        CampaignNotebook.objects.create(
            campaign=self.other_campaign,
            notebook=self.empty_notebook,
            linked_by=self.mary,
        )
        campaign_id = self.other_campaign.id
        response = client.post(
            "/campaigns/delete",
            {"campaign": self.other_campaign.pk},
        )
        assert response.status_code == HTTPStatus.FOUND
        assert response.url == "/profile/mary/"
        assert not Campaign.objects.filter(id=campaign_id).exists()

    @CampaignMixin.as_user("wendy")
    def test_campaign_with_non_empty_notebooks_shows_confirmation(self, client):
        CampaignNotebook.objects.create(
            campaign=self.owned_campaign,
            notebook=self.wendys_notebook,
            linked_by=self.wendy,
        )
        response = client.post(
            "/campaigns/delete",
            {"campaign": self.owned_campaign.pk},
        )
        content = response.content.decode()
        assert response.status_code == HTTPStatus.OK
        assert "The Old Forest" in content
        assert "delete" in content.lower()
        assert Campaign.objects.filter(id=self.owned_campaign.id).exists()


@pytest.mark.django_db
class TestCampaignNotebook(CampaignMixin):
    def test_create_links_notebook_to_campaign(self):
        link = CampaignNotebook.objects.create(
            campaign=self.owned_campaign,
            notebook=self.wendys_notebook,
            linked_by=self.wendy,
        )
        assert link.campaign == self.owned_campaign
        assert link.notebook == self.wendys_notebook
        assert link.linked_by == self.wendy
        assert link.order == 0

    def test_order_increments_for_each_link(self):
        link1 = CampaignNotebook.objects.create(
            campaign=self.owned_campaign,
            notebook=self.wendys_notebook,
            linked_by=self.wendy,
        )
        link2 = CampaignNotebook.objects.create(
            campaign=self.owned_campaign,
            notebook=self.susans_notebook,
            linked_by=self.susan,
        )
        assert link1.order == 0
        assert link2.order == 1

    def test_same_notebook_cannot_be_linked_twice(self):
        CampaignNotebook.objects.create(
            campaign=self.owned_campaign,
            notebook=self.wendys_notebook,
            linked_by=self.wendy,
        )
        with pytest.raises(IntegrityError):
            CampaignNotebook.objects.create(
                campaign=self.owned_campaign,
                notebook=self.wendys_notebook,
                linked_by=self.susan,
            )

    def test_same_notebook_can_be_linked_to_multiple_campaigns(self):
        link1 = CampaignNotebook.objects.create(
            campaign=self.owned_campaign,
            notebook=self.wendys_notebook,
            linked_by=self.wendy,
        )
        link2 = CampaignNotebook.objects.create(
            campaign=self.joined_campaign,
            notebook=self.wendys_notebook,
            linked_by=self.wendy,
        )
        assert link1.notebook == link2.notebook
        assert link1.campaign != link2.campaign


@pytest.mark.django_db
class TestCampaignNotebookLinkView(CampaignMixin):
    @CampaignMixin.as_user("wendy")
    def test_owner_can_link_owned_notebook(self, client):
        response = client.post("/campaigns/notebooks", {
            "campaign": self.owned_campaign.pk,
            "link_notebook": self.wendys_notebook.pk,
        })
        assert response.status_code == HTTPStatus.FOUND
        assert CampaignNotebook.objects.filter(
            campaign=self.owned_campaign,
            notebook=self.wendys_notebook,
            linked_by=self.wendy,
        ).exists()

    @CampaignMixin.as_user("susan")
    def test_player_can_link_owned_notebook(self, client):
        response = client.post("/campaigns/notebooks", {
            "campaign": self.owned_campaign.pk,
            "link_notebook": self.susans_notebook.pk,
        })
        assert response.status_code == HTTPStatus.FOUND
        assert CampaignNotebook.objects.filter(
            campaign=self.owned_campaign,
            notebook=self.susans_notebook,
            linked_by=self.susan,
        ).exists()

    @CampaignMixin.as_user("wendy")
    def test_player_can_link_public_notebook(self, client):
        response = client.post("/campaigns/notebooks", {
            "campaign": self.owned_campaign.pk,
            "link_notebook": self.susans_notebook.pk,
        })
        assert response.status_code == HTTPStatus.FOUND
        assert CampaignNotebook.objects.filter(
            campaign=self.owned_campaign,
            notebook=self.susans_notebook,
            linked_by=self.wendy,
        ).exists()

    @CampaignMixin.as_user("wendy")
    def test_cannot_link_private_notebook_without_access(self, client):
        response = client.post("/campaigns/notebooks", {
            "campaign": self.owned_campaign.pk,
            "link_notebook": self.hughs_notebook.pk,
        })
        assert response.status_code == HTTPStatus.FORBIDDEN
        assert not CampaignNotebook.objects.filter(
            notebook=self.hughs_notebook,
        ).exists()

    @CampaignMixin.as_user("wendy")
    def test_cannot_link_same_notebook_twice(self, client):
        CampaignNotebook.objects.create(
            campaign=self.owned_campaign,
            notebook=self.wendys_notebook,
            linked_by=self.wendy,
        )
        response = client.post("/campaigns/notebooks", {
            "campaign": self.owned_campaign.pk,
            "link_notebook": self.wendys_notebook.pk,
        })
        assert response.status_code == HTTPStatus.BAD_REQUEST
        assert CampaignNotebook.objects.filter(
            campaign=self.owned_campaign,
            notebook=self.wendys_notebook,
        ).count() == 1

    @CampaignMixin.as_user("hugh")
    def test_non_member_cannot_link_notebook(self, client):
        response = client.post("/campaigns/notebooks", {
            "campaign": self.owned_campaign.pk,
            "link_notebook": self.hughs_notebook.pk,
        })
        assert response.status_code == HTTPStatus.FORBIDDEN
        assert not CampaignNotebook.objects.filter(
            notebook=self.hughs_notebook,
        ).exists()

    def test_anonymous_cannot_link_notebook(self, client):
        response = client.post("/campaigns/notebooks", {
            "campaign": self.owned_campaign.pk,
            "link_notebook": self.wendys_notebook.pk,
        })
        assert response.status_code == HTTPStatus.UNAUTHORIZED
        assert not CampaignNotebook.objects.filter(
            campaign=self.owned_campaign,
        ).exists()


@pytest.mark.django_db
class TestCampaignNotebookRemoveView(LinkedCampaignNotebooksMixin):
    @LinkedCampaignNotebooksMixin.as_user("wendy")
    def test_campaign_owner_can_remove_any_notebook(self, client):
        response = client.post("/campaigns/notebooks", {
            "campaign": self.owned_campaign.pk,
            "unlink_notebook": self.susans_link.pk,
        })
        assert response.status_code == HTTPStatus.FOUND
        assert not CampaignNotebook.objects.filter(pk=self.susans_link.pk).exists()

    @LinkedCampaignNotebooksMixin.as_user("susan")
    def test_notebook_owner_can_remove_their_notebook(self, client):
        response = client.post("/campaigns/notebooks", {
            "campaign": self.owned_campaign.pk,
            "unlink_notebook": self.susans_link.pk,
        })
        assert response.status_code == HTTPStatus.FOUND
        assert not CampaignNotebook.objects.filter(pk=self.susans_link.pk).exists()

    @LinkedCampaignNotebooksMixin.as_user("susan")
    def test_linker_can_remove_notebook_they_linked(self, client):
        response = client.post("/campaigns/notebooks", {
            "campaign": self.owned_campaign.pk,
            "unlink_notebook": self.susans_link.pk,
        })
        assert response.status_code == HTTPStatus.FOUND
        assert not CampaignNotebook.objects.filter(pk=self.susans_link.pk).exists()

    @LinkedCampaignNotebooksMixin.as_user("susan")
    def test_player_cannot_remove_notebook_they_did_not_link_or_own(self, client):
        response = client.post("/campaigns/notebooks", {
            "campaign": self.owned_campaign.pk,
            "unlink_notebook": self.wendys_link.pk,
        })
        assert response.status_code == HTTPStatus.FORBIDDEN
        assert CampaignNotebook.objects.filter(pk=self.wendys_link.pk).exists()

    @LinkedCampaignNotebooksMixin.as_user("hugh")
    def test_non_member_cannot_remove_notebook(self, client):
        response = client.post("/campaigns/notebooks", {
            "campaign": self.owned_campaign.pk,
            "unlink_notebook": self.wendys_link.pk,
        })
        assert response.status_code == HTTPStatus.FORBIDDEN
        assert CampaignNotebook.objects.filter(pk=self.wendys_link.pk).exists()

    def test_anonymous_cannot_remove_notebook(self, client):
        response = client.post("/campaigns/notebooks", {
            "campaign": self.owned_campaign.pk,
            "unlink_notebook": self.wendys_link.pk,
        })
        assert response.status_code == HTTPStatus.UNAUTHORIZED
        assert CampaignNotebook.objects.filter(pk=self.wendys_link.pk).exists()


@pytest.mark.django_db
class TestCampaignNotebookOrderView(LinkedCampaignNotebooksMixin):
    @LinkedCampaignNotebooksMixin.as_user("wendy")
    def test_owner_can_move_notebook_up(self, client):
        response = client.post(
            "/campaigns/notebooks",
            {
                "campaign": self.owned_campaign.pk,
                "move_notebook_up": self.susans_link.pk,
            },
        )
        assert response.status_code == HTTPStatus.FOUND
        self.wendys_link.refresh_from_db()
        self.susans_link.refresh_from_db()
        assert self.susans_link.order < self.wendys_link.order

    @LinkedCampaignNotebooksMixin.as_user("wendy")
    def test_owner_can_move_notebook_down(self, client):
        response = client.post(
            "/campaigns/notebooks",
            {
                "campaign": self.owned_campaign.pk,
                "move_notebook_down": self.wendys_link.pk,
            },
        )
        assert response.status_code == HTTPStatus.FOUND
        self.wendys_link.refresh_from_db()
        self.susans_link.refresh_from_db()
        assert self.wendys_link.order > self.susans_link.order

    @LinkedCampaignNotebooksMixin.as_user("susan")
    def test_player_cannot_reorder_notebooks(self, client):
        original_order1 = self.wendys_link.order
        original_order2 = self.susans_link.order
        response = client.post(
            "/campaigns/notebooks",
            {
                "campaign": self.owned_campaign.pk,
                "move_notebook_up": self.susans_link.pk,
            },
        )
        assert response.status_code == HTTPStatus.FORBIDDEN
        self.wendys_link.refresh_from_db()
        self.susans_link.refresh_from_db()
        assert self.wendys_link.order == original_order1
        assert self.susans_link.order == original_order2

    @LinkedCampaignNotebooksMixin.as_user("hugh")
    def test_non_member_cannot_reorder_notebooks(self, client):
        response = client.post(
            "/campaigns/notebooks",
            {
                "campaign": self.owned_campaign.pk,
                "move_notebook_up": self.susans_link.pk,
            },
        )
        assert response.status_code == HTTPStatus.FORBIDDEN

    def test_anonymous_cannot_reorder_notebooks(self, client):
        response = client.post(
            "/campaigns/notebooks",
            {
                "campaign": self.owned_campaign.pk,
                "move_notebook_up": self.susans_link.pk,
            },
        )
        assert response.status_code == HTTPStatus.UNAUTHORIZED


@pytest.mark.django_db
class TestCampaignViewNotebooks(LinkedCampaignNotebooksMixin):
    @LinkedCampaignNotebooksMixin.as_user("wendy")
    def test_owner_sees_all_accessible_notebooks(self, client):
        response = client.get("/campaigns/wendy/the-old-forest")
        content = response.content.decode()
        assert html.escape("Wendy's Notes") in content
        assert html.escape("Susan's Guide") in content
        assert html.escape("Mary's Prayer") in content

    @LinkedCampaignNotebooksMixin.as_user("susan")
    def test_player_sees_only_accessible_notebooks(self, client):
        response = client.get("/campaigns/wendy/the-old-forest")
        content = response.content.decode()
        assert html.escape("Wendy's Notes") not in content
        assert html.escape("Susan's Guide") in content
        assert html.escape("Mary's Prayer") in content

    @LinkedCampaignNotebooksMixin.as_user("wendy")
    def test_notebook_shows_owner(self, client):
        response = client.get("/campaigns/wendy/the-old-forest")
        content = response.content.decode()
        assert "by wendy" in content or "by Wendy" in content

    @LinkedCampaignNotebooksMixin.as_user("wendy")
    def test_notebook_only_shows_editors_and_viewers_who_are_players(self, client):
        NotebookPermission.objects.create(
            notebook=self.wendys_notebook,
            user=self.hugh,
            role=NotebookPermission.Role.EDITOR,
        )
        response = client.get("/campaigns/wendy/the-old-forest")
        content = response.content.decode()
        normalised = " ".join(content.split())
        assert "wendy can edit" in normalised
        assert "susan can see" in normalised
        assert "hugh" not in content

    @LinkedCampaignNotebooksMixin.as_user("wendy")
    def test_notebook_owner_sees_cannot_see_warning(self, client):
        response = client.get("/campaigns/wendy/the-old-forest")
        content = response.content.decode()
        normalised = " ".join(content.split()).lower()
        assert "susan cannot see" in normalised

    @LinkedCampaignNotebooksMixin.as_user("susan")
    def test_non_owner_does_not_see_cannot_see_warning(self, client):
        response = client.get("/campaigns/wendy/the-old-forest")
        content = response.content.decode()
        assert "cannot see" not in content.lower()

    @LinkedCampaignNotebooksMixin.as_user("wendy")
    def test_notebooks_appear_in_order(self, client):
        response = client.get("/campaigns/wendy/the-old-forest")
        content = response.content.decode()
        notes = content.find(html.escape("Wendy's Notes"))
        guide = content.find(html.escape("Susan's Guide"))
        prayer = content.find(html.escape("Mary's Prayer"))
        assert notes < guide < prayer

    @LinkedCampaignNotebooksMixin.as_user("wendy")
    def test_owner_sees_reorder_controls(self, client):
        response = client.get("/campaigns/wendy/the-old-forest")
        content = response.content.decode()
        assert "move_notebook_up" in content
        assert "move_notebook_down" in content

    @LinkedCampaignNotebooksMixin.as_user("wendy")
    def test_first_notebook_has_no_up_button(self, client):
        response = client.get("/campaigns/wendy/the-old-forest")
        content = response.content.decode()
        after_name = content.split(html.escape("Wendy's Notes"))[1]
        wendys_section = after_name.split("</li>")[0]
        assert "move_notebook_up" not in wendys_section

    @LinkedCampaignNotebooksMixin.as_user("wendy")
    def test_last_notebook_has_no_down_button(self, client):
        response = client.get("/campaigns/wendy/the-old-forest")
        content = response.content.decode()
        after_name = content.split(html.escape("Mary's Prayer"))[1]
        marys_section = after_name.split("</li>")[0]
        assert "move_notebook_down" not in marys_section

    @LinkedCampaignNotebooksMixin.as_user("susan")
    def test_player_does_not_see_reorder_controls(self, client):
        response = client.get("/campaigns/wendy/the-old-forest")
        content = response.content.decode()
        assert "move_notebook_up" not in content
        assert "move_notebook_down" not in content

    @LinkedCampaignNotebooksMixin.as_user("wendy")
    def test_owner_sees_link_notebook_dropdown(self, client):
        response = client.get("/campaigns/wendy/the-old-forest")
        content = response.content.decode()
        assert "link_notebook" in content

    @LinkedCampaignNotebooksMixin.as_user("susan")
    def test_player_sees_link_notebook_dropdown(self, client):
        response = client.get("/campaigns/wendy/the-old-forest")
        content = response.content.decode()
        assert "link_notebook" in content


@pytest.mark.django_db
class TestCampaignCreateNotebook(CampaignMixin):
    @CampaignMixin.as_user("wendy")
    def test_owner_sees_create_notebook_form(self, client):
        response = client.get("/campaigns/wendy/the-old-forest")
        content = response.content.decode()
        assert 'action="/notebooks/create"' in content

    @CampaignMixin.as_user("susan")
    def test_player_sees_create_notebook_form(self, client):
        self.owned_campaign.players.add(self.susan)
        response = client.get("/campaigns/wendy/the-old-forest")
        content = response.content.decode()
        assert 'action="/notebooks/create"' in content

    @CampaignMixin.as_user("wendy")
    def test_create_notebook_form_prepopulates_players(self, client):
        self.owned_campaign.players.add(self.susan, self.mary)
        response = client.get("/campaigns/wendy/the-old-forest")
        content = response.content.decode()
        assert f'name="prepopulate_collaborator" value="{self.susan.pk}"' in content
        assert f'name="prepopulate_collaborator" value="{self.mary.pk}"' in content

    @CampaignMixin.as_user("wendy")
    def test_create_notebook_form_excludes_current_user(self, client):
        self.owned_campaign.players.add(self.susan)
        response = client.get("/campaigns/wendy/the-old-forest")
        content = response.content.decode()
        assert f'name="prepopulate_collaborator" value="{self.wendy.pk}"' not in content
        assert f'name="prepopulate_collaborator" value="{self.susan.pk}"' in content

    @CampaignMixin.as_user("wendy")
    def test_create_notebook_links_to_campaign(self, client):
        # POST from campaign page asserts campaign
        response = client.post("/notebooks/create", {
            "campaign": str(self.owned_campaign.pk),
        })
        assert response.status_code == HTTPStatus.OK
        content = response.content.decode()
        assert f'name="campaign" value="{self.owned_campaign.pk}"' in content

        # submitting that form creates linked notebook
        response = client.post("/notebooks/create", {
            "name": "Quest Log",
            "visibility": "private",
            "campaign": str(self.owned_campaign.pk),
            "create": "true",
        })
        assert response.status_code == HTTPStatus.FOUND
        notebook = Notebook.objects.get(name="Quest Log")
        link = CampaignNotebook.objects.get(
            campaign=self.owned_campaign,
            notebook=notebook,
        )
        assert link.linked_by == self.wendy


@pytest.mark.django_db
class TestCampaignOwnerDeletion(CampaignMixin):
    def test_campaign_reassigned_to_sentinel_when_owner_deleted_with_players(self):
        from users.models import get_sentinel_user
        self.owned_campaign.players.add(self.susan)
        self.wendy.delete()
        self.owned_campaign.refresh_from_db()
        assert self.owned_campaign.owner == get_sentinel_user()
        assert self.susan in self.owned_campaign.players.all()

    def test_campaign_deleted_when_owner_deleted_without_players(self):
        campaign_id = self.other_campaign.id
        self.mary.delete()
        assert not Campaign.objects.filter(id=campaign_id).exists()


@pytest.mark.django_db
class TestCampaignClaimView(CampaignMixin):
    @pytest.fixture(autouse=True)
    def setup_unclaimed_campaign(self, setup_campaigns):
        from users.models import get_sentinel_user
        self.unclaimed_campaign = Campaign.objects.create(
            owner=get_sentinel_user(),
            name="Lost Kingdom",
        )
        self.unclaimed_campaign.players.add(self.wendy, self.susan)

    @CampaignMixin.as_user("wendy")
    def test_player_can_claim_unclaimed_campaign(self, client):
        response = client.post(
            "/campaigns/deleted-user/lost-kingdom",
            {"claim": "true"},
        )
        self.unclaimed_campaign.refresh_from_db()
        assert response.status_code == HTTPStatus.FOUND
        assert response.url == "/campaigns/wendy/lost-kingdom"
        assert self.unclaimed_campaign.owner == self.wendy

    @CampaignMixin.as_user("wendy")
    def test_player_sees_claim_button_on_unclaimed_campaign(self, client):
        response = client.get("/campaigns/deleted-user/lost-kingdom")
        content = response.content.decode()
        assert response.status_code == HTTPStatus.OK
        assert "claim" in content.lower()

    @CampaignMixin.as_user("mary")
    def test_non_player_cannot_claim_unclaimed_campaign(self, client):
        response = client.post(
            "/campaigns/deleted-user/lost-kingdom",
            {"claim": "true"},
        )
        assert response.status_code == HTTPStatus.FORBIDDEN

    def test_anonymous_cannot_claim_unclaimed_campaign(self, client):
        response = client.post(
            "/campaigns/deleted-user/lost-kingdom",
            {"claim": "true"},
        )
        assert response.status_code == HTTPStatus.UNAUTHORIZED

    @CampaignMixin.as_user("wendy")
    def test_cannot_claim_non_unclaimed_campaign(self, client):
        client.post(
            "/campaigns/susan/river-crossing",
            {"claim": "true"},
        )
        self.joined_campaign.refresh_from_db()
        assert self.joined_campaign.owner == self.susan


@pytest.mark.django_db
class TestCampaignListView(CampaignMixin):
    def test_anonymous_redirected_to_login(self, client):
        response = client.get("/campaigns/")
        assert response.status_code == HTTPStatus.FOUND
        assert response.url == "/login?next=/campaigns/"

    @CampaignMixin.as_user("wendy")
    def test_shows_accessible_campaigns_with_owner_and_players(self, client):
        response = client.get("/campaigns/")
        content = response.content.decode()
        assert response.status_code == HTTPStatus.OK
        assert "The Old Forest" in content
        assert "River Crossing" in content
        assert "The Eastern Road" not in content
        assert 'href="/campaigns/create"' in content
        assert ">wendy<" in content
        assert ">susan<" in content


@pytest.mark.django_db
class TestCampaignUserRedirect(UserMixin):
    def test_redirects_to_campaign_list(self, client):
        response = client.get("/campaigns/wendy/")
        assert response.status_code == HTTPStatus.FOUND
        assert response.url == "/campaigns/"
