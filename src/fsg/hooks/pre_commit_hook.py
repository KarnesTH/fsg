import json
import re
from importlib.metadata import version
from pathlib import Path

from fsg.hooks.hook import PRE_COMMIT_CONFIG, Hook
from fsg.text_file import TextFile

REPOSITORY_URL = "https://github.com/KarnesTH/fsg"


class PreCommitHook(Hook):
    """Appends the fsg repository entry to the repos list of an existing .pre-commit-config.yaml."""

    def location(self) -> Path:
        """Returns the .pre-commit-config.yaml in the repository root."""

        return self.repository / PRE_COMMIT_CONFIG

    def install(self) -> bool:
        """Inserts the fsg entry after the last line of the repos block, keeping every other line unchanged.

        The entry uses the indentation of the first existing list item and the line endings of the file.
        Returns False without writing when the file already references the fsg repository.

        Raises:
            ValueError: The file has no block-style repos key at the top level or is not valid UTF-8.
            OSError: The file cannot be read or written.
        """

        path = self.location()
        file = TextFile(path)
        text = file.read()
        if "karnesth/fsg" in text.lower():
            return False
        newline = TextFile.newline(text)
        lines = text.splitlines(keepends=True)
        start = next((index for index, line in enumerate(lines) if line.rstrip() == "repos:"), None)
        if start is None:
            raise ValueError(f"{path}: no 'repos:' block found, add the fsg hook manually")
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
            f"{indent}  rev: v{version('fsg')}",
            f"{indent}  hooks:",
            f"{indent}    - id: fsg",
            f"{indent}      args: [--update, {target}]",
        ]
        return newline.join(lines) + newline