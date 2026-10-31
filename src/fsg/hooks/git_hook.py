import shlex
import subprocess
from pathlib import Path

from fsg.hooks.hook import Hook

MARKER = "# fsg: keep the directory tree up to date"


class GitHook(Hook):
    """Writes the fsg step into the native pre-commit hook script of the repository."""

    def location(self) -> Path:
        """Returns the pre-commit script inside the hooks directory git reports, honoring core.hooksPath."""

        result = subprocess.run(
            ["git", "rev-parse", "--git-path", "hooks"],
            cwd=self.repository,
            capture_output=True,
            text=True,
            check=True,
        )
        hooks = Path(result.stdout.strip())
        if not hooks.is_absolute():
            hooks = self.repository / hooks
        return hooks / "pre-commit"

    def install(self) -> bool:
        """Creates the executable script or adds the fsg step to the existing one.

        In an existing script the step goes before a final exit line, otherwise at the end.
        Returns False without writing when the script already contains the fsg step.
        """

        path = self.location()
        if not path.exists():
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("#!/bin/sh\n" + self._step(), encoding="utf-8", newline="\n")
            path.chmod(0o755)
            return True
        lines = path.read_text(encoding="utf-8").splitlines(keepends=True)
        if any(line.strip() == MARKER for line in lines):
            return False
        position = len(lines)
        content = [index for index, line in enumerate(lines) if line.strip() and not line.lstrip().startswith("#")]
        if content and lines[content[-1]].split()[0] == "exit":
            position = content[-1]
        if lines and not lines[-1].endswith("\n"):
            lines[-1] += "\n"
        lines.insert(position, self._step())
        path.write_text("".join(lines), encoding="utf-8", newline="\n")
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
            f"    1) fsg --update {target}; echo \"fsg: add {self.target} and commit again\"; exit 1 ;;\n"
            f"    *) fsg --check {target}; exit 1 ;;\n"
            "  esac\n"
            "fi\n"
        )