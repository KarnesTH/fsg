from __future__ import annotations

import os
import subprocess
from functools import cache
from pathlib import Path

from fsg.errors import GitError


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
            GitError: git is not installed or cannot be started in the directory.
        """

        executable = self.executable()
        if executable is None:
            raise GitError("git is not installed or not on PATH", "install git or add it to PATH")
        try:
            return subprocess.run(
                [executable, *args],
                cwd=self.directory,
                capture_output=True,
                text=True,
                encoding="utf-8",
                check=False,
            )
        except OSError as error:
            raise GitError(f"git cannot run in {self.directory}: {error.strerror or error}") from None

    def is_repository(self) -> bool:
        """Returns whether the directory lies inside a git working tree, False when git cannot run there."""

        try:
            result = self.run("rev-parse", "--is-inside-work-tree")
        except GitError:
            return False
        return result.returncode == 0 and result.stdout.strip() == "true"

    def toplevel(self) -> Path | None:
        """Returns the root of the working tree containing the directory, or None outside a repository."""

        try:
            result = self.run("rev-parse", "--show-toplevel")
        except GitError:
            return None
        if result.returncode != 0:
            return None
        return Path(result.stdout.strip())

    def ls_files(self) -> list[str]:
        """Returns the tracked and untracked but not ignored paths relative to the directory, using forward slashes.

        Tracked files deleted from the working tree are left out.

        Raises:
            GitError: git cannot run or the command fails.
        """

        listed = self._checked("ls-files", "--cached", "--others", "--exclude-standard", "-z").stdout
        deleted = set(self._checked("ls-files", "--deleted", "-z").stdout.split("\0"))
        return [entry for entry in listed.split("\0") if entry and entry not in deleted]

    def hooks_dir(self) -> Path:
        """Returns the absolute hooks directory of the repository, honoring core.hooksPath.

        Raises:
            GitError: git cannot run or the command fails.
        """

        hooks = Path(self._checked("rev-parse", "--git-path", "hooks").stdout.strip())
        return hooks if hooks.is_absolute() else self.directory / hooks

    def _checked(self, *args: str) -> subprocess.CompletedProcess[str]:
        """Runs git and raises with the git error output when the exit status is not zero.

        Args:
            *args: Arguments passed to git.

        Raises:
            GitError: git cannot run or the command fails.
        """

        result = self.run(*args)
        if result.returncode != 0:
            message = result.stderr.strip() or f"exit status {result.returncode}"
            raise GitError(f"git {args[0]} failed: {message}")
        return result