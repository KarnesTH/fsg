from __future__ import annotations

import re
from pathlib import Path

from fsg.errors import MarkerError
from fsg.section import Section
from fsg.text_file import TextFile

START_MARKER = "<!-- fsg:start -->"
END_MARKER = "<!-- fsg:end -->"
START_LINE = re.compile(r"^<!-- fsg:start(?:\s+(?P<options>.*?))?\s*-->$")


class MarkedFile:
    """Reads, compares and replaces the blocks between fsg start and end markers of a text file."""

    def __init__(self, path: Path) -> None:
        """Reads the file and locates every block between a start and an end marker.

        Markers count only on a line of their own, indented by at most three spaces and outside a fenced code
        block. A start marker may carry options after "fsg:start".

        Args:
            path: Path of the file holding the markers.

        Raises:
            FileError: The file does not exist, is not UTF-8 or cannot be read.
            MarkerError: No block exists, a block has no end marker, or an end marker has no start marker.
        """

        self.path = Path(path)
        self.file = TextFile(path)
        self.text = self.file.read()
        self.newline = TextFile.newline(self.text)
        self.sections = self._scan()
        if not self.sections:
            raise MarkerError(
                f"{self.path}: missing {START_MARKER} marker",
                f"add {START_MARKER} and {END_MARKER} on their own lines outside a code block",
            )

    def content(self, index: int = 0) -> str:
        """Returns the text between the markers of a block.

        Args:
            index: Position of the block in the file, starting at 0.
        """

        section = self.sections[index]
        return self.text[section.inner_start:section.inner_end]

    def is_current(self, tree: str, index: int = 0) -> bool:
        """Returns whether a block equals the tree on its own lines.

        Args:
            tree: Rendered tree, using \\n line breaks.
            index: Position of the block in the file, starting at 0.
        """

        return self.content(index) == self._block(tree)

    def update(self, trees: list[str]) -> int:
        """Writes the trees into the blocks in file order when they differ and returns the number of changed blocks.

        The rest of the file is kept unchanged and the file is written once.

        Args:
            trees: Rendered trees, one per block, using \\n line breaks.

        Raises:
            FileError: The file cannot be written.
        """

        changed = 0
        text = self.text
        for section, tree in reversed(list(zip(self.sections, trees, strict=True))):
            block = self._block(tree)
            if text[section.inner_start:section.inner_end] != block:
                text = text[:section.inner_start] + block + text[section.inner_end:]
                changed += 1
        if changed:
            self.file.write(text)
            self.text = text
            self.sections = self._scan()
        return changed

    def _scan(self) -> list[Section]:
        """Returns the blocks of the file in order.

        A fence opens with three or more backticks or tildes indented by at most three spaces and closes with a
        line of at least as many of the same character; lines indented by four or more spaces or a tab never count
        as marker.

        Raises:
            MarkerError: A start marker follows another one before its end marker, an end marker has no start
                marker, a block has no end marker, or the options of a start marker are invalid.
        """

        sections: list[Section] = []
        open_start: tuple[int, int, dict[str, str]] | None = None
        position = 0
        fence = ""
        for number, line in enumerate(self.text.splitlines(keepends=True), start=1):
            content = line.rstrip("\r\n")
            stripped = content.strip()
            indent = len(content) - len(content.lstrip(" "))
            opening = self._fence(stripped) if indent < 4 else ""
            is_marker_line = indent < 4 and not content.startswith("\t")
            if fence:
                if opening and opening[0] == fence[0] and len(opening) >= len(fence) and stripped == opening:
                    fence = ""
            elif opening:
                fence = opening
            elif is_marker_line and (match := START_LINE.match(stripped)):
                if open_start is not None:
                    raise MarkerError(
                        f"{self.path}: missing {END_MARKER} marker after the {START_MARKER} in line {open_start[1]}",
                        f"put {END_MARKER} on its own line after each start marker",
                    )
                options = Section.parse_options(match.group("options") or "", f"{self.path}:{number}")
                open_start = (position + content.index(stripped) + len(stripped), number, options)
            elif is_marker_line and stripped == END_MARKER:
                if open_start is None:
                    raise MarkerError(
                        f"{self.path}: {END_MARKER} in line {number} has no {START_MARKER} before it",
                        "remove it or add the start marker above",
                    )
                inner_start, start_line, options = open_start
                sections.append(Section(inner_start, position + content.index(END_MARKER), start_line, options))
                open_start = None
            position += len(line)
        if open_start is not None:
            raise MarkerError(
                f"{self.path}: missing {END_MARKER} marker",
                f"put {END_MARKER} on its own line after {START_MARKER}",
            )
        return sections

    @staticmethod
    def _fence(stripped: str) -> str:
        """Returns the run of backticks or tildes a stripped line starts with when it is at least three long, otherwise an empty string.

        Args:
            stripped: Line without surrounding whitespace.
        """

        if not stripped or stripped[0] not in "`~":
            return ""
        run = len(stripped) - len(stripped.lstrip(stripped[0]))
        return stripped[:run] if run >= 3 else ""

    def _block(self, tree: str) -> str:
        """Returns the tree surrounded by line breaks, using the newline style of the file.

        Args:
            tree: Rendered tree, using \\n line breaks.
        """

        return self.newline + tree.replace("\n", self.newline) + self.newline