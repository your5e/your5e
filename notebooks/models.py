from django.db import models
from slugify import slugify

from users.models import User
from wikis.models import Wiki


class Notebook(Wiki):
    class Visibility(models.TextChoices):
        PRIVATE = "private"
        SITE = "site"
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

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = self.generate_unique_slug()
        super().save(*args, **kwargs)

    def rename(self, name):
        self.name = name
        self.slug = self.generate_unique_slug()
        self.save()

    def generate_unique_slug(self):
        base_slug = slugify(self.name)
        slug = base_slug
        counter = 2
        while (
            Notebook.objects.filter(slug=slug, owner=self.owner)
                .exclude(pk=self.pk)
                .exists()
        ):
            slug = f"{base_slug}-{counter}"
            counter += 1
        return slug


class NotebookPermission(models.Model):
    class Role(models.TextChoices):
        EDITOR = "editor"
        VIEWER = "viewer"

    notebook = models.ForeignKey(Notebook, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    role = models.CharField(max_length=10, choices=Role.choices)

    def __str__(self):
        return (
            f"{self.notebook.name} ({self.notebook.owner.username})"
            f" grants {self.user.username} {self.role} permission"
        )
