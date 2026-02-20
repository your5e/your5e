from django.core.management.base import BaseCommand

from users.models import ProfileLink, User


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
            description="Developer and tabletop enthusiast.",
            is_public=True,
        )
        ProfileLink.objects.create(
            user=norm,
            url="https://marknormanfrancis.com",
            label="Website",
        )
        wendy = User.objects.create_user(
            username="wendy",
            email="wendy@localhost",
            password="wendy",
            name="Wendy Testaburger",
            short_name="Wendy",
        )
