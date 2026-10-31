from pathlib import Path

from fsg.errors import MarkerError
from fsg.text_file import TextFile

START_MARKER = "<!-- fsg:start -->"
END_MARKER = "<!-- fsg:end -->"


class ReadmeSection:
    """Reads, compares and replaces the block between the fsg markers of a text file."""

    def __init__(self, path: Path) -> None:
        """Reads the file and locates the block between the start and end marker.

        Both markers count only on a line of their own, indented by at most three spaces and outside a
        fenced code block; the end marker is the first such line after the start marker.

        Args:
            path: Path of the file holding the markers.

        Raises:
            FileError: The file does not exist, is not UTF-8 or cannot be read.
            MarkerError: A marker is missing.
        """

        self.file = TextFile(path)
        self.text = self.file.read()
        self.newline = TextFile.newline(self.text)
        start = self._find_line(START_MARKER, 0)
        if start == -1:
            raise MarkerError(
                f"{path}: missing {START_MARKER} marker",
                f"add {START_MARKER} and {END_MARKER} on their own lines outside a code block",
            )
        self.inner_start = start + len(START_MARKER)
        end = self._find_line(END_MARKER, self.inner_start)
        if end == -1:
            raise MarkerError(
                f"{path}: missing {END_MARKER} marker",
                f"put {END_MARKER} on its own line after {START_MARKER}",
            )
        self.inner_end = end

    def content(self) -> str:
        """Returns the text between the markers."""

        return self.text[self.inner_start:self.inner_end]

    def is_current(self, tree: str) -> bool:
        """Returns whether the block between the markers equals the tree on its own lines.

        Args:
            tree: Rendered tree, using \\n line breaks.
        """

        return self.content() == self._block(tree)

    def update(self, tree: str) -> bool:
        """Writes the tree between the markers when it differs, keeping the rest of the file, and returns whether the file was changed.

        Args:
            tree: Rendered tree, using \\n line breaks.

        Raises:
            FileError: The file cannot be written.
        """

        block = self._block(tree)
        if self.content() == block:
            return False
        text = self.text[:self.inner_start] + block + self.text[self.inner_end:]
        self.file.write(text)
        self.text = text
        self.inner_end = self.inner_start + len(block)
        return True

    def _find_line(self, marker: str, offset: int) -> int:
        """Returns the offset of the first line at or after the offset that holds only the marker outside a fenced code block, or -1.

        Scanning starts at the beginning of the line containing the offset. A fence opens with three or more
        backticks or tildes indented by at most three spaces and closes with a line of at least as many of the
        same character; lines indented by four or more spaces never count as marker.

        Args:
            marker: Marker text the line must consist of, apart from surrounding whitespace.
            offset: Position in the text to start from.
        """

        position = self.text.rfind("\n", 0, offset) + 1
        fence = ""
        for line in self.text[position:].splitlines(keepends=True):
            content = line.rstrip("\r\n")
            stripped = content.strip()
            indent = len(content) - len(content.lstrip(" "))
            opening = self._fence(stripped) if indent < 4 else ""
            if fence:
                if opening and opening[0] == fence[0] and len(opening) >= len(fence) and stripped == opening:
                    fence = ""
            elif opening:
                fence = opening
            elif stripped == marker and indent < 4 and not content.startswith("\t"):
                index = position + content.index(marker)
                if index >= offset:
                    return index
            position += len(line)
        return -1

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