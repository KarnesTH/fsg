import json
import re
from pathlib import Path

import fsg
from fsg.errors import HookError
from fsg.hooks.hook import PRE_COMMIT_CONFIG, Hook
from fsg.text_file import TextFile

REPOSITORY_URL = "https://github.com/KarnesTH/fsg"
REPOSITORY_LINE = re.compile(r"^\s*(?:-\s*)?repo:\s*[\"']?https://github\.com/karnesth/fsg(?:\.git)?/?[\"']?\s*(?:#.*)?$", re.IGNORECASE)


class PreCommitHook(Hook):
    """Appends the fsg repository entry to the repos list of an existing .pre-commit-config.yaml."""

    def location(self) -> Path:
        """Returns the .pre-commit-config.yaml in the repository root."""

        return self.repository / PRE_COMMIT_CONFIG

    def install(self) -> bool:
        """Inserts the fsg entry after the last line of the repos block, keeping every other line unchanged.

        The entry uses the indentation of the first existing list item and the line endings of the file.
        Returns False without writing when a repo line already points to the fsg repository.

        Raises:
            HookError: The file has no block-style repos key at the top level or the installed version is unknown.
            FileError: The file cannot be read or written, or is not valid UTF-8.
        """

        path = self.location()
        file = TextFile(path)
        text = file.read()
        if any(REPOSITORY_LINE.match(line) for line in text.splitlines()):
            return False
        if fsg.__version__ == "unknown":
            raise HookError("cannot determine the installed fsg version", "install fsg as a package, e.g. uv tool install fsg")
        newline = TextFile.newline(text)
        lines = text.splitlines(keepends=True)
        start = next((index for index, line in enumerate(lines) if line.rstrip() == "repos:"), None)
        if start is None:
            raise HookError(f"{path}: no block-style 'repos:' list found", "add the fsg hook manually, see the README")
        last = start
        indent = None
        for index in range(start + 1, len(lines)):
            line = lines[index]
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            if not line[0].isspace() and not stripped.startswith("-"):
                break
            if indent is None and stripped.startswith("-"):
                indent = line[: len(line) - len(line.lstrip())]
            last = index
        if not lines[last].endswith(("\n", "\r")):
            lines[last] += newline
        lines.insert(last + 1, self._entry(indent if indent is not None else "  ", newline))
        file.write("".join(lines))
        return True

    def _entry(self, indent: str, newline: str) -> str:
        """Returns the repos list item for fsg, pinned to the installed version.

        Args:
            indent: Whitespace placed before the list dash.
            newline: Line break sequence of the file.
        """

        target = self.target if re.fullmatch(r"[\w./-]+", self.target) else json.dumps(self.target)
        lines = [
            f"{indent}- repo: {REPOSITORY_URL}",
            f"{indent}  rev: v{fsg.__version__}",
            f"{indent}  hooks:",
            f"{indent}    - id: fsg",
            f"{indent}      args: [--update, {target}]",
        ]
        return newline.join(lines) + newline