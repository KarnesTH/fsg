import argparse
import io
import sys
from pathlib import Path

import fsg
from fsg.config import Config
from fsg.console import Console
from fsg.errors import FsgError, HookError, PathError
from fsg.git import Git
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
        version=f"%(prog)s {fsg.__version__}",
    )
    args = parser.parse_args(argv)
    if args.depth is not None and args.depth < 1:
        parser.error("--depth must be at least 1")
    return args


def main(argv: list[str] | None = None) -> int:
    """Runs the mode selected by the arguments, reports the result on the console and returns the exit status.

    Without a mode the tree is rendered from the arguments alone and written UTF-8 encoded to stdout.
    With --update or --check the config found from the directory of the target file fills in the path
    and every option not given. Returns 0 on success, 1 when --check finds an outdated tree, and 2 for
    every error.

    Args:
        argv: Argument list to use instead of the command line arguments.
    """

    args = parse_args(argv)
    for stream in (sys.stdout, sys.stderr):
        if isinstance(stream, io.TextIOWrapper):
            stream.reconfigure(encoding="utf-8")
    console = Console(use_ascii=bool(args.use_ascii))
    try:
        if args.setup_hook:
            return _setup_hook(console, args.setup_hook)
        return _render(console, args)
    except FsgError as error:
        console.error(error)
        return 2


def _render(console: Console, args: argparse.Namespace) -> int:
    """Renders the tree and prints it, or compares or writes it in the marked section of the target file.

    Args:
        console: Console the result is reported on.
        args: Parsed command line arguments.

    Raises:
        FsgError: The config, the directory, git or the target file fails.
    """

    target = args.update or args.check
    config = Config.find(target.resolve().parent) if target is not None else Config()
    root = args.path or config.path or Path(".")
    if not root.is_dir():
        raise PathError(f"{root}: not a directory", "pass an existing directory or set path in the config")
    output = ProjectTree.for_path(root, **config.merge(args)).render()
    if target is None:
        console.output(output)
        return 0
    section = ReadmeSection(target)
    if args.check:
        if section.is_current(output):
            console.success(f"{target}: tree is up to date")
            return 0
        console.failure(f"{target}: tree is out of date", f"run fsg --update {target}")
        return 1
    if section.update(output):
        console.success(f"{target}: tree updated")
    else:
        console.info(f"{target}: tree already up to date")
    return 0


def _setup_hook(console: Console, target: Path) -> int:
    """Adds the update step for the target to the hooks of the repository around the current directory and reports the result.

    The target must exist and hold both markers before a hook is written.

    Args:
        console: Console the result is reported on.
        target: File holding the markers, relative to the current directory.

    Raises:
        FsgError: The directory is not in a repository, the target is invalid or the hook cannot be written.
    """

    repository = Git(Path.cwd()).toplevel()
    if repository is None:
        raise HookError("not inside a git repository", "run fsg --setup-hook inside your project")
    ReadmeSection(target)
    root = repository.resolve()
    resolved = target.resolve()
    if not resolved.is_relative_to(root):
        raise HookError(f"{target}: not inside the repository {repository}")
    hook = Hook.for_repository(repository, resolved.relative_to(root).as_posix())
    location = hook.location()
    added = hook.install()
    location = location.resolve()
    shown = (location.relative_to(root) if location.is_relative_to(root) else location).as_posix()
    if not added:
        console.info(f"{shown}: fsg hook already present")
    elif isinstance(hook, GitHook):
        console.success(f"{shown}: fsg hook added")
    else:
        console.success(f"{shown}: fsg hook added", "run pre-commit install if not done yet")
    return 0