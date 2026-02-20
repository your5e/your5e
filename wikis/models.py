import hashlib

from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone
from slugify import slugify

from users.models import User, get_sentinel_user

FORBIDDEN_FILENAME_CHARS = r'[]#^|\\:*"<>?'


class Wiki(models.Model):
    def __str__(self):
        if hasattr(self, "notebook"):
            return str(self.notebook)
        return f"Wiki {self.pk}"

    def latest_versions(self):
        return Version.objects.filter(
            page__wiki=self,
            page__deleted_at__isnull=True,
        ).annotate(
            max_number=models.Max("page__version__number")
        ).filter(
            number=models.F("max_number")
        )

    def get_page(self, *, filename=None, path=None):
        if filename and path:
            raise ValueError("Cannot specify both filename and path")
        if not filename and not path:
            raise ValueError("Must specify filename or path")
        lookup = {"filename": filename} if filename else {"path": path}
        version = self.latest_versions().filter(**lookup).first()
        if not version:
            raise Page.DoesNotExist()
        return version.page

    def all_pages(self):
        return [
            page.latest_version
                for page in self.page_set.filter(deleted_at__isnull=True)
        ]

    def deleted_pages(self):
        return [
            page.latest_version
                for page in self.page_set.filter(deleted_at__isnull=False)
        ]

    def changes_since(self, timestamp):
        return list(
            self.page_set.filter(
                models.Q(version__created_at__gte=timestamp)
                | models.Q(deleted_at__gte=timestamp)
            ).distinct()
        )

    def names_in_directory(self, directory):
        prefix = directory[1:]
        versions = self.latest_versions()
        if prefix:
            versions = versions.filter(path__startswith=prefix)
        results = []
        for version in versions:
            depth = prefix.count("/")
            parts = version.filename.split("/")
            results.append("/".join(parts[depth:]))
        return results

    def files_in(self, directory):
        files = []
        for name in self.names_in_directory(directory):
            if "/" not in name:
                files.append(name)
        return sorted(files)

    def folders_in(self, directory):
        folders = set()
        for name in self.names_in_directory(directory):
            if "/" in name:
                folders.add(name.split("/", 1)[0])
        return sorted(folders)

    def purge_deleted(self, cutoff):
        for page in self.page_set.filter(deleted_at__lt=cutoff):
            page.delete()


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
        if (
            latest
            and latest.content.hash == content_hash
            and latest.filename == filename
        ):
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

    def history(self):
        return list(self.version_set.order_by("number"))

    def revert(self, *, version_number, reverted_by):
        try:
            version = self.version_set.get(number=version_number)
        except Version.DoesNotExist as err:
            raise ValueError(f"Version {version_number} does not exist") from err
        return self.update(
            filename=version.filename,
            mime_type=version.mime_type,
            data=version.content.data,
            created_by=reverted_by,
        )

    def delete_version(self, version_number):
        try:
            version = self.version_set.get(number=version_number)
        except Version.DoesNotExist as err:
            raise ValueError(f"Version {version_number} does not exist") from err
        content_hash = version.content_id
        version.delete()
        Content.purge_orphaned([content_hash])
        if not self.version_set.exists():
            self.delete()

    def delete(self, *args, **kwargs):
        content_hashes = set(
            self.version_set.values_list("content_id", flat=True)
        )
        super().delete(*args, **kwargs)
        Content.purge_orphaned(content_hashes)

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

    def delete(self, *args, **kwargs):
        raise RuntimeError("Content cannot be deleted directly; use purge")

    @classmethod
    def purge_orphaned(cls, content_hashes):
        for content_hash in content_hashes:
            if not Version.objects.filter(content_id=content_hash).exists():
                cls.objects.filter(hash=content_hash).delete()


class Version(models.Model):
    class Meta:
        ordering = ["-number"]

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
