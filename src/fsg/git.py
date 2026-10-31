from __future__ import annotations

import os
import subprocess
from functools import cache
from pathlib import Path


class Git:
    """Runs git commands in one directory with the git executable found on PATH."""

    def __init__(self, directory: Path) -> None:
        """Stores the directory the commands run in.

        Args:
            directory: Working directory for every git command.
        """

        self.directory = Path(directory)

    @staticmethod
    @cache
    def executable() -> str | None:
        """Returns the absolute path of the first git executable in the absolute PATH entries, or None.

        Relative entries and the current directory are skipped. On Windows every extension listed in PATHEXT is tried.
        """

        names = ["git"]
        if os.name == "nt":
            extensions = os.environ.get("PATHEXT", ".COM;.EXE;.BAT;.CMD").split(os.pathsep)
            names = [f"git{extension.lower()}" for extension in extensions if extension]
        for entry in os.environ.get("PATH", "").split(os.pathsep):
            directory = Path(entry)
            if not entry or not directory.is_absolute():
                continue
            for name in names:
                candidate = directory / name
                if candidate.is_file() and os.access(candidate, os.X_OK):
                    return str(candidate)
        return None

    def run(self, *args: str) -> subprocess.CompletedProcess[str]:
        """Runs git with the arguments and returns the completed process without checking the exit status.

        Args:
            *args: Arguments passed to git.

        Raises:
            OSError: git is not installed or the directory does not exist.
        """

        executable = self.executable()
        if executable is None:
            raise OSError("git is not installed or not on PATH")
        return subprocess.run(
            [executable, *args],
            cwd=self.directory,
            capture_output=True,
            text=True,
            encoding="utf-8",
            check=False,
        )

    def is_repository(self) -> bool:
        """Returns whether the directory lies inside a git working tree, False when git cannot run there."""

        try:
            result = self.run("rev-parse", "--is-inside-work-tree")
        except OSError:
            return False
        return result.returncode == 0 and result.stdout.strip() == "true"

    def toplevel(self) -> Path | None:
        """Returns the root of the working tree containing the directory, or None outside a repository."""

        try:
            result = self.run("rev-parse", "--show-toplevel")
        except OSError:
            return None
        if result.returncode != 0:
            return None
        return Path(result.stdout.strip())

    def ls_files(self) -> list[str]:
        """Returns the tracked and untracked but not ignored paths relative to the directory, using forward slashes.

        Raises:
            OSError: git cannot run or the command fails.
        """

        result = self._checked("ls-files", "--cached", "--others", "--exclude-standard", "-z")
        return [entry for entry in result.stdout.split("\0") if entry]

    def hooks_dir(self) -> Path:
        """Returns the absolute hooks directory of the repository, honouring core.hooksPath.

        Raises:
            OSError: git cannot run or the command fails.
        """

        hooks = Path(self._checked("rev-parse", "--git-path", "hooks").stdout.strip())
        return hooks if hooks.is_absolute() else self.directory / hooks

    def _checked(self, *args: str) -> subprocess.CompletedProcess[str]:
        """Runs git and raises with the git error output when the exit status is not zero.

        Args:
            *args: Arguments passed to git.

        Raises:
            OSError: git cannot run or the command fails.
        """

        result = self.run(*args)
        if result.returncode != 0:
            message = result.stderr.strip() or f"exit status {result.returncode}"
            raise OSError(f"git {args[0]} failed: {message}")
        return result