from __future__ import annotations

import argparse
import tomllib
from pathlib import Path
from typing import Any

from fsg.errors import ConfigError
from fsg.git import Git

CONFIG_FILE = ".fsg.toml"
PYPROJECT_FILE = "pyproject.toml"


class Config:
    """Holds the render options read from a .fsg.toml file or the [tool.fsg] table of a pyproject.toml."""

    def __init__(self, values: dict[str, Any] | None = None, source: Path | None = None) -> None:
        """Validates and stores the option values together with the file they were read from.

        Args:
            values: Option table with the keys path, depth, dirs-only, exclude, fence and ascii.
            source: File the values were read from, or None when no config file was found.

        Raises:
            ConfigError: A key is unknown or a value has the wrong type.
        """

        self.source = source
        self.path: Path | None = None
        self.depth: int | None = None
        self.dirs_only: bool | None = None
        self.exclude: list[str] = []
        self.fence: bool | None = None
        self.use_ascii: bool | None = None
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

    def merge(self, args: argparse.Namespace) -> dict[str, Any]:
        """Returns the ProjectTree options, taking each value from the arguments when given, else from the config, else the default.

        Exclude patterns from the config and the arguments are combined.

        Args:
            args: Parsed command line arguments holding depth, dirs_only, exclude, fence and use_ascii.
        """

        return {
            "depth": args.depth if args.depth is not None else self.depth,
            "dirs_only": self._pick(args.dirs_only, self.dirs_only, False),
            "exclude": [*self.exclude, *args.exclude],
            "fence": self._pick(args.fence, self.fence, True),
            "use_ascii": self._pick(args.use_ascii, self.use_ascii, False),
        }

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
        elif key in ("dirs-only", "fence", "ascii"):
            if not isinstance(value, bool):
                raise ConfigError(f"{self.source}: {key} must be true or false")
            setattr(self, {"dirs-only": "dirs_only", "ascii": "use_ascii"}.get(key, key), value)
        elif key == "exclude":
            if not isinstance(value, list) or not all(isinstance(pattern, str) for pattern in value):
                raise ConfigError(f"{self.source}: exclude must be a list of strings")
            self.exclude = list(value)
        else:
            raise ConfigError(f"{self.source}: unknown option '{key}'")