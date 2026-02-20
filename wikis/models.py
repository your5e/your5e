import hashlib

from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone
from slugify import slugify

from users.models import User, get_sentinel_user

FORBIDDEN_FILENAME_CHARS = r'[]#^|\\:*"<>?'


class Wiki(models.Model):
    def __str__(self):
        return f"Wiki {self.pk}"


class Page(models.Model):
    wiki = models.ForeignKey(Wiki, on_delete=models.CASCADE)
    deleted_at = models.DateTimeField(null=True, blank=True)

    @property
    def latest_version(self):
        return self.version_set.order_by("-number").first()

    def update(self, *, filename, mime_type, data, created_by):
        content_hash = hashlib.sha256(data).hexdigest()
        content, _ = Content.objects.get_or_create(
            hash=content_hash,
            defaults={"data": data},
        )

        latest = self.latest_version
        if latest and latest.content_id == content_hash and latest.filename == filename:
            return latest

        number = (latest.number + 1) if latest else 1
        version = Version(
            page=self,
            filename=filename,
            mime_type=mime_type,
            number=number,
            content=content,
            created_by=created_by,
        )
        version.path = version.generate_path()
        version.full_clean()
        version.save()
        return version

    def soft_delete(self):
        self.deleted_at = timezone.now()
        self.save()

    def __str__(self):
        latest = self.latest_version
        if latest:
            return latest.filename
        return f"Page {self.pk}"


class Content(models.Model):
    hash = models.CharField(max_length=64, primary_key=True)
    data = models.BinaryField()

    def __str__(self):
        return self.hash[:12]


class Version(models.Model):
    page = models.ForeignKey(Page, on_delete=models.CASCADE)
    filename = models.CharField(max_length=255)
    path = models.CharField(max_length=255)
    mime_type = models.CharField(max_length=100)
    number = models.PositiveIntegerField()
    content = models.ForeignKey(Content, on_delete=models.PROTECT)
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET(get_sentinel_user),
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.filename} (v{self.number})"

    def clean(self):
        self.validate_filename()
        self.validate_path_unique()

    def validate_filename(self):
        if self.filename.endswith("/"):
            raise ValidationError("Filename cannot end with /")
        if "../" in self.filename:
            raise ValidationError("Filename cannot contain ../")
        for char in FORBIDDEN_FILENAME_CHARS:
            if char in self.filename:
                raise ValidationError(f"Filename cannot contain {char}")

    def generate_path(self):
        parts = self.filename.split("/")
        result = []
        for part in parts:
            if "." in part:
                name, ext = part.rsplit(".", 1)
                result.append(f"{slugify(name)}.{ext.lower()}")
            else:
                result.append(slugify(part))
        return "/".join(result)

    def validate_path_unique(self):
        latest_version_numbers = Version.objects.filter(
            page__wiki=self.page.wiki
        ).exclude(
            page=self.page
        ).values("page").annotate(
            max_number=models.Max("number")
        )
        conflicting = Version.objects.filter(
            page__wiki=self.page.wiki,
            path=self.path,
        ).exclude(
            page=self.page
        ).filter(
            number__in=models.Subquery(
                latest_version_numbers.filter(
                    page=models.OuterRef("page")
                ).values("max_number")
            )
        ).exists()
        if conflicting:
            raise ValidationError(
                f"Path {self.path} already exists in this wiki"
            )
