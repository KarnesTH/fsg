import os
import subprocess
from pathlib import Path

import pytest

from fsg.git import Git
from tests.conftest import create_files, init_repository, requires_git


@pytest.fixture
def clean_executable_cache():
    """Clears the cached git executable before and after the test."""

    Git.executable.cache_clear()
    yield
    Git.executable.cache_clear()


@pytest.mark.usefixtures("clean_executable_cache")
class TestExecutable:
    """Covers locating the git executable."""

    def test_ignores_current_directory(self, tmp_path: Path, monkeypatch) -> None:
        """Skips a git file in the current directory and in relative PATH entries."""

        fake = tmp_path / ("git.exe" if os.name == "nt" else "git")
        fake.write_text("", encoding="utf-8")
        fake.chmod(0o755)
        monkeypatch.chdir(tmp_path)
        monkeypatch.setenv("PATH", os.pathsep.join([".", "", "relative/bin"]))
        assert Git.executable() is None

    def test_finds_git_in_absolute_entry(self, tmp_path: Path, monkeypatch) -> None:
        """Returns the absolute path of the first matching executable."""

        bin_dir = tmp_path / "bin"
        bin_dir.mkdir()
        name = "git.exe" if os.name == "nt" else "git"
        (bin_dir / name).write_text("", encoding="utf-8")
        (bin_dir / name).chmod(0o755)
        monkeypatch.setenv("PATH", str(bin_dir))
        monkeypatch.setenv("PATHEXT", ".EXE")
        assert Path(Git.executable()) == bin_dir / name

    @pytest.mark.skipif(os.name == "nt", reason="execute permission is not checked on Windows")
    def test_skips_non_executable_file(self, tmp_path: Path, monkeypatch) -> None:
        """Ignores a git file without execute permission."""

        (tmp_path / "git").write_text("", encoding="utf-8")
        (tmp_path / "git").chmod(0o644)
        monkeypatch.setenv("PATH", str(tmp_path))
        assert Git.executable() is None

    def test_run_reports_missing_git(self, tmp_path: Path, monkeypatch) -> None:
        """Raises OSError when no git executable is found."""

        monkeypatch.setenv("PATH", "")
        with pytest.raises(OSError, match="not installed"):
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

    def test_raises_outside_repository(self, tmp_path: Path) -> None:
        """Raises OSError carrying the git message, in the language of the user's locale, when the command fails."""

        with pytest.raises(OSError, match=r"^git ls-files failed: \S"):
            Git(tmp_path).ls_files()


@requires_git
class TestHooksDir:
    """Covers locating the hooks directory."""

    def test_returns_default_hooks_directory(self, tmp_path: Path) -> None:
        """Returns .git/hooks below the repository root."""

        init_repository(tmp_path)
        assert Git(tmp_path).hooks_dir() == tmp_path / ".git" / "hooks"

    def test_raises_outside_repository(self, tmp_path: Path) -> None:
        """Raises OSError when the directory is not inside a repository."""

        with pytest.raises(OSError, match="git rev-parse failed"):
            Git(tmp_path).hooks_dir()