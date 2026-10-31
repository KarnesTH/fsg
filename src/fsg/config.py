from __future__ import annotations

import argparse
import copy
import tomllib
from pathlib import Path
from typing import Any

from fsg.errors import ConfigError
from fsg.git import Git
from fsg.glyphs import KEYS, Glyphs

CONFIG_FILE = ".fsg.toml"
PYPROJECT_FILE = "pyproject.toml"


class Config:
    """Holds the render options read from a .fsg.toml file or the [tool.fsg] table of a pyproject.toml."""

    def __init__(self, values: dict[str, Any] | None = None, source: Path | None = None) -> None:
        """Validates and stores the option values together with the file they were read from.

        Args:
            values: Option table with the keys path, depth, dirs-only, exclude, include, fence, ascii, style,
                glyphs and summary.
            source: File the values were read from, or None when no config file was found.

        Raises:
            ConfigError: A key is unknown or a value has the wrong type.
        """

        self.source = source
        self.path: Path | None = None
        self.depth: int | None = None
        self.dirs_only: bool | None = None
        self.exclude: list[str] = []
        self.include: list[str] = []
        self.fence: bool | None = None
        self.use_ascii: bool | None = None
        self.style: str | None = None
        self.glyphs: dict[str, str] = {}
        self.summary: bool | None = None
        for key, value in (values or {}).items():
            self._set(key, value)

    @classmethod
    def find(cls, start: Path) -> Config:
        """Searches the start directory and its parents for a .fsg.toml or a pyproject.toml with a [tool.fsg] table.

        The search stops at the root of the git working tree; outside a repository it stops at the home directory,
        or after the start directory when that lies outside the home directory. The first directory containing
        either file wins; inside one directory .fsg.toml takes precedence. Returns an empty Config when nothing is found.

        Args:
            start: Directory the search begins in.

        Raises:
            ConfigError: A config file cannot be read, is not valid TOML or holds invalid options.
        """

        start = Path(start).resolve()
        for directory in cls._search_path(start):
            config_file = directory / CONFIG_FILE
            if config_file.is_file():
                return cls(cls._load(config_file), config_file)
            pyproject = directory / PYPROJECT_FILE
            if pyproject.is_file():
                table = cls._load(pyproject).get("tool", {}).get("fsg")
                if table is not None:
                    return cls(table, pyproject)
        return cls()

    @staticmethod
    def _search_path(start: Path) -> list[Path]:
        """Returns the start directory and its parents up to and including the search boundary.

        Args:
            start: Resolved directory the search begins in.
        """

        boundary = Git(start).toplevel()
        if boundary is None:
            try:
                home = Path.home().resolve()
            except RuntimeError:
                home = start
            boundary = home if start.is_relative_to(home) else start
        boundary = boundary.resolve()
        directories = [start]
        for parent in start.parents:
            if not directories[-1].is_relative_to(boundary) or directories[-1] == boundary:
                break
            directories.append(parent)
        return directories

    def with_marker(self, options: dict[str, str], file: Path, line: int) -> Config:
        """Returns a copy of the config with the options of a start marker applied on top.

        Values are given as strings: depth as number, switches as true or false, exclude and include as
        comma-separated patterns that are added to the configured ones. A path is resolved against the directory
        of the file and must stay inside its git working tree, or inside that directory outside a repository.

        Args:
            options: Marker options as key-value strings.
            file: File holding the marker.
            line: Line number of the start marker.

        Raises:
            ConfigError: An option is unknown, has an invalid value or the path leaves the allowed directory.
        """

        location = f"{file}:{line}"
        config = copy.copy(self)
        config.exclude = list(self.exclude)
        config.include = list(self.include)
        config.glyphs = dict(self.glyphs)
        for key, value in options.items():
            if key == "path":
                base = file.resolve().parent
                boundary = (Git(base).toplevel() or base).resolve()
                path = (base / value).resolve()
                if not path.is_relative_to(boundary):
                    raise ConfigError(f"{location}: path must stay inside {boundary}", "use a path inside the project")
                config.path = path
            elif key == "depth":
                if not value.isdigit() or int(value) < 1:
                    raise ConfigError(f"{location}: depth must be an integer of at least 1")
                config.depth = int(value)
            elif key in ("dirs-only", "fence", "summary"):
                if value.lower() not in ("true", "false"):
                    raise ConfigError(f"{location}: {key} must be true or false")
                setattr(config, key.replace("-", "_"), value.lower() == "true")
            elif key in ("exclude", "include"):
                getattr(config, key).extend(pattern.strip() for pattern in value.split(",") if pattern.strip())
            elif key == "style":
                config.style = value
            else:
                raise ConfigError(
                    f"{location}: unknown marker option '{key}'",
                    "use path, depth, dirs-only, exclude, include, fence, style or summary",
                )
        return config

    def merge(self, args: argparse.Namespace) -> dict[str, Any]:
        """Returns the ProjectTree options, taking each value from the arguments when given, else from the config, else the default.

        Exclude and include patterns from the config and the arguments are combined. The style comes from --style,
        then --ascii/--no-ascii, then the configured style or ascii switch, defaulting to unicode; glyph overrides
        from --glyph replace those from the config.

        Args:
            args: Parsed command line arguments holding depth, dirs_only, exclude, include, fence, use_ascii, style,
                glyph and summary.

        Raises:
            ConfigError: The style, a glyph override or the resulting glyph widths are invalid.
        """

        return {
            "depth": args.depth if args.depth is not None else self.depth,
            "dirs_only": self._pick(args.dirs_only, self.dirs_only, False),
            "exclude": [*self.exclude, *args.exclude],
            "include": [*self.include, *args.include],
            "fence": self._pick(args.fence, self.fence, True),
            "summary": self._pick(args.summary, self.summary, False),
            "glyphs": Glyphs.from_style(self.resolve_style(args), {**self.glyphs, **self._glyph_arguments(args.glyph)}),
        }

    def resolve_style(self, args: argparse.Namespace) -> str:
        """Returns the style name chosen by --style, --ascii/--no-ascii, the configured style or ascii switch, or unicode.

        Args:
            args: Parsed command line arguments holding style and use_ascii.
        """

        if args.style:
            return args.style
        if args.use_ascii is not None:
            return "ascii" if args.use_ascii else "unicode"
        if self.style:
            return self.style
        return "ascii" if self.use_ascii else "unicode"

    @staticmethod
    def _glyph_arguments(values: list[str]) -> dict[str, str]:
        """Returns the --glyph arguments as mapping of glyph key to string.

        Args:
            values: Arguments in the form key=value.

        Raises:
            ConfigError: An argument has no equals sign.
        """

        glyphs = {}
        for value in values:
            key, separator, glyph = value.partition("=")
            if not separator:
                raise ConfigError(f"--glyph {value}: expected key=value", 'e.g. --glyph branch="+-- "')
            glyphs[key.strip()] = glyph
        return glyphs

    @staticmethod
    def _pick(argument: bool | None, configured: bool | None, default: bool) -> bool:
        """Returns the argument value when set, otherwise the configured value when set, otherwise the default.

        Args:
            argument: Value from the command line, or None.
            configured: Value from the config file, or None.
            default: Value used when neither is set.
        """

        if argument is not None:
            return argument
        if configured is not None:
            return configured
        return default

    @staticmethod
    def _load(path: Path) -> dict[str, Any]:
        """Parses a TOML file and returns its top-level table.

        Args:
            path: File to parse.

        Raises:
            ConfigError: The file cannot be read or is not valid TOML.
        """

        try:
            with path.open("rb") as file:
                return tomllib.load(file)
        except tomllib.TOMLDecodeError as error:
            raise ConfigError(f"{path}: invalid TOML: {error}") from None
        except OSError as error:
            raise ConfigError(f"{path}: {error.strerror or error}") from None

    def _set(self, key: str, value: Any) -> None:
        """Checks the type of one option value and stores it on the matching attribute.

        A path is resolved against the directory of the config file and must not leave it.

        Args:
            key: Option name as written in the config file.
            value: Parsed TOML value.

        Raises:
            ConfigError: The key is unknown or the value has the wrong type.
        """

        if key == "path":
            if not isinstance(value, str):
                raise ConfigError(f"{self.source}: path must be a string")
            if self.source is None:
                self.path = Path(value)
                return
            base = self.source.parent.resolve()
            path = (base / value).resolve()
            if not path.is_relative_to(base):
                raise ConfigError(f"{self.source}: path must stay inside {base}", "use a path relative to the config file without ..")
            self.path = path
        elif key == "depth":
            if not isinstance(value, int) or isinstance(value, bool) or value < 1:
                raise ConfigError(f"{self.source}: depth must be an integer of at least 1")
            self.depth = value
        elif key in ("dirs-only", "fence", "ascii", "summary"):
            if not isinstance(value, bool):
                raise ConfigError(f"{self.source}: {key} must be true or false")
            setattr(self, {"dirs-only": "dirs_only", "ascii": "use_ascii"}.get(key, key), value)
        elif key == "style":
            if not isinstance(value, str):
                raise ConfigError(f"{self.source}: style must be a string")
            self.style = value
        elif key == "glyphs":
            if not isinstance(value, dict) or not all(isinstance(glyph, str) for glyph in value.values()):
                raise ConfigError(f"{self.source}: glyphs must be a table of strings")
            unknown = set(value) - set(KEYS)
            if unknown:
                raise ConfigError(f"{self.source}: unknown glyph '{min(unknown)}'", f"use one of: {', '.join(KEYS)}")
            self.glyphs = dict(value)
        elif key in ("exclude", "include"):
            if not isinstance(value, list) or not all(isinstance(pattern, str) for pattern in value):
                raise ConfigError(f"{self.source}: {key} must be a list of strings")
            setattr(self, key, list(value))
        else:
            raise ConfigError(f"{self.source}: unknown option '{key}'")