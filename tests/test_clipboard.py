import subprocess
from pathlib import Path

import pytest

from fsg.clipboard import Clipboard
from fsg.errors import ClipboardError
from fsg.executable import Executable


@pytest.fixture(autouse=True)
def clean_executable_cache():
    """Clears the cached executable lookups before and after the test."""

    Executable.find.cache_clear()
    yield
    Executable.find.cache_clear()


@pytest.fixture
def calls(monkeypatch) -> list[dict]:
    """Replaces subprocess.run and returns the list the calls are recorded in."""

    recorded: list[dict] = []

    def run(command, **kwargs):
        recorded.append({"command": command, **kwargs})
        return subprocess.CompletedProcess(command, 0)

    monkeypatch.setattr("fsg.clipboard.subprocess.run", run)
    return recorded


def fake_tool(directory: Path, name: str) -> str:
    """Creates an executable file with the name and returns its path.

    Args:
        directory: Directory the file is created in.
        name: File name.
    """

    path = directory / name
    path.write_text("", encoding="utf-8")
    path.chmod(0o755)
    return str(path)


@pytest.fixture
def linux(monkeypatch, tmp_path: Path) -> Path:
    """Points PATH to an empty directory and removes the graphical session variables."""

    monkeypatch.setenv("PATH", str(tmp_path))
    monkeypatch.delenv("WAYLAND_DISPLAY", raising=False)
    monkeypatch.delenv("DISPLAY", raising=False)
    return tmp_path


class TestLinux:
    """Covers choosing the clipboard tool on Linux."""

    def test_uses_wl_copy_on_wayland(self, linux: Path, calls: list, monkeypatch) -> None:
        """Runs wl-copy with the UTF-8 text when WAYLAND_DISPLAY is set."""

        tool = fake_tool(linux, "wl-copy")
        monkeypatch.setenv("WAYLAND_DISPLAY", "wayland-0")
        Clipboard("linux").copy("├── ä")
        assert calls[0]["command"] == [tool]
        assert calls[0]["input"] == "├── ä".encode()

    def test_uses_xclip_on_x11(self, linux: Path, calls: list, monkeypatch) -> None:
        """Runs xclip on the clipboard selection when DISPLAY is set."""

        tool = fake_tool(linux, "xclip")
        monkeypatch.setenv("DISPLAY", ":0")
        Clipboard("linux").copy("x")
        assert calls[0]["command"] == [tool, "-selection", "clipboard"]

    def test_falls_back_to_xsel(self, linux: Path, calls: list, monkeypatch) -> None:
        """Runs xsel when xclip is missing."""

        tool = fake_tool(linux, "xsel")
        monkeypatch.setenv("DISPLAY", ":0")
        Clipboard("linux").copy("x")
        assert calls[0]["command"] == [tool, "--clipboard", "--input"]

    def test_does_not_wait_for_background_tool(self, linux: Path, calls: list, monkeypatch) -> None:
        """Discards the output streams, so a tool that stays in the background cannot block."""

        fake_tool(linux, "wl-copy")
        monkeypatch.setenv("WAYLAND_DISPLAY", "wayland-0")
        Clipboard("linux").copy("x")
        assert calls[0]["stdout"] == subprocess.DEVNULL
        assert calls[0]["stderr"] == subprocess.DEVNULL

    def test_reports_missing_tool(self, linux: Path, monkeypatch) -> None:
        """Raises ClipboardError with an installation hint when no tool is found."""

        monkeypatch.setenv("WAYLAND_DISPLAY", "wayland-0")
        with pytest.raises(ClipboardError, match="no clipboard tool") as error:
            Clipboard("linux").copy("x")
        assert "wl-clipboard" in error.value.hint

    def test_reports_missing_session(self, linux: Path) -> None:
        """Raises ClipboardError when neither Wayland nor X11 is running."""

        with pytest.raises(ClipboardError) as error:
            Clipboard("linux").copy("x")
        assert "graphical session" in error.value.hint

    def test_reports_failing_tool(self, linux: Path, monkeypatch) -> None:
        """Raises ClipboardError with the exit status when the tool fails."""

        fake_tool(linux, "xclip")
        monkeypatch.setenv("DISPLAY", ":0")
        monkeypatch.setattr("fsg.clipboard.subprocess.run", lambda command, **_: subprocess.CompletedProcess(command, 1))
        with pytest.raises(ClipboardError, match="xclip failed with exit status 1"):
            Clipboard("linux").copy("x")


class TestOtherSystems:
    """Covers Windows and macOS."""

    def test_windows_uses_system_clip_with_utf16(self, calls: list, monkeypatch) -> None:
        """Runs clip.exe from System32 with UTF-16LE input."""

        monkeypatch.setenv("SystemRoot", "C:\\\\Windows")
        Clipboard("windows").copy("├──")
        assert calls[0]["command"][0].endswith("clip.exe")
        assert "System32" in calls[0]["command"][0]
        assert calls[0]["input"] == "├──".encode("utf-16-le")

    def test_macos_uses_pbcopy_with_utf8_locale(self, calls: list, monkeypatch, tmp_path: Path) -> None:
        """Runs pbcopy with a UTF-8 locale in its environment."""

        monkeypatch.setenv("PATH", str(tmp_path))
        tool = fake_tool(tmp_path, "pbcopy")
        Clipboard("macos").copy("x")
        assert calls[0]["command"] == [tool]
        assert calls[0]["env"]["LC_CTYPE"] == "UTF-8"


def test_detects_running_system() -> None:
    """Chooses the system name from the running interpreter when none is given."""

    assert Clipboard().system in ("windows", "macos", "linux")