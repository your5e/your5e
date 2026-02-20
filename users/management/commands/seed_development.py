from django.core.management.base import BaseCommand

from users.models import User


class Command(BaseCommand):
    help = "Create default users for development"

    def handle(self, *args, **options):
        User.objects.create_user(
            username="admin",
            email="admin@localhost",
            password="admin",
            is_staff=True,
            is_superuser=True,
        )
        norm = User.objects.create_user(
            username="norm",
            email="norm@localhost",
            password="norm",
            name="Mark Norman Francis",
            short_name="Norm",
        )
