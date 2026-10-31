import shlex
from pathlib import Path

from fsg.git import Git
from fsg.hooks.hook import Hook
from fsg.text_file import TextFile

MARKER = "# fsg: keep the directory tree up to date"


class GitHook(Hook):
    """Writes the fsg step into the native pre-commit hook script of the repository."""

    def location(self) -> Path:
        """Returns the pre-commit script inside the hooks directory git reports, honouring core.hooksPath.

        Raises:
            GitError: git cannot run or the command fails.
        """

        return Git(self.repository).hooks_dir() / "pre-commit"

    def install(self) -> bool:
        """Creates the executable script or adds the fsg step to the existing one.

        In an existing script the step goes before a final exit or exec line, otherwise at the end; line endings become \\n.
        Returns False without writing when the script already contains the fsg step.

        Raises:
            GitError: git cannot run or the command fails.
            FileError: The script cannot be read or written, or is not valid UTF-8.
        """

        path = self.location()
        file = TextFile(path)
        if not path.exists():
            path.parent.mkdir(parents=True, exist_ok=True)
            file.write("#!/bin/sh\n" + self._step(), mode=0o755)
            return True
        lines = file.read().replace("\r\n", "\n").splitlines(keepends=True)
        if any(line.strip() == MARKER for line in lines):
            return False
        position = len(lines)
        content = [index for index, line in enumerate(lines) if line.strip() and not line.lstrip().startswith("#")]
        if content and lines[content[-1]].split()[0] in ("exit", "exec"):
            position = content[-1]
        if lines and not lines[-1].endswith("\n"):
            lines[-1] += "\n"
        lines.insert(position, self._step())
        file.write("".join(lines))
        return True

    def _step(self) -> str:
        """Returns the shell block that updates the target and aborts the commit when the tree was outdated, or shows the error when the check fails otherwise."""

        target = shlex.quote(self.target)
        return (
            f"{MARKER}\n"
            "if command -v fsg >/dev/null 2>&1; then\n"
            f"  fsg --check {target} >/dev/null 2>&1\n"
            "  case $? in\n"
            "    0) ;;\n"
            f"    1) fsg --update {target}; printf 'fsg: add %s and commit again\\n' {target}; exit 1 ;;\n"
            f"    *) fsg --check {target}; exit 1 ;;\n"
            "  esac\n"
            "fi\n"
        )