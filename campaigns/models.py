import secrets

import bleach
import markdown
from django.db import models
from django.db.models.signals import m2m_changed, post_delete
from django.dispatch import receiver
from django.utils.text import slugify

from notebooks.models import Notebook, NotebookPermission, OwnedSlugMixin
from users.models import User, get_sentinel_user


class CampaignNotebook(OwnedSlugMixin, models.Model):
    slug_scope_field = "campaign"

    campaign = models.ForeignKey(
        "Campaign",
        on_delete=models.CASCADE,
        related_name="campaign_notebooks",
    )
    notebook = models.ForeignKey(
        Notebook,
        on_delete=models.CASCADE,
        related_name="campaign_notebooks",
    )
    linked_by = models.ForeignKey(
        User,
        on_delete=models.SET(get_sentinel_user),
        related_name="linked_notebooks",
    )
    slug = models.SlugField(max_length=255, blank=True)
    order = models.PositiveIntegerField(default=0)
    is_wiki = models.BooleanField(default=False)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["campaign", "notebook"],
                name="unique_notebook_per_campaign",
            ),
            models.UniqueConstraint(
                fields=["campaign", "slug"],
                name="unique_slug_per_campaign",
            ),
        ]
        ordering = ["order"]

    @property
    def name(self):
        return self.notebook.name

    def get_base_slug(self):
        return self.notebook.slug

    def __str__(self):
        return f"{self.notebook.name} in {self.campaign.name}"

    def save(self, *args, **kwargs):
        if self.pk is None and not self.is_wiki:
            max_order = CampaignNotebook.objects.filter(
                campaign=self.campaign
            ).aggregate(models.Max("order"))["order__max"]
            if max_order is None:
                self.order = 1
            else:
                self.order = max_order + 1
            self.slug = self.generate_unique_slug()
        super().save(*args, **kwargs)


class Campaign(OwnedSlugMixin, models.Model):
    owner = models.ForeignKey(
        User,
        on_delete=models.SET(get_sentinel_user),
        related_name="owned_campaigns",
    )
    name = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255)
    description = models.TextField(blank=True, default="")
    join_slug = models.CharField(max_length=32, unique=True)
    players = models.ManyToManyField(User, related_name="campaigns")

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["owner", "name"],
                name="unique_name_per_owner",
            ),
            models.UniqueConstraint(
                fields=["owner", "slug"],
                name="unique_campaign_slug_per_owner",
            ),
        ]

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        from django.urls import reverse
        return reverse("campaign", kwargs={
            "username": self.owner.username,
            "slug": self.slug,
        })

    def get_players(self):
        return [
            m.user
            for m in Campaign.players.through.objects.filter(campaign=self)
            .select_related("user")
            .order_by("id")
        ]

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = self.generate_unique_slug()
        if not self.join_slug:
            self.join_slug = self.generate_join_slug()
        is_new = self.pk is None
        super().save(*args, **kwargs)
        if is_new:
            wiki = Notebook.objects.create(
                name=f"{self.name} wiki",
                owner=self.owner,
                visibility=Notebook.Visibility.PRIVATE,
            )
            CampaignNotebook.objects.create(
                campaign=self,
                notebook=wiki,
                linked_by=self.owner,
                order=0,
                is_wiki=True,
            )
            self.players.add(self.owner)
        else:
            wiki_link = self.campaign_notebooks.filter(is_wiki=True).first()
            if wiki_link and wiki_link.notebook.owner != self.owner:
                wiki_link.notebook.owner = self.owner
                wiki_link.notebook.save()

    def generate_join_slug(self):
        while True:
            join_slug = secrets.token_urlsafe(16)
            if not Campaign.objects.filter(join_slug=join_slug).exists():
                return join_slug

    def has_content(self):
        if self.players.exclude(pk=self.owner_id).exists():
            return True
        return self.campaign_notebooks.filter(
            notebook__page__isnull=False,
            notebook__page__deleted_at__isnull=True,
        ).exists()

    def description_html(self):
        if not self.description:
            return ""
        clean = bleach.clean(self.description, tags=[], strip=True)
        return markdown.markdown(clean)

    def visible_notebook_links(self, user, include_wiki=False):
        from django.db.models import Q

        from notebooks.models import Notebook

        links = self.campaign_notebooks.select_related(
            "notebook", "notebook__owner"
        ).prefetch_related("notebook__notebookpermission_set__user")
        if not include_wiki:
            links = links.filter(is_wiki=False)
        return list(links.filter(
            Q(notebook__visibility=Notebook.Visibility.PUBLIC) |
            Q(notebook__visibility=Notebook.Visibility.INTERNAL) |
            Q(notebook__owner=user) |
            Q(notebook__notebookpermission__user=user)
        ).distinct())

    def resolve_wikilink(self, target):
        target = target.removesuffix(".md").removesuffix(".MD")
        target_slug = slugify(target.replace("'", ""))

        candidates = []
        for link in self.campaign_notebooks.all():
            notebook = link.notebook
            for version in notebook.latest_versions():
                path_basename = version.path.rsplit("/", 1)[-1]
                if path_basename == target_slug or version.path == target_slug:
                    if link.is_wiki:
                        full_path = version.path
                    else:
                        full_path = f"{link.slug}/{version.path}"
                    depth = version.path.count("/")
                    candidates.append((depth, link.order, full_path))

        if candidates:
            candidates.sort()
            return candidates[0][2]
        return target_slug


@receiver(post_delete, sender=User)
def delete_orphaned_campaigns(sender, instance, **kwargs):
    sentinel = get_sentinel_user()
    Campaign.objects.filter(owner=sentinel).annotate(
        player_count=models.Count("players")
    ).filter(player_count=0).delete()


@receiver(m2m_changed, sender=Campaign.players.through)
def update_wiki_permissions(sender, instance, action, pk_set, **kwargs):
    if action not in ("post_add", "post_remove"):
        return
    wiki_link = instance.campaign_notebooks.filter(is_wiki=True).first()
    if not wiki_link:
        return
    wiki = wiki_link.notebook
    if action == "post_add":
        for user_pk in pk_set:
            if user_pk == wiki.owner_id:
                continue
            NotebookPermission.objects.get_or_create(
                notebook=wiki,
                user_id=user_pk,
                defaults={"role": NotebookPermission.Role.EDITOR},
            )
    elif action == "post_remove":
        NotebookPermission.objects.filter(
            notebook=wiki,
            user_id__in=pk_set,
        ).delete()
