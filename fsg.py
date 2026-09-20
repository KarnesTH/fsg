import subprocess
import sys
from pathlib import Path
from typing import Iterator

BRANCH = "├── "
LAST = "└── "
PIPE = "│   "
SPACE = "    "

IGNORED = {
    ".git", ".svn", ".hg",
    ".idea", ".vscode",
    "__pycache__", ".mypy_cache", ".pytest_cache", ".ruff_cache",
    ".venv", "venv", "env",
    "node_modules", "target", "dist", "build", "out",
    ".godot", ".import",
    ".DS_Store", "Thumbs.db",
    "uv.lock",
}


class ProjectTree:
    """Collects the relevant paths of a project directory and renders them as a tree."""

    def __init__(self, root: Path) -> None:
        """Resolves and stores the root directory of the project.

        Args:
            root: Path of the directory to render.
        """

        self.root = Path(root).resolve()

    @classmethod
    def for_path(cls, root: Path) -> "ProjectTree":
        """Returns a GitProjectTree when the path lies inside a working git repository, otherwise a PlainProjectTree.

        Args:
            root: Path of the directory to render.
        """

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

        tree = {}
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


class GitProjectTree(ProjectTree):
    """Collects the paths git reports as tracked or untracked but not ignored."""

    @staticmethod
    def is_repository(root: Path) -> bool:
        """Returns whether the given path lies inside the working tree of a git repository.

        Args:
            root: Path to check.
        """

        try:
            result = subprocess.run(
                ["git", "rev-parse", "--is-inside-work-tree"],
                cwd=root,
                capture_output=True,
                text=True,
            )
        except (FileNotFoundError, NotADirectoryError):
            return False
        return result.returncode == 0 and result.stdout.strip() == "true"

    def collect(self) -> list[list[str]]:
        """Returns the paths listed by git ls-files, split into their path parts."""

        result = subprocess.run(
            ["git", "ls-files", "--cached", "--others", "--exclude-standard", "-z"],
            cwd=self.root,
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            return []
        return [entry.split("/") for entry in result.stdout.split("\0") if entry]


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


def main(argv=None) -> int:
    """Renders the tree for the path given as the first argument, or the current directory."""

    arguments = sys.argv[1:] if argv is None else argv
    root = Path(arguments[0] if arguments else ".")
    if not root.is_dir():
        print(f"not a directory: {root}", file=sys.stderr)
        return 1
    print(ProjectTree.for_path(root).render())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())