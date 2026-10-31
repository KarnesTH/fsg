import argparse
import io
import subprocess
import sys
from importlib.metadata import version
from pathlib import Path

from fsg.config import Config
from fsg.hooks import GitHook, Hook
from fsg.readme_section import ReadmeSection
from fsg.trees import ProjectTree


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parses the command line arguments and returns the resulting namespace.

    Boolean options are None when not given.
    Exits with status 2 when --depth is smaller than 1.

    Args:
        argv: Argument list to parse instead of the command line arguments.
    """

    parser = argparse.ArgumentParser(
        prog="fsg",
        description="Generates clean directory trees that respect .gitignore and keep your docs up to date.",
        epilog=(
            "With --update or --check, the path and options not given on the command line are read from "
            ".fsg.toml or [tool.fsg] in pyproject.toml, searched from the directory of FILE upwards."
        ),
    )
    parser.add_argument(
        "path",
        nargs="?",
        type=Path,
        help="project directory to render (default: the configured path or the current directory)",
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
        action=argparse.BooleanOptionalAction,
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
        "--fence",
        action=argparse.BooleanOptionalAction,
        help="wrap the tree in a Markdown code fence (default: on)",
    )
    parser.add_argument(
        "--ascii",
        action=argparse.BooleanOptionalAction,
        dest="use_ascii",
        help="draw the tree with ASCII characters instead of box-drawing characters",
    )
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "-u",
        "--update",
        type=Path,
        metavar="FILE",
        help="write the tree between the <!-- fsg:start --> and <!-- fsg:end --> markers of FILE",
    )
    mode.add_argument(
        "-c",
        "--check",
        type=Path,
        metavar="FILE",
        help="exit with status 1 when the tree between the markers of FILE is out of date",
    )
    mode.add_argument(
        "--setup-hook",
        type=Path,
        metavar="FILE",
        help="add 'fsg --update FILE' to .pre-commit-config.yaml if present, otherwise to the git pre-commit hook",
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
    """Runs the mode selected by the arguments and returns the exit status.

    Without a mode the tree is rendered from the arguments alone and written UTF-8 encoded to stdout.
    With --update or --check the config found from the directory of the target file fills in the path
    and every option not given. Returns 0 on success, 1 when the path is not a directory or --check finds
    an outdated tree, and 2 when a file cannot be read, lacks the markers, the config is invalid or the
    hook cannot be set up.

    Args:
        argv: Argument list to use instead of the command line arguments.
    """

    args = parse_args(argv)
    for stream in (sys.stdout, sys.stderr):
        if isinstance(stream, io.TextIOWrapper):
            stream.reconfigure(encoding="utf-8")
    if args.setup_hook:
        return _setup_hook(args.setup_hook)
    target = args.update or args.check
    config = Config()
    if target is not None:
        try:
            config = Config.find(target.resolve().parent)
        except (OSError, ValueError) as error:
            return _fail(str(error), 2)
    root = args.path or config.path or Path(".")
    if not root.is_dir():
        return _fail(f"{root}: not a directory", 1)
    output = ProjectTree.for_path(root, **config.merge(args)).render()
    if target is None:
        print(output)
        return 0
    return _sync(target, output, check=bool(args.check))


def _sync(target: Path, output: str, check: bool) -> int:
    """Compares or writes the tree in the marked section of the target and prints one status line.

    Args:
        target: File holding the markers.
        output: Rendered tree.
        check: Only compares when True, otherwise writes the tree.
    """

    try:
        section = ReadmeSection(target)
    except FileNotFoundError:
        return _fail(f"{target}: file not found", 2)
    except UnicodeDecodeError:
        return _fail(f"{target}: not a UTF-8 text file", 2)
    except (OSError, ValueError) as error:
        return _fail(f"{target}: {getattr(error, 'strerror', None) or error}", 2)
    if check:
        if section.is_current(output):
            print(f"{target}: tree is up to date")
            return 0
        print(f"{target}: tree is out of date, run fsg --update {target}", file=sys.stderr)
        return 1
    if section.update(output):
        print(f"{target}: tree updated")
    else:
        print(f"{target}: tree already up to date")
    return 0


def _setup_hook(target: Path) -> int:
    """Adds the update step for the target to the hooks of the repository around the current directory and prints the result.

    Args:
        target: File holding the markers, relative to the current directory.
    """

    repository = Hook.repository_root(Path.cwd())
    if repository is None:
        return _fail("not inside a git repository", 2)
    try:
        relative = target.resolve().relative_to(repository.resolve()).as_posix()
    except ValueError:
        return _fail(f"{target}: not inside the repository {repository}", 2)
    hook = Hook.for_repository(repository, relative)
    try:
        location = hook.location()
        added = hook.install()
    except (OSError, ValueError, subprocess.CalledProcessError) as error:
        return _fail(str(error), 2)
    root = repository.resolve()
    location = location.resolve()
    shown = location.relative_to(root) if location.is_relative_to(root) else location
    if not added:
        print(f"{shown}: fsg hook already present")
    elif isinstance(hook, GitHook):
        print(f"{shown}: fsg hook added")
    else:
        print(f"{shown}: fsg hook added, run 'pre-commit install' if not done yet")
    return 0


def _fail(message: str, status: int) -> int:
    """Prints the message prefixed with fsg: to stderr and returns the status.

    Args:
        message: Error description.
        status: Exit status to return.
    """

    print(f"fsg: {message}", file=sys.stderr)
    return status