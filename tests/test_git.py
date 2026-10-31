import subprocess
from pathlib import Path

import pytest

from fsg.errors import GitError
from fsg.executable import Executable
from fsg.git import Git
from tests.conftest import create_files, init_repository, requires_git


@pytest.fixture
def clean_executable_cache():
    """Clears the cached executable lookups before and after the test."""

    Executable.find.cache_clear()
    yield
    Executable.find.cache_clear()


@pytest.mark.usefixtures("clean_executable_cache")
class TestMissingGit:
    """Covers running without a git executable."""

    def test_run_reports_missing_git(self, tmp_path: Path, monkeypatch) -> None:
        """Raises GitError when no git executable is found."""

        monkeypatch.setenv("PATH", "")
        with pytest.raises(GitError, match="not installed"):
            Git(tmp_path).run("status")

    def test_is_repository_without_git(self, tmp_path: Path, monkeypatch) -> None:
        """Reports False instead of raising when git is not installed."""

        monkeypatch.setenv("PATH", "")
        assert Git(tmp_path).is_repository() is False


@requires_git
class TestIsRepository:
    """Covers the git working tree detection."""

    def test_detects_repository(self, tmp_path: Path) -> None:
        """Reports True for a directory containing a git repository."""

        init_repository(tmp_path)
        assert Git(tmp_path).is_repository() is True

    def test_rejects_plain_directory(self, tmp_path: Path) -> None:
        """Reports False for a directory outside any repository."""

        assert Git(tmp_path).is_repository() is False

    def test_rejects_missing_directory(self, tmp_path: Path) -> None:
        """Reports False instead of raising when the directory does not exist."""

        assert Git(tmp_path / "missing").is_repository() is False

    def test_rejects_file_path(self, tmp_path: Path) -> None:
        """Reports False instead of raising when the path is a file."""

        create_files(tmp_path, ["__main__.py"])
        assert Git(tmp_path / "__main__.py").is_repository() is False


@requires_git
class TestToplevel:
    """Covers locating the root of the working tree."""

    def test_returns_root_from_subdirectory(self, tmp_path: Path) -> None:
        """Returns the top-level directory when started in a subdirectory."""

        init_repository(tmp_path)
        nested = tmp_path / "src"
        nested.mkdir()
        assert Git(nested).toplevel().resolve() == tmp_path.resolve()

    def test_returns_none_outside_repository(self, tmp_path: Path) -> None:
        """Returns None for a directory outside any repository."""

        assert Git(tmp_path).toplevel() is None

    def test_returns_none_for_missing_directory(self, tmp_path: Path) -> None:
        """Returns None instead of raising when the directory does not exist."""

        assert Git(tmp_path / "missing").toplevel() is None


@requires_git
class TestLsFiles:
    """Covers listing the paths of the working tree."""

    def test_lists_tracked_and_untracked_files(self, tmp_path: Path) -> None:
        """Returns staged and untracked paths with forward slashes."""

        init_repository(tmp_path)
        create_files(tmp_path, ["a.py", "src/b.py"])
        subprocess.run(["git", "add", "a.py"], cwd=tmp_path, check=True)
        assert sorted(Git(tmp_path).ls_files()) == ["a.py", "src/b.py"]

    def test_keeps_non_ascii_names(self, tmp_path: Path) -> None:
        """Returns file names with non-ASCII characters unchanged."""

        init_repository(tmp_path)
        create_files(tmp_path, ["Größe.md"])
        assert Git(tmp_path).ls_files() == ["Größe.md"]

    def test_leaves_out_deleted_files(self, tmp_path: Path) -> None:
        """Omits tracked files that were deleted from the working tree but not yet staged."""

        init_repository(tmp_path)
        create_files(tmp_path, ["keep.py", "gone.py"])
        subprocess.run(["git", "add", "."], cwd=tmp_path, check=True)
        (tmp_path / "gone.py").unlink()
        assert Git(tmp_path).ls_files() == ["keep.py"]

    def test_raises_outside_repository(self, tmp_path: Path) -> None:
        """Raises GitError carrying the git message, in the language of the user's locale, when the command fails."""

        with pytest.raises(GitError, match=r"^git ls-files failed: \S"):
            Git(tmp_path).ls_files()


@requires_git
class TestHooksDir:
    """Covers locating the hooks directory."""

    def test_returns_default_hooks_directory(self, tmp_path: Path) -> None:
        """Returns .git/hooks below the repository root."""

        init_repository(tmp_path)
        assert Git(tmp_path).hooks_dir() == tmp_path / ".git" / "hooks"

    def test_raises_outside_repository(self, tmp_path: Path) -> None:
        """Raises GitError when the directory is not inside a repository."""

        with pytest.raises(GitError, match="git rev-parse failed"):
            Git(tmp_path).hooks_dir()