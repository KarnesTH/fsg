import sys
from pathlib import Path

from fsg.trees import ProjectTree


def main(argv: list[str] | None = None) -> int:
    """Renders the tree for the path given as the first argument, or the current directory.

    Args:
        argv: Argument list to use instead of the command line arguments.
    """

    arguments = sys.argv[1:] if argv is None else argv
    root = Path(arguments[0] if arguments else ".")
    if not root.is_dir():
        print(f"not a directory: {root}", file=sys.stderr)
        return 1
    print(ProjectTree.for_path(root).render())
    return 0