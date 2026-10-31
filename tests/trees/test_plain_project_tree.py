from pathlib import Path

import pytest

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
        try:
            (tmp_path / "link").symlink_to(tmp_path / "real", target_is_directory=True)
        except OSError:
            pytest.skip("creating symlinks is not permitted")
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

class TestPrunedWalk:
    """Covers that the walk stops early without changing the rendered tree."""

    @staticmethod
    def project(root: Path) -> None:
        """Creates a nested project with files on several levels, an excluded directory and a directory without files.

        Args:
            root: Directory the project is created in.
        """

        create_files(
            root,
            [
                "README.md",
                "src/main.py",
                "src/pkg/core.py",
                "src/pkg/deep/deeper/leaf.txt",
                "docs/guide.md",
                "docs/api/index.md",
                "vendor/lib/a.js",
                "only_dirs/empty/.keep",
            ],
        )
        (root / "hollow" / "inner").mkdir(parents=True)

    @pytest.mark.parametrize(
        "options",
        [
            {"depth": 1},
            {"depth": 2},
            {"depth": 2, "dirs_only": True},
            {"depth": 1, "include": ["*.md"]},
            {"depth": 2, "include": ["*.txt"]},
            {"depth": 3, "exclude": ["vendor", "*.md"]},
            {"depth": 1, "include": ["*.js"], "exclude": ["vendor"]},
            {"exclude": ["src/pkg"]},
            {"include": ["docs"], "dirs_only": True},
        ],
    )
    def test_matches_unpruned_result(self, tmp_path: Path, options: dict) -> None:
        """Renders the same tree as filtering the complete list of paths."""

        self.project(tmp_path)
        pruned = PlainProjectTree(tmp_path, **options)
        complete = [parts for parts in self.all_files(tmp_path)]
        reference = PlainProjectTree(tmp_path, **options)
        reference.collect = lambda: complete
        assert pruned.render() == reference.render()

    def test_does_not_enter_directories_below_depth(self, tmp_path: Path, monkeypatch) -> None:
        """Lists no directory deeper than needed to mark the last rendered level as directory."""

        self.project(tmp_path)
        visited: list[Path] = []
        original = PlainProjectTree._children

        def children(directory: Path) -> list[Path]:
            visited.append(directory)
            return original(directory)

        monkeypatch.setattr(PlainProjectTree, "_children", staticmethod(children))
        PlainProjectTree(tmp_path, depth=1).collect()
        assert tmp_path / "src" / "pkg" / "deep" not in visited

    def test_does_not_enter_excluded_directories(self, tmp_path: Path, monkeypatch) -> None:
        """Never lists a directory that matches an exclude pattern."""

        self.project(tmp_path)
        visited: list[Path] = []
        original = PlainProjectTree._children

        def children(directory: Path) -> list[Path]:
            visited.append(directory)
            return original(directory)

        monkeypatch.setattr(PlainProjectTree, "_children", staticmethod(children))
        PlainProjectTree(tmp_path, exclude=["vendor"]).collect()
        assert tmp_path / "vendor" not in visited

    @staticmethod
    def all_files(root: Path) -> list[list[str]]:
        """Returns the parts of every file below the root, without any filtering.

        Args:
            root: Directory to list.
        """

        return [list(path.relative_to(root).parts) for path in root.rglob("*") if path.is_file()]