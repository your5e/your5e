import shutil
import subprocess
from io import StringIO
from pathlib import Path
from textwrap import dedent

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError

from notebooks.management.commands.import_notebook import add_source
from notebooks.models import Notebook
from users.models import get_public_owner
from wikis.models import Page


@pytest.mark.django_db
class TestImportNotebook:
    @pytest.fixture
    def source_dir(self, tmp_path):
        path = tmp_path / "source"
        path.mkdir()
        return path

    @pytest.fixture
    def system_notebook(self):
        owner = get_public_owner()
        return Notebook.objects.create(
            name="SRD",
            slug="srd",
            owner=owner,
            visibility=Notebook.Visibility.PUBLIC,
        )

    @pytest.fixture
    def config_dir(self, tmp_path):
        path = tmp_path / "config"
        path.mkdir()
        return path

    @pytest.fixture
    def config_with_name(self, config_dir):
        config_path = config_dir / "import_config.toml"
        config_path.write_text(dedent("""
            [srd]
            name = "5e SRD"
        """).lstrip())
        return config_path

    @pytest.fixture
    def config_with_slug_override(self, config_dir):
        config_path = config_dir / "import_config.toml"
        config_path.write_text(dedent("""
            [srd]
            name = "5e SRD"
            slug = "five-e-srd"
        """).lstrip())
        return config_path

    @pytest.fixture
    def config_with_source_override(self, config_dir):
        config_path = config_dir / "import_config.toml"
        config_path.write_text(dedent("""
            [srd]
            name = "5e SRD"
            source = "[Custom Source](/custom)"
        """).lstrip())
        return config_path

    def create_git_repo(self, repo_dir):
        repo_dir.mkdir()
        subprocess.run(["git", "init"], cwd=repo_dir, check=True, capture_output=True)
        subprocess.run(
            ["git", "config", "user.email", "test@test.com"],
            cwd=repo_dir,
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "config", "user.name", "Test"],
            cwd=repo_dir,
            check=True,
            capture_output=True,
        )

        repo_name = repo_dir.name
        cloned_dir = Path("/tmp") / repo_name
        if cloned_dir.exists():
            shutil.rmtree(cloned_dir)

        return repo_dir

    @pytest.fixture
    def multiple_source_dirs(self, tmp_path):
        main_dir = tmp_path / "main"
        main_dir.mkdir()
        (main_dir / "overview.md").write_text("# Overview\n\nMain content.")

        backgrounds_dir = tmp_path / "backgrounds"
        backgrounds_dir.mkdir()
        (backgrounds_dir / "acolyte.md").write_text("# Acolyte\n\nBackground.")

        feats_dir = tmp_path / "feats"
        feats_dir.mkdir()
        (feats_dir / "alert.md").write_text("# Alert\n\nFeat.")

        return {
            "main": main_dir,
            "backgrounds": backgrounds_dir,
            "feats": feats_dir,
        }

    def test_raises_error_when_folder_does_not_exist(self, config_with_name):
        with pytest.raises(CommandError, match="does not exist"):
            call_command(
                "import_notebook",
                "srd",
                "/nonexistent/path",
                config=config_with_name,
            )

    def test_raises_error_when_folder_is_empty(
        self,
        source_dir,
        system_notebook,
        config_with_name,
    ):
        with pytest.raises(CommandError, match="No files found"):
            call_command(
                "import_notebook",
                "srd",
                str(source_dir),
                config=config_with_name,
            )

    def test_raises_error_when_section_not_in_config(
        self,
        source_dir,
        config_with_name,
    ):
        (source_dir / "test.md").write_text("# Test")
        with pytest.raises(CommandError, match="'nonexistent' not found in config"):
            call_command(
                "import_notebook",
                "nonexistent",
                str(source_dir),
                config=config_with_name,
            )

    def test_raises_error_when_name_missing(self, source_dir, config_dir):
        (source_dir / "test.md").write_text("# Test")
        config_path = config_dir / "import_config.toml"
        config_path.write_text("[srd]\n")

        with pytest.raises(CommandError, match="'name' is required"):
            call_command(
                "import_notebook",
                "srd",
                str(source_dir),
                config=config_path,
            )

    def test_creates_notebook_if_not_exists(self, source_dir, config_with_name):
        (source_dir / "spells.md").write_text("# Spells")

        call_command(
            "import_notebook",
            "srd",
            str(source_dir),
            config=config_with_name,
        )

        owner = get_public_owner()
        notebook = Notebook.objects.get(slug="srd", owner=owner)
        assert notebook.name == "5e SRD"
        assert notebook.visibility == Notebook.Visibility.PUBLIC
        assert notebook.get_page(path="spells") is not None

    def test_creates_notebook_with_slug_override(
        self,
        source_dir,
        config_with_slug_override,
    ):
        (source_dir / "spells.md").write_text("# Spells")

        call_command(
            "import_notebook",
            "srd",
            str(source_dir),
            config=config_with_slug_override,
        )

        owner = get_public_owner()
        notebook = Notebook.objects.get(slug="five-e-srd", owner=owner)
        assert notebook.name == "5e SRD"

    def test_imports_single_markdown_file(
        self,
        source_dir,
        system_notebook,
        config_with_name,
    ):
        (source_dir / "spells.md").write_text("# Spells\n\nA list of spells.")

        call_command(
            "import_notebook",
            "srd",
            str(source_dir),
            config=config_with_name,
        )

        page = system_notebook.get_page(path="spells")
        assert page.latest_version.filename == "spells.md"
        assert page.latest_version.mime_type == "text/markdown"
        assert b"A list of spells" in page.latest_version.content.data

    def test_imports_nested_directory_structure(
        self,
        source_dir,
        system_notebook,
        config_with_name,
    ):
        spells_dir = source_dir / "Spells"
        spells_dir.mkdir()
        (spells_dir / "Fireball.md").write_text("# Fireball\n\nA ball of fire.")
        (spells_dir / "Magic Missile.md").write_text("# Magic Missile\n\nDarts.")

        call_command(
            "import_notebook",
            "srd",
            str(source_dir),
            config=config_with_name,
        )

        fireball = system_notebook.get_page(path="spells/fireball")
        assert fireball.latest_version.filename == "Spells/Fireball.md"
        assert b"ball of fire" in fireball.latest_version.content.data

        missile = system_notebook.get_page(path="spells/magic-missile")
        assert missile.latest_version.filename == "Spells/Magic Missile.md"
        assert b"Darts" in missile.latest_version.content.data

    def test_imports_non_markdown_files(
        self,
        source_dir,
        system_notebook,
        config_with_name,
    ):
        images_dir = source_dir / "images"
        images_dir.mkdir()
        png_bytes = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01"
        (images_dir / "logo.png").write_bytes(png_bytes)

        call_command(
            "import_notebook",
            "srd",
            str(source_dir),
            config=config_with_name,
        )

        logo = system_notebook.get_page(path="images/logo.png")
        assert logo.latest_version.filename == "images/logo.png"
        assert logo.latest_version.mime_type == "image/png"
        assert logo.latest_version.content.data == png_bytes

    def test_updates_existing_pages(
        self,
        source_dir,
        system_notebook,
        config_with_name,
    ):
        owner = get_public_owner()
        page = Page.objects.create(wiki=system_notebook)
        page.update(
            filename="spells.md",
            mime_type="text/markdown",
            data=b"# Spells\n\nVersion 1.",
            created_by=owner,
        )

        (source_dir / "spells.md").write_text("# Spells\n\nVersion 2.")

        call_command(
            "import_notebook",
            "srd",
            str(source_dir),
            config=config_with_name,
        )

        page.refresh_from_db()
        assert page.latest_version.number == 2
        assert b"Version 2" in page.latest_version.content.data

    def test_skips_version_when_content_unchanged(
        self,
        source_dir,
        system_notebook,
        config_with_name,
    ):
        (source_dir / "spells.md").write_text("# Spells\n\nSame content.")

        call_command(
            "import_notebook",
            "srd",
            str(source_dir),
            config=config_with_name,
        )
        call_command(
            "import_notebook",
            "srd",
            str(source_dir),
            config=config_with_name,
        )

        page = system_notebook.get_page(path="spells")
        assert page.latest_version.number == 1

    def test_status_output(self, source_dir, system_notebook, config_with_name):
        owner = get_public_owner()
        page = Page.objects.create(wiki=system_notebook)
        page.update(
            filename="spells.md",
            mime_type="text/markdown",
            data=b"# Spells\n\n**Source:** [5e SRD](/notebooks/your5e/srd)\n\n",
            created_by=owner,
        )

        (source_dir / "spells.md").write_text("# Spells")
        (source_dir / "items.md").write_text("# Items")

        stdout = StringIO()
        call_command(
            "import_notebook",
            "srd",
            str(source_dir),
            stdout=stdout,
            config=config_with_name,
        )

        output = stdout.getvalue()
        assert "++ items.md" in output
        assert "spells.md" not in output

    def test_applies_computed_source_to_markdown(
        self,
        source_dir,
        system_notebook,
        config_with_name,
    ):
        (source_dir / "dragon.md").write_text(dedent("""
            # Adult Brass Dragon

            _Huge Dragon (Metallic), Chaotic Good_
        """).lstrip())

        call_command(
            "import_notebook",
            "srd",
            str(source_dir),
            config=config_with_name,
        )

        page = system_notebook.get_page(path="dragon")
        content = page.latest_version.content.data.decode()
        assert content == dedent("""
            # Adult Brass Dragon

            **Source:** [5e SRD](/notebooks/your5e/srd)

            _Huge Dragon (Metallic), Chaotic Good_
        """).lstrip()

    def test_applies_source_override_to_markdown(
        self,
        source_dir,
        system_notebook,
        config_with_source_override,
    ):
        (source_dir / "dragon.md").write_text(dedent("""
            # Adult Brass Dragon

            _Huge Dragon (Metallic), Chaotic Good_
        """).lstrip())

        call_command(
            "import_notebook",
            "srd",
            str(source_dir),
            config=config_with_source_override,
        )

        page = system_notebook.get_page(path="dragon")
        content = page.latest_version.content.data.decode()
        assert content == dedent("""
            # Adult Brass Dragon

            **Source:** [Custom Source](/custom)

            _Huge Dragon (Metallic), Chaotic Good_
        """).lstrip()

    def test_does_not_filter_non_markdown_files(
        self,
        source_dir,
        system_notebook,
        config_with_name,
    ):
        png_bytes = b"\x89PNG\r\n\x1a\n"
        (source_dir / "image.png").write_bytes(png_bytes)

        call_command(
            "import_notebook",
            "srd",
            str(source_dir),
            config=config_with_name,
        )

        page = system_notebook.get_page(path="image.png")
        assert page.latest_version.content.data == png_bytes

    def test_raises_error_when_no_folder_or_repo(self, config_with_name):
        with pytest.raises(CommandError, match="'folder'.*or 'repo'"):
            call_command(
                "import_notebook",
                "srd",
                config=config_with_name,
            )

    def git_commit(self, repo_dir, message):
        subprocess.run(
            ["git", "add", "."],
            cwd=repo_dir,
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "commit", "-m", message],
            cwd=repo_dir,
            check=True,
            capture_output=True,
        )

    def test_imports_from_git_repo(self, tmp_path, config_dir):
        git_repo = self.create_git_repo(tmp_path / "git-repo-import")
        content_dir = git_repo / "content"
        content_dir.mkdir()
        (content_dir / "spells.md").write_text("# Spells\n\nFrom git.")
        self.git_commit(git_repo, "initial")

        config_path = config_dir / "import_config.toml"
        config_path.write_text(dedent(f"""
            [srd]
            name = "5e SRD"
            repo = "{git_repo}"
            path = "content"
        """).lstrip())

        call_command("import_notebook", "srd", config=config_path)

        owner = get_public_owner()
        notebook = Notebook.objects.get(slug="srd", owner=owner)
        page = notebook.get_page(path="spells")
        assert b"From git" in page.latest_version.content.data

    def test_pulls_updates_from_git_repo(self, tmp_path, config_dir):
        git_repo = self.create_git_repo(tmp_path / "git-repo-pull")
        (git_repo / "spells.md").write_text("# Spells\n\nVersion 1.")
        self.git_commit(git_repo, "initial")

        config_path = config_dir / "import_config.toml"
        config_path.write_text(dedent(f"""
            [srd]
            name = "5e SRD"
            repo = "{git_repo}"
        """).lstrip())

        call_command("import_notebook", "srd", config=config_path)

        (git_repo / "spells.md").write_text("# Spells\n\nVersion 2.")
        self.git_commit(git_repo, "update")

        call_command("import_notebook", "srd", config=config_path)

        owner = get_public_owner()
        notebook = Notebook.objects.get(slug="srd", owner=owner)
        page = notebook.get_page(path="spells")
        assert b"Version 2" in page.latest_version.content.data

    def test_imports_all_sections_with_all_flag(self, tmp_path, config_dir):
        monsters_dir = tmp_path / "monsters"
        monsters_dir.mkdir()
        (monsters_dir / "goblin.md").write_text("# Goblin\n\nSmall creature.")

        spells_dir = tmp_path / "spells"
        spells_dir.mkdir()
        (spells_dir / "fireball.md").write_text("# Fireball\n\nBall of fire.")

        config_path = config_dir / "import_config.toml"
        config_path.write_text(dedent(f"""
            [monsters]
            name = "SRD Monsters"
            folder = "{monsters_dir}"

            [spells]
            name = "SRD Spells"
            folder = "{spells_dir}"
        """).lstrip())

        call_command("import_notebook", all=True, config=config_path)

        owner = get_public_owner()
        monsters_notebook = Notebook.objects.get(slug="monsters", owner=owner)
        spells_notebook = Notebook.objects.get(slug="spells", owner=owner)

        assert monsters_notebook.get_page(path="goblin") is not None
        assert spells_notebook.get_page(path="fireball") is not None

    def test_imports_from_sources_array_with_empty_prefix(
        self,
        source_dir,
        system_notebook,
        config_dir,
    ):
        (source_dir / "test.md").write_text("# Test\n\nSingle source.")

        config_path = config_dir / "sources_config.toml"
        config_path.write_text(dedent(f"""
            [srd]
            name = "5e SRD"

            [[srd.sources]]
            path = ""
            prefix = ""
            folder = "{source_dir}"
        """).lstrip())

        call_command("import_notebook", "srd", config=config_path)

        page = system_notebook.get_page(path="test")
        assert page.latest_version.filename == "test.md"
        assert b"Single source" in page.latest_version.content.data

    def test_imports_from_multiple_sources_with_prefixes(
        self,
        config_dir,
        multiple_source_dirs,
    ):
        owner = get_public_owner()
        notebook = Notebook.objects.create(
            name="Character Creation",
            slug="character-creation",
            owner=owner,
            visibility=Notebook.Visibility.PUBLIC,
        )

        config_path = config_dir / "import_config.toml"
        config_path.write_text(dedent(f"""
            [character-creation]
            name = "Character Creation"

            [[character-creation.sources]]
            folder = "{multiple_source_dirs['main']}"
            prefix = ""

            [[character-creation.sources]]
            folder = "{multiple_source_dirs['backgrounds']}"
            prefix = "Backgrounds"

            [[character-creation.sources]]
            folder = "{multiple_source_dirs['feats']}"
            prefix = "Feats"
        """).lstrip())

        call_command("import_notebook", "character-creation", config=config_path)

        overview = notebook.get_page(path="overview")
        assert overview.latest_version.filename == "overview.md"
        assert b"Main content" in overview.latest_version.content.data

        acolyte = notebook.get_page(path="backgrounds/acolyte")
        assert acolyte.latest_version.filename == "Backgrounds/acolyte.md"
        assert b"Background" in acolyte.latest_version.content.data

        alert = notebook.get_page(path="feats/alert")
        assert alert.latest_version.filename == "Feats/alert.md"
        assert b"Feat" in alert.latest_version.content.data

    def test_sources_array_inherits_repo_from_top_level(self, tmp_path, config_dir):
        git_repo = self.create_git_repo(tmp_path / "sources-inherit-repo")
        (git_repo / "content.md").write_text("# Content\n\nFrom repo.")
        self.git_commit(git_repo, "initial")

        config_path = config_dir / "import_config.toml"
        config_path.write_text(dedent(f"""
            [test-repo]
            name = "Test Repo"
            repo = "{git_repo}"

            [[test-repo.sources]]
            path = ""
            prefix = ""
        """).lstrip())

        call_command("import_notebook", "test-repo", config=config_path)

        owner = get_public_owner()
        notebook = Notebook.objects.get(slug="test-repo", owner=owner)
        page = notebook.get_page(path="content")
        assert b"From repo" in page.latest_version.content.data

    def test_sources_array_can_override_repo(self, tmp_path, config_dir):
        repo1 = self.create_git_repo(tmp_path / "multi-repo-1")
        (repo1 / "file1.md").write_text("# File 1\n\nFrom repo 1.")
        self.git_commit(repo1, "initial")

        repo2 = self.create_git_repo(tmp_path / "multi-repo-2")
        (repo2 / "file2.md").write_text("# File 2\n\nFrom repo 2.")
        self.git_commit(repo2, "initial")

        config_path = config_dir / "import_config.toml"
        config_path.write_text(dedent(f"""
            [multi-repo]
            name = "Multi Repo"
            repo = "{repo1}"

            [[multi-repo.sources]]
            path = ""
            prefix = ""

            [[multi-repo.sources]]
            repo = "{repo2}"
            path = ""
            prefix = "Other"
        """).lstrip())

        call_command("import_notebook", "multi-repo", config=config_path)

        owner = get_public_owner()
        notebook = Notebook.objects.get(slug="multi-repo", owner=owner)

        file1 = notebook.get_page(path="file1")
        assert b"From repo 1" in file1.latest_version.content.data

        file2 = notebook.get_page(path="other/file2")
        assert file2.latest_version.filename == "Other/file2.md"
        assert b"From repo 2" in file2.latest_version.content.data

    def test_imports_index_from_indexes_directory(
        self,
        source_dir,
        system_notebook,
        config_with_name,
    ):
        (source_dir / "spells.md").write_text("# Spells\n\nA list of spells.")

        indexes_dir = config_with_name.parent / "indexes"
        indexes_dir.mkdir()
        (indexes_dir / "srd.md").write_text(dedent("""
            ---
            description: The System Reference Document for D&D 5e.
            ---

            # System Reference Document

            This notebook contains the official SRD content.
        """).lstrip())

        call_command(
            "import_notebook",
            "srd",
            str(source_dir),
            config=config_with_name,
        )

        index_page = system_notebook.get_page(path="index")
        assert index_page.latest_version.filename == "index.md"
        assert b"System Reference Document" in index_page.latest_version.content.data
        assert b"official SRD content" in index_page.latest_version.content.data


