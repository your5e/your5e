from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from wikis.models import Wiki


class Command(BaseCommand):
    help = "Purge soft-deleted wiki pages older than the specified number of days"

    def add_arguments(self, parser):
        parser.add_argument(
            "--days",
            type=int,
            default=30,
            help="Delete pages soft-deleted more than this many days ago",
        )

    def handle(self, *args, **options):
        cutoff = timezone.now() - timedelta(days=options["days"])
        for wiki in Wiki.objects.all():
            wiki.purge_deleted(cutoff)
