from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

from fsg.constants import ASCII_GLYPHS, IGNORED, UNICODE_GLYPHS


class ProjectTree:
    """Collects the relevant paths of a project directory and renders them as a tree."""

    def __init__(self, root: Path, use_ascii: bool = False) -> None:
        """Resolves and stores the root directory of the project and selects the glyph set for the branches.

        Args:
            root: Path of the directory to render.
            use_ascii: Draws the branches with ASCII characters instead of box-drawing characters.
        """

        self.root = Path(root).resolve()
        self.glyphs = ASCII_GLYPHS if use_ascii else UNICODE_GLYPHS

    @classmethod
    def for_path(cls, root: Path, use_ascii: bool = False) -> ProjectTree:
        """Returns a GitProjectTree when the path lies inside a working git repository, otherwise a PlainProjectTree.

        Args:
            root: Path of the directory to render.
            use_ascii: Draws the branches with ASCII characters instead of box-drawing characters.
        """

        from fsg.trees.git_project_tree import GitProjectTree
        from fsg.trees.plain_project_tree import PlainProjectTree

        if GitProjectTree.is_repository(root):
            return GitProjectTree(root, use_ascii)
        return PlainProjectTree(root, use_ascii)

    def collect(self) -> list[list[str]]:
        """Returns the relative paths to render, as lists of path parts."""

        raise NotImplementedError

    def render(self) -> str:
        """Returns the tree as one string, wrapped in a Markdown code fence."""

        body = "\n".join([f"{self.root.name}/", *self._lines(self._nodes(), "")])
        return f"```plaintext\n{body}\n```"

    def _nodes(self) -> dict[str, dict]:
        """Turns the collected paths into nested dicts, dropping paths that contain an ignored part."""

        tree: dict[str, dict] = {}
        for parts in self.collect():
            if any(part in IGNORED for part in parts):
                continue
            current = tree
            for part in parts:
                current = current.setdefault(part, {})
        return tree

    def _lines(self, nodes: dict[str, dict], prefix: str) -> Iterator[str]:
        """Yields the rendered lines for one level of the node tree and recurses into its children.

        Args:
            nodes: Mapping of entry name to its child nodes.
            prefix: Indentation string carried over from the parent levels.
        """

        entries = sorted(nodes.items(), key=lambda item: (not item[1], item[0].lower()))
        for index, (name, children) in enumerate(entries):
            is_last = index == len(entries) - 1
            connector = self.glyphs["last"] if is_last else self.glyphs["branch"]
            yield f"{prefix}{connector}{name}{'/' if children else ''}"
            if children:
                yield from self._lines(children, prefix + (self.glyphs["space"] if is_last else self.glyphs["pipe"]))