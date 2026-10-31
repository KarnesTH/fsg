from pathlib import Path

from fsg.constants import IGNORED
from fsg.trees.project_tree import ProjectTree


class PlainProjectTree(ProjectTree):
    """Collects the paths by walking the directory, skipping well-known generated entries."""

    def collect(self) -> list[list[str]]:
        """Returns the paths found below the root, split into their path parts.

        Walks the directories with an explicit stack and does not follow directory symlinks. Directories matching
        an exclude pattern are not entered. A directory on the last rendered level is not walked further; only the
        first file below it that passes the filters is collected, so it still renders as directory.
        """

        paths: list[list[str]] = []
        stack: list[tuple[Path, list[str]]] = [(self.root, [])]
        while stack:
            directory, parts = stack.pop()
            for child in self._children(directory):
                child_parts = parts + [child.name]
                if not self._is_directory(child):
                    paths.append(child_parts)
                elif self._matches(child_parts, self.exclude):
                    continue
                elif self.depth is not None and len(child_parts) >= self.depth:
                    first = self._first_file(child, child_parts)
                    if first is not None:
                        paths.append(first)
                else:
                    stack.append((child, child_parts))
        return paths

    def _first_file(self, directory: Path, parts: list[str]) -> list[str] | None:
        """Returns the path parts of the first file below the directory that passes the filters, or None.

        Args:
            directory: Directory to search.
            parts: Path parts of that directory relative to the root.
        """

        stack: list[tuple[Path, list[str]]] = [(directory, parts)]
        while stack:
            current, current_parts = stack.pop()
            for child in self._children(current):
                child_parts = current_parts + [child.name]
                if self._is_directory(child):
                    if not self._matches(child_parts, self.exclude):
                        stack.append((child, child_parts))
                elif self._accepts(child_parts):
                    return child_parts
        return None

    @staticmethod
    def _children(directory: Path) -> list[Path]:
        """Returns the entries of the directory that are not in IGNORED, or an empty list when it cannot be read.

        Args:
            directory: Directory to list.
        """

        try:
            return [child for child in directory.iterdir() if child.name not in IGNORED]
        except OSError:
            return []

    @staticmethod
    def _is_directory(path: Path) -> bool:
        """Returns whether the path is a directory that is not a symlink.

        Args:
            path: Path to check.
        """

        return path.is_dir() and not path.is_symlink()