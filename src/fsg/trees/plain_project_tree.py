from pathlib import Path

from fsg.constants import IGNORED
from fsg.trees.project_tree import ProjectTree


class PlainProjectTree(ProjectTree):
    """Collects the paths by walking the directory, skipping well-known generated entries."""

    def collect(self) -> list[list[str]]:
        """Returns the paths found below the root, split into their path parts.

        Walks the directories with an explicit stack, skips unreadable directories and does not follow directory symlinks.
        """

        paths: list[list[str]] = []
        stack: list[tuple[Path, list[str]]] = [(self.root, [])]
        while stack:
            directory, parts = stack.pop()
            try:
                children = list(directory.iterdir())
            except OSError:
                continue
            for child in children:
                if child.name in IGNORED:
                    continue
                if child.is_dir() and not child.is_symlink():
                    stack.append((child, parts + [child.name]))
                else:
                    paths.append(parts + [child.name])
        return paths