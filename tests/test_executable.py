import os
from pathlib import Path

import pytest

from fsg.executable import Executable


@pytest.fixture(autouse=True)
def clean_executable_cache():
    """Clears the cached executable lookups before and after the test."""

    Executable.find.cache_clear()
    yield
    Executable.find.cache_clear()


class TestFind:
    """Covers locating programs on PATH."""

    def test_ignores_current_directory(self, tmp_path: Path, monkeypatch) -> None:
        """Skips a git file in the current directory and in relative PATH entries."""

        fake = tmp_path / ("git.exe" if os.name == "nt" else "git")
        fake.write_text("", encoding="utf-8")
        fake.chmod(0o755)
        monkeypatch.chdir(tmp_path)
        monkeypatch.setenv("PATH", os.pathsep.join([".", "", "relative/bin"]))
        assert Executable.find("git") is None

    def test_finds_git_in_absolute_entry(self, tmp_path: Path, monkeypatch) -> None:
        """Returns the absolute path of the first matching executable."""

        bin_dir = tmp_path / "bin"
        bin_dir.mkdir()
        name = "git.exe" if os.name == "nt" else "git"
        (bin_dir / name).write_text("", encoding="utf-8")
        (bin_dir / name).chmod(0o755)
        monkeypatch.setenv("PATH", str(bin_dir))
        monkeypatch.setenv("PATHEXT", ".EXE")
        assert Path(Executable.find("git")) == bin_dir / name

    @pytest.mark.skipif(os.name == "nt", reason="execute permission is not checked on Windows")
    def test_skips_non_executable_file(self, tmp_path: Path, monkeypatch) -> None:
        """Ignores a git file without execute permission."""

        (tmp_path / "git").write_text("", encoding="utf-8")
        (tmp_path / "git").chmod(0o644)
        monkeypatch.setenv("PATH", str(tmp_path))
        assert Executable.find("git") is None