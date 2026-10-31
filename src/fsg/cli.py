import argparse
import io
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
        description="Generates clean directory trees that respect .gitignore and keep your docs up to date.",
    )
    parser.add_argument(
        "path",
        nargs="?",
        default=".",
        type=Path,
        help="project directory to render (default: the current directory)",
    )
    parser.add_argument(
        "--ascii",
        action="store_true",
        dest="use_ascii",
        help="draw the tree with ASCII characters instead of box-drawing characters",
    )
    parser.add_argument(
        "-V",
        "--version",
        action="version",
        version=f"%(prog)s {version('fsg')}",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """Renders the tree for the parsed path and writes it UTF-8 encoded to stdout.

    Args:
        argv: Argument list to use instead of the command line arguments.
    """

    args = parse_args(argv)
    if not args.path.is_dir():
        print(f"not a directory: {args.path}", file=sys.stderr)
        return 1
    if isinstance(sys.stdout, io.TextIOWrapper):
        sys.stdout.reconfigure(encoding="utf-8")
    print(ProjectTree.for_path(args.path, args.use_ascii).render())
    return 0