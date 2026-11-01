import argparse
import io
import sys
import webbrowser
from pathlib import Path

import fsg
from fsg.clipboard import Clipboard
from fsg.config import Config
from fsg.console import Console
from fsg.constants import DOCS_URL, STYLES
from fsg.errors import FsgError, HookError, PathError
from fsg.git import Git
from fsg.hooks import GitHook, Hook
from fsg.marked_file import MarkedFile
from fsg.tree_comments import TreeComments
from fsg.trees import ProjectTree


class DocsAction(argparse.Action):
    """Opens the documentation in the browser and exits, like the version action."""

    def __init__(self, option_strings: list[str], dest: str, help: str | None = None) -> None:
        """Registers the option without a value.

        Args:
            option_strings: Option names, e.g. ["--docs"].
            dest: Attribute name, unused because the action exits.
            help: Help text of the option.
        """

        super().__init__(option_strings, dest, nargs=0, default=argparse.SUPPRESS, help=help)

    def __call__(self, parser: argparse.ArgumentParser, namespace: argparse.Namespace, values: object, option_string: str | None = None) -> None:
        """Opens the documentation URL and exits with status 0.

        Args:
            parser: Parser the action belongs to.
            namespace: Namespace parsed so far.
            values: Empty, the option takes no value.
            option_string: Option name used on the command line.
        """

        _open_docs(Console())
        parser.exit()


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parses the command line arguments and returns the resulting namespace.

    Boolean options are None when not given.
    Exits with status 2 when --depth is smaller than 1 or --copy is combined with a mode.

    Args:
        argv: Argument list to parse instead of the command line arguments.
    """

    parser = argparse.ArgumentParser(
        prog="fsg",
        description="Generates clean directory trees that respect .gitignore and keep your docs up to date.",
        epilog=(
            "With --update or --check, the path and options not given on the command line are read from the start "
            "marker of each block, then from .fsg.toml or [tool.fsg] in pyproject.toml, searched from the directory "
            "of FILE upwards."
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
        "-i",
        "--include",
        action="append",
        default=[],
        metavar="PATTERN",
        help="show only entries whose name or relative path matches the glob pattern (repeatable, exclude wins)",
    )
    parser.add_argument(
        "--fence",
        action=argparse.BooleanOptionalAction,
        help="wrap the tree in a Markdown code fence (default: on)",
    )
    parser.add_argument(
        "--summary",
        action=argparse.BooleanOptionalAction,
        help="add a line with the number of directories and files (default: off)",
    )
    parser.add_argument(
        "-s",
        "--style",
        choices=list(STYLES),
        help="draw the tree in a built-in style (default: unicode)",
    )
    parser.add_argument(
        "--glyph",
        action="append",
        default=[],
        metavar="KEY=VALUE",
        help="replace one glyph of the style: branch, last, pipe or space (repeatable)",
    )
    parser.add_argument(
        "--ascii",
        action=argparse.BooleanOptionalAction,
        dest="use_ascii",
        help="short for --style ascii; also uses ASCII status symbols",
    )
    parser.add_argument(
        "--copy",
        action="store_true",
        help="copy the tree to the clipboard instead of printing it",
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
    parser.add_argument(
        "--docs",
        action=DocsAction,
        help="open the documentation in the browser and exit",
    )
    args = parser.parse_args(argv)
    if args.depth is not None and args.depth < 1:
        parser.error("--depth must be at least 1")
    if args.copy and (args.update or args.check or args.setup_hook):
        parser.error("--copy cannot be combined with --update, --check or --setup-hook")
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

    for stream in (sys.stdout, sys.stderr):
        if isinstance(stream, io.TextIOWrapper):
            stream.reconfigure(encoding="utf-8")
    args = parse_args(argv)
    console = Console(use_ascii=bool(args.use_ascii) or args.style == "ascii")
    try:
        if args.setup_hook:
            return _setup_hook(console, args.setup_hook)
        return _render(console, args)
    except FsgError as error:
        console.error(error)
        return 2


def _render(console: Console, args: argparse.Namespace) -> int:
    """Renders the tree and prints or copies it, or compares or writes the trees of every marked block of the target file.

    Args:
        console: Console the result is reported on.
        args: Parsed command line arguments.

    Raises:
        FsgError: The config, a directory, git, the clipboard or the target file fails.
    """

    target = args.update or args.check
    if target is None:
        output = _tree(Config(), args).render()
        if args.copy:
            Clipboard().copy(output)
            console.success("tree copied to clipboard")
        else:
            console.output(output)
        return 0
    marked = MarkedFile(target)
    config = Config.find(target.resolve().parent)
    trees = []
    for index, section in enumerate(marked.sections):
        tree = _tree(config.with_marker(section.options, target, section.line), args)
        comments = TreeComments(tree.glyphs.characters()).parse(marked.content(index))
        trees.append(tree.render(comments))
    count = len(trees)
    noun = "tree" if count == 1 else f"{count} trees"
    if args.check:
        outdated = sum(1 for index, tree in enumerate(trees) if not marked.is_current(tree, index))
        if not outdated:
            console.success(f"{target}: {noun} {'is' if count == 1 else 'are'} up to date")
            return 0
        detail = "tree is" if count == 1 else f"{outdated} of {count} trees are"
        console.failure(f"{target}: {detail} out of date", f"run fsg --update {target}")
        return 1
    changed = marked.update(trees)
    if changed:
        console.success(f"{target}: {'tree' if count == 1 else f'{changed} of {count} trees'} updated")
    else:
        console.info(f"{target}: {noun} already up to date")
    return 0


def _tree(config: Config, args: argparse.Namespace) -> ProjectTree:
    """Returns the tree for the directory and options chosen by the arguments, falling back to the config.

    Args:
        config: Config, possibly with marker options applied.
        args: Parsed command line arguments.

    Raises:
        FsgError: The directory does not exist or the options are invalid.
    """

    root = args.path or config.path or Path(".")
    if not root.is_dir():
        raise PathError(f"{root}: not a directory", "pass an existing directory or set path in the config or marker")
    return ProjectTree.for_path(root, **config.merge(args))


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
    MarkedFile(target)
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


def _open_docs(console: Console) -> None:
    """Opens the documentation URL in the default browser and prints it, with a hint when no browser is available.

    Args:
        console: Console the URL is reported on.
    """

    try:
        opened = webbrowser.open(DOCS_URL)
    except webbrowser.Error:
        opened = False
    if opened:
        console.info(f"opening {DOCS_URL}")
    else:
        console.info(DOCS_URL, "no browser found, open the link manually")