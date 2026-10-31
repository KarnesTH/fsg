from __future__ import annotations

import re

from fsg.constants import STYLES

COMMENT = re.compile(r"^(?P<name>.*?\S)\s{2,}#\s?(?P<comment>.*?)\s*$")
SUMMARY = re.compile(r"^\d+ director(?:y|ies), \d+ files?$")


class TreeComments:
    """Reads the "# comment" annotations of a rendered tree and maps them to the relative paths of their entries."""

    def __init__(self, glyph_characters: set[str] | None = None) -> None:
        """Stores the characters that can appear in the branch prefix of a line.

        Args:
            glyph_characters: Characters of custom glyphs in addition to those of every built-in style.
        """

        characters = {character for style in STYLES.values() for value in style.values() for character in value}
        self.glyph_characters = characters | (glyph_characters or set())

    def parse(self, block: str) -> dict[str, str]:
        """Returns the comments of a rendered tree block, keyed by relative path with forward slashes, "" for the root.

        Fence lines, empty lines and the summary line are skipped. The level of an entry is taken from the column
        its name starts at, divided by the column of the first entry below the root.

        Args:
            block: Text of the tree, with or without surrounding code fence.
        """

        comments: dict[str, str] = {}
        lines = [line for line in block.splitlines() if line.strip() and not line.lstrip().startswith(("```", "~~~"))]
        lines = [line for line in lines if not SUMMARY.match(line.strip())]
        if not lines:
            return comments
        _, root_comment = self._split(lines[0])
        if root_comment is not None:
            comments[""] = root_comment
        unit = 0
        parents: list[str] = []
        for line in lines[1:]:
            start = self._name_start(line)
            if start == 0:
                continue
            unit = unit or start
            level = max(start // unit, 1)
            name, comment = self._split(line[start:])
            parents = parents[: level - 1] + [name.rstrip("/")]
            if comment is not None:
                comments["/".join(parents)] = comment
        return comments

    def _name_start(self, line: str) -> int:
        """Returns the column the entry name starts at: after the last space within the leading run of glyph characters.

        Args:
            line: Rendered tree line.
        """

        run = 0
        while run < len(line) and line[run] in self.glyph_characters:
            run += 1
        last_space = line.rfind(" ", 0, run)
        return last_space + 1 if last_space != -1 else run

    @staticmethod
    def _split(text: str) -> tuple[str, str | None]:
        """Splits an entry into name and comment, the comment being None when the entry has none.

        Args:
            text: Entry name with an optional comment separated by at least two spaces and a hash.
        """

        match = COMMENT.match(text)
        if match is None:
            return text.rstrip(), None
        return match.group("name"), match.group("comment")