from pathlib import Path

from fsg.trees import PlainProjectTree
from tests.conftest import create_files, requires_unprivileged_user


class TestCollect:
    """Covers collecting without a git repository."""

    def test_skips_ignored_directories(self, project: Path) -> None:
        """Leaves out generated and tool directories from the walk."""

        output = PlainProjectTree(project).render()
        for name in ("__pycache__", ".idea", ".venv", "node_modules"):
            assert name not in output

    def test_keeps_source_files(self, project: Path) -> None:
        """Keeps the handwritten files of the project."""

        output = PlainProjectTree(project).render()
        for name in ("__main__.py", "README.md", "main_window.py", "home.svg"):
            assert name in output

    def test_keeps_hidden_files_that_are_not_ignored(self, tmp_path: Path) -> None:
        """Keeps dot files that are part of the project."""

        create_files(tmp_path, [".gitignore", ".github/workflows/ci.yml"])
        output = PlainProjectTree(tmp_path).render()
        assert ".gitignore" in output
        assert "ci.yml" in output

    def test_omits_empty_directories(self, tmp_path: Path) -> None:
        """Leaves out directories that contain no files."""

        create_files(tmp_path, ["__main__.py"])
        (tmp_path / "hollow").mkdir()
        assert "hollow" not in PlainProjectTree(tmp_path).render()

    def test_does_not_follow_directory_symlinks(self, tmp_path: Path) -> None:
        """Renders a symlinked directory as an entry without descending into it."""

        create_files(tmp_path, ["real/deep/file.py"])
        (tmp_path / "link").symlink_to(tmp_path / "real", target_is_directory=True)
        output = PlainProjectTree(tmp_path).render()
        assert "link" in output
        assert output.count("file.py") == 1

    @requires_unprivileged_user
    def test_skips_unreadable_directories(self, tmp_path: Path) -> None:
        """Continues the walk when a directory cannot be listed."""

        create_files(tmp_path, ["__main__.py", "locked/secret.py"])
        locked = tmp_path / "locked"
        locked.chmod(0o000)
        try:
            output = PlainProjectTree(tmp_path).render()
        finally:
            locked.chmod(0o755)
        assert "__main__.py" in output
        assert "secret.py" not in output