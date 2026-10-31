import argparse
import sys
from importlib.metadata import version
from pathlib import Path

from fsg.trees import ProjectTree


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parses the command line arguments and returns the resulting namespace.

    Args:
        argv: Argument list to parse instead of the command line arguments.
    """

    parser = argparse.ArgumentParser(
        prog="fsg",
        description="Prints a project structure as a tree for GitHub READMEs.",
    )
    parser.add_argument(
        "path",
        nargs="?",
        default=".",
        type=Path,
        help="project directory to render (default: the current directory)",
    )
    parser.add_argument(
        "-V",
        "--version",
        action="version",
        version=f"%(prog)s {version('fsg')}",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """Renders the tree for the parsed path and writes it to stdout.

    Args:
        argv: Argument list to use instead of the command line arguments.
    """

    args = parse_args(argv)
    if not args.path.is_dir():
        print(f"not a directory: {args.path}", file=sys.stderr)
        return 1
    print(ProjectTree.for_path(args.path).render())
    return 0