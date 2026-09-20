from collections.abc import Iterator
from pathlib import Path

from fsg.constants import IGNORED
from fsg.trees.project_tree import ProjectTree


class PlainProjectTree(ProjectTree):
    """Collects the paths by walking the directory, skipping well-known generated entries."""

    def collect(self) -> list[list[str]]:
        """Returns the paths found below the root, split into their path parts."""

        return list(self._walk(self.root, []))

    def _walk(self, directory: Path, parts: list[str]) -> Iterator[list[str]]:
        """Yields the path parts of every entry below a directory, recursing into subdirectories.

        Args:
            directory: Directory to list.
            parts: Path parts of that directory relative to the root.
        """

        try:
            children = list(directory.iterdir())
        except OSError:
            return
        for child in sorted(children, key=lambda path: path.name.lower()):
            if child.name in IGNORED:
                continue
            if child.is_dir() and not child.is_symlink():
                yield from self._walk(child, parts + [child.name])
            else:
                yield parts + [child.name]