class TestAddSource:
    def test_inserts_source_after_h1(self):
        content = dedent("""\
            # Adult Brass Dragon

            _Huge Dragon (Metallic), Chaotic Good_

            - **AC** 18

        """)
        expected = dedent("""\
            # Adult Brass Dragon

            **Source:** _Monster Manual_

            _Huge Dragon (Metallic), Chaotic Good_

            - **AC** 18

        """)
        result = add_source(content, "Monster Manual")
        assert result == expected

    def test_inserts_source_when_no_blank_line_after_heading(self):
        content = dedent("""\

            # Adult Brass Dragon
            _Huge Dragon (Metallic), Chaotic Good_

        """)
        expected = dedent("""\

            # Adult Brass Dragon

            **Source:** _Monster Manual_

            _Huge Dragon (Metallic), Chaotic Good_

        """)
        result = add_source(content, "Monster Manual")
        assert result == expected

    def test_inserts_source_when_multiple_blank_lines_after_heading(self):
        content = dedent("""\
            # Adult Brass Dragon



            _Huge Dragon (Metallic), Chaotic Good_
        """)
        expected = dedent("""\
            # Adult Brass Dragon

            **Source:** _Monster Manual_



            _Huge Dragon (Metallic), Chaotic Good_
        """)
        result = add_source(content, "Monster Manual")
        assert result == expected

    def test_inserts_source_after_h1_with_frontmatter(self):
        content = dedent("""\
            ---
            tags: [dragon, metallic]
            cr: 13
            ---

            # Adult Brass Dragon

            _Huge Dragon (Metallic), Chaotic Good_

        """)
        expected = dedent("""\
            ---
            tags: [dragon, metallic]
            cr: 13
            ---

            # Adult Brass Dragon

            **Source:** _Monster Manual_

            _Huge Dragon (Metallic), Chaotic Good_

        """)
        result = add_source(content, "Monster Manual")
        assert result == expected

    def test_no_source_when_no_h1(self):
        content = dedent("""\
            ## Subheading

            Some content.
        """)
        result = add_source(content, "Monster Manual")
        assert result == content
