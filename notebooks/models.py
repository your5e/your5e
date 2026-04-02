from django.db import models
from django.urls import reverse
from slugify import slugify

from users.models import User
from wikis.models import Wiki


class OwnedSlugMixin:
    """
    Mixin for models with name and slug fields.
    Generates unique slugs scoped to a configurable field.
    Override slug_scope_field to change the scoping (default: 'owner').
    Override get_base_slug() to change how the base slug is determined.
    """

    slug_scope_field = "owner"

    def get_base_slug(self):
        return slugify(self.name)

    def generate_unique_slug(self):
        base_slug = self.get_base_slug()
        slug = base_slug
        counter = 2
        scope_filter = {self.slug_scope_field: getattr(self, self.slug_scope_field)}
        while (
            self.__class__.objects.filter(slug=slug, **scope_filter)
            .exclude(pk=self.pk)
            .exists()
        ):
            slug = f"{base_slug}-{counter}"
            counter += 1
        return slug


class Notebook(OwnedSlugMixin, Wiki):
    class Visibility(models.TextChoices):
        PRIVATE = "private"
        INTERNAL = "internal"
        PUBLIC = "public"

    name = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255)
    owner = models.ForeignKey(User, on_delete=models.CASCADE)
    visibility = models.CharField(
        max_length=10,
        choices=Visibility.choices,
        default=Visibility.PRIVATE,
    )
    copied_from = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["owner", "slug"],
                name="unique_slug_per_owner",
            ),
        ]

    def __str__(self):
        return f"{self.name} ({self.owner.username})"

    def get_absolute_url(self):
        return reverse("notebook", kwargs={
            "username": self.owner.username,
            "slug": self.slug,
        })

    def get_folder_url(self, path):
        if "/" in path:
            folder = path.rsplit("/", 1)[0]
            return reverse("notebook_directory", kwargs={
                "username": self.owner.username,
                "slug": self.slug,
                "path": folder,
            })
        return self.get_absolute_url()

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = self.generate_unique_slug()
        super().save(*args, **kwargs)

    def rename(self, name):
        self.name = name
        self.slug = self.generate_unique_slug()
        self.save()

    def has_content(self):
        return self.page_set.filter(deleted_at__isnull=True).exists()

    @property
    def is_campaign_wiki(self):
        return self.campaign_notebooks.filter(is_wiki=True).exists()

    def delete(self, *args, **kwargs):
        if self.is_campaign_wiki:
            raise ValueError("Cannot delete a campaign wiki notebook")
        super().delete(*args, **kwargs)


class NotebookPermission(models.Model):
    class Role(models.TextChoices):
        EDITOR = "editor"
        VIEWER = "viewer"

    notebook = models.ForeignKey(Notebook, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    role = models.CharField(max_length=10, choices=Role.choices)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["notebook", "user"],
                name="unique_notebook_user",
            ),
        ]

    def __str__(self):
        return (
            f"{self.notebook.name} ({self.notebook.owner.username})"
            f" grants {self.user.username} {self.role} permission"
        )
