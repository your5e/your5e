import re
import subprocess
import tomllib
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from notebooks.mime import guess_mime_type
from notebooks.models import Notebook
from users.models import get_public_owner
from wikis.models import Page

CONFIG_PATH = Path(__file__).parent / "import_config.toml"


def add_source(content: str, source: str) -> str:
    match = re.search(r"^# (?!#).+", content, re.MULTILINE)
    if not match:
        return content

    before = content[: match.end()]
    after = content[match.end() :]

    stripped_after = after.lstrip("\n")
    original_newlines = len(after) - len(stripped_after)
    newlines_after_source = "\n" * max(2, original_newlines)

    if source.startswith("["):
        formatted_source = source
    else:
        formatted_source = f"_{source}_"

    return f"{before}\n\n**Source:** {formatted_source}{newlines_after_source}{stripped_after}"


class Command(BaseCommand):
    help = "Import files from a folder into a system notebook"

    def add_arguments(self, parser):
        parser.add_argument(
            "section",
            nargs="?",
            help="Config section to use for import",
        )
        parser.add_argument(
            "folder",
            nargs="?",
            help="Path to the source folder (optional if repo in config)",
        )
        parser.add_argument(
            "--all",
            action="store_true",
            dest="import_all",
            help="Import all sections from config",
        )
        parser.add_argument(
            "--config",
            default=CONFIG_PATH,
            type=Path,
            help="Path to import config TOML file",
        )

    def handle(self, *args, **options):
        section = options["section"]
        folder_arg = options["folder"]
        config_path = options["config"]
        import_all = options["import_all"]

        full_config = {}
        if config_path.exists():
            full_config = tomllib.loads(config_path.read_text())

        if import_all:
            for section_name in full_config:
                self.import_section(section_name, full_config, None)
            return

        if not section:
            raise CommandError("section is required (or use --all)")

        self.import_section(section, full_config, folder_arg)

    def import_section(self, section, full_config, folder_arg):
        if section not in full_config:
            raise CommandError(f"'{section}' not found in config")

        config = full_config[section]
        if "name" not in config:
            raise CommandError(f"'name' is required for [{section}]")
        name = config["name"]
        slug = config.get("slug", section)
        source = config.get(
            "source",
            f"[{name}](/notebooks/your5e/{slug})",
        )

        owner = get_public_owner()
        notebook, _ = Notebook.objects.get_or_create(
            slug=slug,
            owner=owner,
            defaults={
                "name": name,
                "visibility": Notebook.Visibility.PUBLIC,
            },
        )

        if "sources" in config:
            sources = config["sources"]
        else:
            sources = [{"prefix": ""}]

        total_file_count = 0
        for source_config in sources:
            merged_config = {**config, **source_config}
            prefix = source_config.get("prefix", "")

            folder = self.get_source_folder(merged_config, folder_arg, section)

            for file_path in folder.rglob("*"):
                if file_path.is_dir():
                    continue
                relative = file_path.relative_to(folder)
                if any(part.startswith(".") for part in relative.parts):
                    continue

                total_file_count += 1
                relative_path = file_path.relative_to(folder)
                if prefix:
                    filename = str(Path(prefix) / relative_path)
                else:
                    filename = str(relative_path)
                mime_type = guess_mime_type(filename)
                data = file_path.read_bytes()

                if mime_type == "text/markdown":
                    content = data.decode()
                    content = add_source(content, source)
                    data = content.encode()

                try:
                    page = notebook.get_page(filename=filename)
                except Page.DoesNotExist:
                    page = Page.objects.create(wiki=notebook)

                previous_version = page.latest_version
                previous_number = 0
                if previous_version:
                    previous_number = previous_version.number

                version = page.update(
                    filename=filename,
                    mime_type=mime_type,
                    data=data,
                    created_by=owner,
                )

                if version.number > previous_number:
                    self.stdout.write(f"++ {filename}")

        if total_file_count == 0:
            raise CommandError(f"No files found in '{folder}'")

    def get_source_folder(self, config, folder_arg, section):
        if "repo" in config:
            repo_url = config["repo"]
            path = config.get("path", "")

            repo_name = repo_url.rstrip("/").split("/")[-1].removesuffix(".git")
            repo_dir = Path("/tmp") / repo_name

            if repo_dir.exists():
                subprocess.run(
                    ["git", "pull"],
                    cwd=repo_dir,
                    check=True,
                    capture_output=True,
                )
            else:
                subprocess.run(
                    ["git", "clone", repo_url],
                    cwd=Path("/tmp"),
                    check=True,
                    capture_output=True,
                )

            return repo_dir / path

        folder = None
        if "folder" in config:
            folder = Path(config["folder"])
        elif folder_arg:
            folder = Path(folder_arg)

        if folder:
            if not folder.is_dir():
                raise CommandError(f"Folder '{folder}' does not exist")
            return folder

        raise CommandError(
            f"Either 'folder' argument or 'repo' in config required for [{section}]"
        )
