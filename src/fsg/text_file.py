from __future__ import annotations

import os
import stat
import tempfile
from pathlib import Path

from fsg.errors import FileError


class TextFile:
    """Reads and writes a UTF-8 text file without newline translation, replacing it atomically on write."""

    def __init__(self, path: Path) -> None:
        """Stores the path of the file.

        Args:
            path: Path of the text file.
        """

        self.path = Path(path)

    @staticmethod
    def newline(text: str) -> str:
        """Returns \\r\\n when the text contains it, otherwise \\n.

        Args:
            text: Text to inspect.
        """

        return "\r\n" if "\r\n" in text else "\n"

    def read(self) -> str:
        """Returns the content of the file with its original line endings.

        Raises:
            FileError: The file does not exist, is not valid UTF-8 or cannot be read.
        """

        try:
            with self.path.open(encoding="utf-8", newline="") as file:
                return file.read()
        except FileNotFoundError:
            raise FileError(f"{self.path}: file not found") from None
        except UnicodeDecodeError:
            raise FileError(f"{self.path}: not a UTF-8 text file") from None
        except OSError as error:
            raise FileError(f"{self.path}: {error.strerror or error}") from None

    def write(self, text: str, mode: int | None = None) -> None:
        """Writes the text to a temporary file next to the target and moves it over the target in one step.

        A symlinked target is resolved first, so the link stays in place. An existing file keeps its permission
        bits; a new file gets the given mode, or the default file mode of the process.

        Args:
            text: Content to write, written without newline translation.
            mode: Permission bits for a newly created file.

        Raises:
            FileError: The file cannot be written.
        """

        try:
            self._replace(text, mode)
        except OSError as error:
            raise FileError(f"{self.path}: {error.strerror or error}") from None

    def _replace(self, text: str, mode: int | None) -> None:
        """Writes the text to a temporary file in the target directory, applies the permission bits and renames it onto the target.

        Args:
            text: Content to write.
            mode: Permission bits for a newly created file.

        Raises:
            OSError: A file system operation fails; the temporary file is removed.
        """

        target = self.path.resolve()
        if target.exists():
            permissions = stat.S_IMODE(target.stat().st_mode)
        else:
            umask = os.umask(0)
            os.umask(umask)
            permissions = mode if mode is not None else 0o666 & ~umask
        descriptor, temporary = tempfile.mkstemp(prefix=f".{target.name}.", suffix=".tmp", dir=target.parent)
        try:
            with os.fdopen(descriptor, "w", encoding="utf-8", newline="") as file:
                file.write(text)
            os.chmod(temporary, permissions)
            os.replace(temporary, target)
        except BaseException:
            Path(temporary).unlink(missing_ok=True)
            raise