from __future__ import annotations

from collections.abc import Iterable, Iterator
from fnmatch import fnmatchcase
from pathlib import Path
from typing import Any

from fsg.constants import ASCII_GLYPHS, IGNORED, UNICODE_GLYPHS
from fsg.git import Git


class ProjectTree:
    """Collects the relevant paths of a project directory and renders them as a tree."""

    def __init__(
        self,
        root: Path,
        *,
        use_ascii: bool = False,
        depth: int | None = None,
        dirs_only: bool = False,
        exclude: Iterable[str] = (),
        fence: bool = True,
    ) -> None:
        """Resolves and stores the root directory of the project together with the render options.

        Args:
            root: Path of the directory to render.
            use_ascii: Draws the branches with ASCII characters instead of box-drawing characters.
            depth: Number of levels below the root to render, or None for all levels.
            dirs_only: Renders directories only and leaves out files.
            exclude: Glob patterns matched case-sensitively against every path part and every relative path prefix.
            fence: Wraps the rendered tree in a Markdown code fence.
        """

        self.root = Path(root).resolve()
        self.glyphs = ASCII_GLYPHS if use_ascii else UNICODE_GLYPHS
        self.depth = depth
        self.dirs_only = dirs_only
        self.exclude = tuple(exclude)
        self.fence = fence

    @classmethod
    def for_path(cls, root: Path, **options: Any) -> ProjectTree:
        """Returns a GitProjectTree when the path lies inside a working git repository, otherwise a PlainProjectTree.

        Args:
            root: Path of the directory to render.
            **options: Render options passed on to the constructor.
        """

        from fsg.trees.git_project_tree import GitProjectTree
        from fsg.trees.plain_project_tree import PlainProjectTree

        if Git(root).is_repository():
            return GitProjectTree(root, **options)
        return PlainProjectTree(root, **options)

    def collect(self) -> list[list[str]]:
        """Returns the relative paths to render, as lists of path parts."""

        raise NotImplementedError

    def render(self) -> str:
        """Returns the tree as one string, wrapped in a Markdown code fence unless fence is disabled."""

        body = "\n".join([f"{self.root.name}/", *self._lines(self._nodes(), "", 1)])
        return f"```plaintext\n{body}\n```" if self.fence else body

    def _nodes(self) -> dict[str, dict]:
        """Turns the collected paths into nested dicts, dropping paths that contain an ignored or excluded part."""

        tree: dict[str, dict] = {}
        for parts in self.collect():
            if any(part in IGNORED for part in parts) or self._is_excluded(parts):
                continue
            current = tree
            for part in parts:
                current = current.setdefault(part, {})
        return tree

    def _is_excluded(self, parts: list[str]) -> bool:
        """Returns whether any part name or any slash-joined prefix of the parts matches an exclude pattern.

        Args:
            parts: Path parts relative to the root.
        """

        for index, part in enumerate(parts):
            prefix = "/".join(parts[: index + 1])
            if any(fnmatchcase(part, pattern) or fnmatchcase(prefix, pattern) for pattern in self.exclude):
                return True
        return False

    def _lines(self, nodes: dict[str, dict], prefix: str, level: int) -> Iterator[str]:
        """Yields the rendered lines for one level of the node tree and recurses into its children up to the depth limit.

        Args:
            nodes: Mapping of entry name to its child nodes.
            prefix: Indentation string carried over from the parent levels.
            level: Level of the given nodes below the root, starting at 1.
        """

        entries = sorted(nodes.items(), key=lambda item: (not item[1], item[0].lower()))
        if self.dirs_only:
            entries = [entry for entry in entries if entry[1]]
        for index, (name, children) in enumerate(entries):
            is_last = index == len(entries) - 1
            connector = self.glyphs["last"] if is_last else self.glyphs["branch"]
            yield f"{prefix}{connector}{name}{'/' if children else ''}"
            if children and (self.depth is None or level < self.depth):
                indent = self.glyphs["space"] if is_last else self.glyphs["pipe"]
                yield from self._lines(children, prefix + indent, level + 1)