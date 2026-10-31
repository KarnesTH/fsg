from pathlib import Path

START_MARKER = "<!-- fsg:start -->"
END_MARKER = "<!-- fsg:end -->"


class ReadmeSection:
    """Reads, compares and replaces the block between the fsg markers of a text file."""

    def __init__(self, path: Path) -> None:
        """Reads the file without newline translation and locates the block between the start and end marker.

        The start marker counts only on a line of its own outside a fenced code block;
        the end marker is the first one following it.

        Args:
            path: Path of the file holding the markers.

        Raises:
            FileNotFoundError: The file does not exist.
            ValueError: A marker is missing or the end marker precedes the start marker.
        """

        self.path = Path(path)
        with self.path.open(encoding="utf-8", newline="") as file:
            self.text = file.read()
        self.newline = "\r\n" if "\r\n" in self.text else "\n"
        start = self._find_start()
        end = self.text.find(END_MARKER, start + len(START_MARKER)) if start != -1 else -1
        if start == -1 or end == -1:
            raise ValueError(f"missing {START_MARKER} / {END_MARKER} markers in {self.path}")
        self.inner_start = start + len(START_MARKER)
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
        """

        block = self._block(tree)
        if self.content() == block:
            return False
        self.text = self.text[:self.inner_start] + block + self.text[self.inner_end:]
        self.inner_end = self.inner_start + len(block)
        with self.path.open("w", encoding="utf-8", newline="") as file:
            file.write(self.text)
        return True

    def _find_start(self) -> int:
        """Returns the offset of the first start marker standing alone on a line outside a fenced code block, or -1."""

        offset = 0
        fence = ""
        for line in self.text.splitlines(keepends=True):
            stripped = line.strip()
            if fence:
                if stripped.startswith(fence):
                    fence = ""
            elif stripped.startswith(("```", "~~~")):
                fence = stripped[:3]
            elif stripped == START_MARKER:
                return offset + line.index(START_MARKER)
            offset += len(line)
        return -1

    def _block(self, tree: str) -> str:
        """Returns the tree surrounded by line breaks, using the newline style of the file.

        Args:
            tree: Rendered tree, using \\n line breaks.
        """

        return self.newline + tree.replace("\n", self.newline) + self.newline