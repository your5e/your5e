from django.contrib.auth.models import (
    AbstractBaseUser,
    BaseUserManager,
    PermissionsMixin,
)
from django.db import models
from django.utils import timezone


def get_sentinel_user():
    user, _ = User.objects.get_or_create(
        username="(deleted)",
        defaults={
            "email": "deleted@localhost",
            "is_active": False,
        },
    )
    return user


class UserManager(BaseUserManager):
    def create_user(self, username, email, password=None, **extra_fields):
        if not username:
            raise ValueError("Username is required")
        if not email:
            raise ValueError("Email is required")

        email = self.normalize_email(email)
        user = self.model(username=username, email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, username, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        return self.create_user(username, email, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    username = models.CharField(max_length=150, unique=True)
    email = models.EmailField(unique=True)
    name = models.CharField(max_length=255, blank=True, default="")
    short_name = models.CharField(max_length=50, blank=True, default="")
    description = models.TextField(blank=True, default="")
    is_public = models.BooleanField(default=False)

    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    date_joined = models.DateTimeField(default=timezone.now)

    objects = UserManager()

    USERNAME_FIELD = "username"
    REQUIRED_FIELDS = ["email"]

    def __str__(self):
        if self.short_name:
            return self.short_name
        if self.name:
            return self.name
        return self.username


class ProfileLink(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="profile_links",
    )
    url = models.URLField()
    label = models.CharField(max_length=100)

    def __str__(self):
        return f"{self.user} {self.label} link"
