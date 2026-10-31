from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from fsg.errors import ClipboardError
from fsg.executable import Executable


class Clipboard:
    """Copies text to the system clipboard with the tool the operating system provides."""

    def __init__(self, system: str | None = None) -> None:
        """Stores the operating system the clipboard tool is chosen for.

        Args:
            system: "windows", "macos" or "linux", detected from the running system when None.
        """

        if system is None:
            system = "windows" if os.name == "nt" else "macos" if sys.platform == "darwin" else "linux"
        self.system = system

    def copy(self, text: str) -> None:
        """Copies the text with clip.exe on Windows, pbcopy on macOS, or wl-copy, xclip or xsel on Linux.

        clip.exe receives UTF-16LE, every other tool UTF-8.

        Args:
            text: Text to copy.

        Raises:
            ClipboardError: No clipboard tool is available or the tool fails.
        """

        command, data, environment = self._command(text)
        try:
            result = subprocess.run(
                command,
                input=data,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                env=environment,
                check=False,
            )
        except OSError as error:
            raise ClipboardError(f"{Path(command[0]).stem} cannot run: {error.strerror or error}") from None
        if result.returncode != 0:
            raise ClipboardError(f"{Path(command[0]).stem} failed with exit status {result.returncode}")

    def _command(self, text: str) -> tuple[list[str], bytes, dict[str, str] | None]:
        """Returns the command line, the encoded input and the environment of the clipboard tool for this system.

        On Windows clip.exe is taken from the System32 directory; elsewhere tools are looked up on PATH. On Linux,
        wl-copy is used when WAYLAND_DISPLAY is set and xclip or xsel when DISPLAY is set.

        Args:
            text: Text to copy.

        Raises:
            ClipboardError: No suitable tool is found.
        """

        if self.system == "windows":
            clip = Path(os.environ.get("SystemRoot", r"C:\Windows")) / "System32" / "clip.exe"
            return [str(clip)], text.encode("utf-16-le"), None
        data = text.encode("utf-8")
        if self.system == "macos":
            pbcopy = Executable.find("pbcopy")
            if pbcopy:
                return [pbcopy], data, {**os.environ, "LANG": "en_US.UTF-8", "LC_CTYPE": "UTF-8"}
            raise ClipboardError("pbcopy not found")
        candidates = []
        if os.environ.get("WAYLAND_DISPLAY"):
            candidates.append(("wl-copy", []))
        if os.environ.get("DISPLAY"):
            candidates += [("xclip", ["-selection", "clipboard"]), ("xsel", ["--clipboard", "--input"])]
        for name, arguments in candidates:
            executable = Executable.find(name)
            if executable:
                return [executable, *arguments], data, None
        raise ClipboardError(
            "no clipboard tool found",
            "install wl-clipboard on Wayland or xclip on X11" if candidates else "no graphical session detected",
        )