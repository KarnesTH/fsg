import subprocess
from pathlib import Path

import pytest

from fsg.errors import GitError
from fsg.trees import GitProjectTree, PlainProjectTree
from tests.conftest import create_files, init_repository, requires_git


@requires_git
class TestCollect:
    """Covers collecting inside a git repository."""

    def test_honours_gitignore(self, tmp_path: Path) -> None:
        """Leaves out paths that are ignored by a .gitignore file."""

        create_files(tmp_path, ["__main__.py", "logs/run.log"])
        (tmp_path / ".gitignore").write_text("logs/\n", encoding="utf-8")
        init_repository(tmp_path)
        output = GitProjectTree(tmp_path).render()
        assert "run.log" not in output
        assert ".gitignore" in output

    def test_filters_ignored_names_without_root_gitignore(self, project: Path) -> None:
        """Leaves out generated directories even when only a PyCharm .idea/.gitignore exists."""

        init_repository(project)
        output = GitProjectTree(project).render()
        for name in ("__pycache__", ".idea", ".venv", "node_modules"):
            assert name not in output

    def test_keeps_untracked_source_files(self, project: Path) -> None:
        """Includes files that are untracked but not ignored."""

        init_repository(project)
        output = GitProjectTree(project).render()
        for name in ("__main__.py", "README.md", "chip.py", "home.svg"):
            assert name in output

    def test_keeps_tracked_files(self, tmp_path: Path) -> None:
        """Includes files that are staged in the index."""

        create_files(tmp_path, ["__main__.py"])
        init_repository(tmp_path)
        subprocess.run(["git", "add", "__main__.py"], cwd=tmp_path, check=True)
        assert "__main__.py" in GitProjectTree(tmp_path).render()

    def test_raises_outside_repository(self, tmp_path: Path) -> None:
        """Raises OSError with the git message instead of returning an empty result when git fails."""

        create_files(tmp_path, ["__main__.py"])
        with pytest.raises(GitError, match="git ls-files failed"):
            GitProjectTree(tmp_path).collect()

    def test_matches_plain_output_for_a_clean_project(self, tmp_path: Path) -> None:
        """Produces the same tree as the plain walk when no repository-specific rules apply."""

        create_files(tmp_path, ["__main__.py", "gui/window.py", "gui/__pycache__/window.pyc"])
        plain = PlainProjectTree(tmp_path).render()
        init_repository(tmp_path)
        assert GitProjectTree(tmp_path).render() == plain