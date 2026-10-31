import argparse
import io
import sys
from importlib.metadata import version
from pathlib import Path

from fsg.trees import ProjectTree


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parses the command line arguments and returns the resulting namespace.

    Exits with status 2 when --depth is smaller than 1.

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
        "-d",
        "--depth",
        type=int,
        metavar="N",
        help="render only the first N levels below the root",
    )
    parser.add_argument(
        "--dirs-only",
        action="store_true",
        help="render directories only",
    )
    parser.add_argument(
        "-e",
        "--exclude",
        action="append",
        default=[],
        metavar="PATTERN",
        help="leave out entries whose name or relative path matches the glob pattern (repeatable)",
    )
    parser.add_argument(
        "--no-fence",
        action="store_false",
        dest="fence",
        help="print the tree without the surrounding Markdown code fence",
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
    args = parser.parse_args(argv)
    if args.depth is not None and args.depth < 1:
        parser.error("--depth must be at least 1")
    return args


def main(argv: list[str] | None = None) -> int:
    """Renders the tree for the parsed path and options and writes it UTF-8 encoded to stdout.

    Args:
        argv: Argument list to use instead of the command line arguments.
    """

    args = parse_args(argv)
    if not args.path.is_dir():
        print(f"not a directory: {args.path}", file=sys.stderr)
        return 1
    if isinstance(sys.stdout, io.TextIOWrapper):
        sys.stdout.reconfigure(encoding="utf-8")
    tree = ProjectTree.for_path(
        args.path,
        use_ascii=args.use_ascii,
        depth=args.depth,
        dirs_only=args.dirs_only,
        exclude=args.exclude,
        fence=args.fence,
    )
    print(tree.render())
    return 0