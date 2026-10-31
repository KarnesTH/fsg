from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Iterable, Iterator
from fnmatch import fnmatchcase
from pathlib import Path
from typing import Any

from fsg.constants import IGNORED
from fsg.git import Git
from fsg.glyphs import Glyphs


class ProjectTree(ABC):
    """Collects the relevant paths of a project directory and renders them as a tree."""

    def __init__(
        self,
        root: Path,
        *,
        glyphs: Glyphs | None = None,
        depth: int | None = None,
        dirs_only: bool = False,
        exclude: Iterable[str] = (),
        include: Iterable[str] = (),
        fence: bool = True,
        summary: bool = False,
    ) -> None:
        """Resolves and stores the root directory of the project together with the render options.

        Args:
            root: Path of the directory to render.
            glyphs: Strings the branches are drawn with, defaults to the unicode style.
            depth: Number of levels below the root to render, or None for all levels.
            dirs_only: Renders directories only and leaves out files.
            exclude: Glob patterns matched case-sensitively against every path part and every relative path prefix.
            include: Glob patterns matched like exclude; when given, only paths matching one of them are kept.
            fence: Wraps the rendered tree in a Markdown code fence.
            summary: Appends a line with the number of rendered directories and files.
        """

        self.root = Path(root).resolve()
        self.glyphs = glyphs or Glyphs.from_style()
        self.depth = depth
        self.dirs_only = dirs_only
        self.exclude = tuple(exclude)
        self.include = tuple(include)
        self.fence = fence
        self.summary = summary

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

    @abstractmethod
    def collect(self) -> list[list[str]]:
        """Returns the relative paths to render, as lists of path parts."""

    def render(self, comments: dict[str, str] | None = None) -> str:
        """Returns the tree as one string, wrapped in a Markdown code fence unless fence is disabled.

        Comments are appended as "# comment" to the lines of their relative path, "" being the root line, and
        aligned two columns after the longest commented line. With summary, a line counting the rendered
        directories and files follows the tree.

        Args:
            comments: Mapping of relative path, using forward slashes, to comment text.
        """

        entries = [(f"{self.root.name}/", "", True), *self._lines(self._nodes(), "", 1, [])]
        comments = comments or {}
        commented = [Glyphs.width(text) for text, path, _ in entries if path in comments]
        column = max(commented, default=0) + 2
        lines = []
        for text, path, _ in entries:
            if path in comments:
                text = f"{text}{' ' * (column - Glyphs.width(text))}# {comments[path]}"
            lines.append(text)
        if self.summary:
            directories = sum(1 for _, path, is_directory in entries if is_directory and path)
            files = sum(1 for _, _, is_directory in entries if not is_directory)
            lines.extend(["", self._count(directories, "directory", "directories") + ", " + self._count(files, "file", "files")])
        body = "\n".join(lines)
        return f"```plaintext\n{body}\n```" if self.fence else body

    @staticmethod
    def _count(number: int, singular: str, plural: str) -> str:
        """Returns the number followed by the singular or plural noun.

        Args:
            number: Amount to show.
            singular: Noun used for exactly one.
            plural: Noun used for every other amount.
        """

        return f"{number} {singular if number == 1 else plural}"

    def _nodes(self) -> dict[str, dict]:
        """Turns the collected paths into nested dicts, keeping only the paths accepted by the filters."""

        tree: dict[str, dict] = {}
        for parts in self.collect():
            if not self._accepts(parts):
                continue
            current = tree
            for part in parts:
                current = current.setdefault(part, {})
        return tree

    def _accepts(self, parts: list[str]) -> bool:
        """Returns whether a file path passes the filters.

        A path is dropped when a part is in IGNORED or the path matches an exclude pattern. With include patterns,
        it is kept only when it matches one of them; with dirs_only, only the directory parts are matched against
        the include patterns.

        Args:
            parts: Path parts of a file relative to the root.
        """

        if any(part in IGNORED for part in parts) or self._matches(parts, self.exclude):
            return False
        if not self.include:
            return True
        return self._matches(parts[:-1] if self.dirs_only else parts, self.include)

    @staticmethod
    def _matches(parts: list[str], patterns: tuple[str, ...]) -> bool:
        """Returns whether any part name or any slash-joined prefix of the parts matches one of the patterns.

        Args:
            parts: Path parts relative to the root.
            patterns: Glob patterns, matched case-sensitively.
        """

        for index, part in enumerate(parts):
            prefix = "/".join(parts[: index + 1])
            if any(fnmatchcase(part, pattern) or fnmatchcase(prefix, pattern) for pattern in patterns):
                return True
        return False

    def _lines(self, nodes: dict[str, dict], prefix: str, level: int, parents: list[str]) -> Iterator[tuple[str, str, bool]]:
        """Yields the line text, relative path and directory flag for one level of the node tree, recursing up to the depth limit.

        Args:
            nodes: Mapping of entry name to its child nodes.
            prefix: Indentation string carried over from the parent levels.
            level: Level of the given nodes below the root, starting at 1.
            parents: Names of the directories leading to this level.
        """

        entries = sorted(nodes.items(), key=lambda item: (not item[1], item[0].lower()))
        if self.dirs_only:
            entries = [entry for entry in entries if entry[1]]
        for index, (name, children) in enumerate(entries):
            is_last = index == len(entries) - 1
            connector = self.glyphs.last if is_last else self.glyphs.branch
            path = "/".join([*parents, name])
            yield f"{prefix}{connector}{name}{'/' if children else ''}", path, bool(children)
            if children and (self.depth is None or level < self.depth):
                indent = self.glyphs.space if is_last else self.glyphs.pipe
                yield from self._lines(children, prefix + indent, level + 1, [*parents, name])