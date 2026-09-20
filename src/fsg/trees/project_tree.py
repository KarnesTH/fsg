from collections.abc import Iterator
from pathlib import Path

from fsg.constants import BRANCH, IGNORED, LAST, PIPE, SPACE


class ProjectTree:
    """Collects the relevant paths of a project directory and renders them as a tree."""

    def __init__(self, root: Path) -> None:
        """Resolves and stores the root directory of the project.

        Args:
            root: Path of the directory to render.
        """

        self.root = Path(root).resolve()

    @classmethod
    def for_path(cls, root: Path) -> ProjectTree:
        """Returns a GitProjectTree when the path lies inside a working git repository, otherwise a PlainProjectTree.

        Args:
            root: Path of the directory to render.
        """

        from fsg.trees.git_project_tree import GitProjectTree
        from fsg.trees.plain_project_tree import PlainProjectTree

        if GitProjectTree.is_repository(root):
            return GitProjectTree(root)
        return PlainProjectTree(root)

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
            yield f"{prefix}{LAST if is_last else BRANCH}{name}{'/' if children else ''}"
            if children:
                yield from self._lines(children, prefix + (SPACE if is_last else PIPE))