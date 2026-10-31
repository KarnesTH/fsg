import argparse
from pathlib import Path

import pytest

from fsg.config import Config
from fsg.errors import ConfigError
from tests.conftest import init_repository, requires_git


def namespace(**overrides: object) -> argparse.Namespace:
    """Returns parsed arguments with every config-backed option unset, updated with the given values.

    Args:
        **overrides: Attribute values replacing the defaults.
    """

    values = {"depth": None, "dirs_only": None, "exclude": [], "include": [], "fence": None, "use_ascii": None}
    values.update(overrides)
    return argparse.Namespace(**values)


class TestInit:
    """Covers validating the option values."""

    def test_reads_all_options(self) -> None:
        """Stores every supported option on its attribute."""

        config = Config({"depth": 2, "dirs-only": True, "exclude": ["*.log"], "fence": False, "ascii": True})
        assert (config.depth, config.dirs_only, config.exclude, config.fence, config.use_ascii) == (
            2, True, ["*.log"], False, True,
        )

    def test_resolves_path_against_source(self, tmp_path: Path) -> None:
        """Stores the path relative to the directory of the config file."""

        assert Config({"path": "src"}, tmp_path / ".fsg.toml").path == (tmp_path / "src").resolve()

    @pytest.mark.parametrize("path", ["..", "../other", "/", "src/../../x"])
    def test_rejects_path_outside_config_directory(self, tmp_path: Path, path: str) -> None:
        """Raises ValueError when the path leaves the directory of the config file."""

        with pytest.raises(ConfigError, match="must stay inside"):
            Config({"path": path}, tmp_path / "project" / ".fsg.toml")

    def test_accepts_config_directory_itself(self, tmp_path: Path) -> None:
        """Accepts . as the directory of the config file."""

        assert Config({"path": "."}, tmp_path / ".fsg.toml").path == tmp_path.resolve()

    def test_keeps_path_without_source(self) -> None:
        """Stores the path as given when the values come from no file."""

        assert Config({"path": "src"}).path == Path("src")

    def test_rejects_non_string_path(self) -> None:
        """Raises ValueError when path is not a string."""

        with pytest.raises(ConfigError, match="path"):
            Config({"path": 1})

    def test_leaves_unset_options_empty(self) -> None:
        """Keeps None and an empty exclude list when no values are given."""

        config = Config()
        assert config.path is None
        assert (config.depth, config.dirs_only, config.exclude, config.fence, config.use_ascii) == (
            None, None, [], None, None,
        )

    @pytest.mark.parametrize("depth", [0, -1, "2", True, 1.5])
    def test_rejects_invalid_depth(self, depth: object) -> None:
        """Raises ValueError for a depth that is not an integer of at least 1."""

        with pytest.raises(ConfigError, match="depth"):
            Config({"depth": depth})

    @pytest.mark.parametrize("key", ["dirs-only", "fence", "ascii"])
    def test_rejects_non_boolean_switch(self, key: str) -> None:
        """Raises ValueError when a switch is not true or false."""

        with pytest.raises(ConfigError, match=key):
            Config({key: "yes"})

    @pytest.mark.parametrize("exclude", ["*.log", [1, 2], ["*.log", None]])
    def test_rejects_invalid_exclude(self, exclude: object) -> None:
        """Raises ValueError when exclude is not a list of strings."""

        with pytest.raises(ConfigError, match="exclude"):
            Config({"exclude": exclude})

    def test_rejects_unknown_option(self) -> None:
        """Raises ValueError naming the unknown key."""

        with pytest.raises(ConfigError, match="unknown option 'dirs_only'"):
            Config({"dirs_only": True})

    def test_names_source_in_errors(self, tmp_path: Path) -> None:
        """Mentions the config file in the error message."""

        with pytest.raises(ConfigError, match="pyproject.toml"):
            Config({"depth": 0}, tmp_path / "pyproject.toml")


class TestFind:
    """Covers locating the config file."""

    def test_reads_fsg_toml(self, tmp_path: Path) -> None:
        """Reads the top-level options of .fsg.toml."""

        (tmp_path / ".fsg.toml").write_text("depth = 3\n", encoding="utf-8")
        config = Config.find(tmp_path)
        assert config.depth == 3
        assert config.source == tmp_path / ".fsg.toml"

    def test_reads_pyproject_table(self, tmp_path: Path) -> None:
        """Reads the [tool.fsg] table of pyproject.toml."""

        (tmp_path / "pyproject.toml").write_text('[project]\nname = "x"\n\n[tool.fsg]\ndepth = 2\n', encoding="utf-8")
        assert Config.find(tmp_path).depth == 2

    def test_prefers_fsg_toml_over_pyproject(self, tmp_path: Path) -> None:
        """Uses .fsg.toml when both files exist in the same directory."""

        (tmp_path / ".fsg.toml").write_text("depth = 1\n", encoding="utf-8")
        (tmp_path / "pyproject.toml").write_text("[tool.fsg]\ndepth = 5\n", encoding="utf-8")
        assert Config.find(tmp_path).depth == 1

    def test_skips_pyproject_without_table(self, tmp_path: Path) -> None:
        """Continues with the parent directory when pyproject.toml has no [tool.fsg] table."""

        init_repository(tmp_path)
        (tmp_path / ".fsg.toml").write_text("depth = 4\n", encoding="utf-8")
        nested = tmp_path / "pkg"
        nested.mkdir()
        (nested / "pyproject.toml").write_text('[project]\nname = "pkg"\n', encoding="utf-8")
        assert Config.find(nested).depth == 4

    def test_searches_parent_directories(self, tmp_path: Path) -> None:
        """Finds the config of the repository root when rendering a subdirectory."""

        init_repository(tmp_path)
        (tmp_path / ".fsg.toml").write_text("fence = false\n", encoding="utf-8")
        nested = tmp_path / "src" / "pkg"
        nested.mkdir(parents=True)
        assert Config.find(nested).fence is False

    def test_returns_empty_config_without_file(self, tmp_path: Path) -> None:
        """Returns a config without source when no file is found."""

        assert Config.find(tmp_path).source is None

    def test_rejects_invalid_toml(self, tmp_path: Path) -> None:
        """Raises ValueError naming the file when it is not valid TOML."""

        (tmp_path / ".fsg.toml").write_text("depth = \n", encoding="utf-8")
        with pytest.raises(ConfigError, match="invalid TOML"):
            Config.find(tmp_path)


class TestMerge:
    """Covers combining the config with the command line arguments."""

    def test_uses_defaults_without_config_and_arguments(self) -> None:
        """Returns the built-in defaults when nothing is set."""

        assert Config().merge(namespace()) == {
            "depth": None, "dirs_only": False, "exclude": [], "include": [], "fence": True, "use_ascii": False,
        }

    def test_uses_config_values(self) -> None:
        """Returns the configured values when no argument is given."""

        config = Config({"depth": 2, "dirs-only": True, "fence": False, "ascii": True})
        assert config.merge(namespace()) == {
            "depth": 2, "dirs_only": True, "exclude": [], "include": [], "fence": False, "use_ascii": True,
        }

    def test_arguments_override_config(self) -> None:
        """Prefers given arguments, including switched-off ones, over the config."""

        config = Config({"depth": 2, "dirs-only": True, "fence": False, "ascii": True})
        merged = config.merge(namespace(depth=4, dirs_only=False, fence=True, use_ascii=False))
        assert merged == {
            "depth": 4, "dirs_only": False, "exclude": [], "include": [], "fence": True, "use_ascii": False,
        }

    def test_combines_include_patterns(self) -> None:
        """Returns the configured include patterns followed by the ones from the arguments."""

        merged = Config({"include": ["*.py"]}).merge(namespace(include=["*.md"]))
        assert merged["include"] == ["*.py", "*.md"]

    @pytest.mark.parametrize("include", ["*.py", [1], ["*.py", None]])
    def test_rejects_invalid_include(self, include: object) -> None:
        """Raises ConfigError when include is not a list of strings."""

        with pytest.raises(ConfigError, match="include"):
            Config({"include": include})

    def test_combines_exclude_patterns(self) -> None:
        """Returns the configured patterns followed by the ones from the arguments."""

        merged = Config({"exclude": ["*.log"]}).merge(namespace(exclude=["tests"]))
        assert merged["exclude"] == ["*.log", "tests"]

class TestSearchBoundary:
    """Covers where the search for a config file stops."""

    @requires_git
    def test_stops_at_repository_root(self, tmp_path: Path) -> None:
        """Ignores a config file above the root of the git working tree."""

        (tmp_path / ".fsg.toml").write_text("depth = 4\n", encoding="utf-8")
        repository = tmp_path / "project"
        repository.mkdir()
        init_repository(repository)
        assert Config.find(repository).source is None

    def test_stops_at_home_directory(self, tmp_path: Path, monkeypatch) -> None:
        """Ignores a config file above the home directory outside a repository."""

        (tmp_path / ".fsg.toml").write_text("depth = 4\n", encoding="utf-8")
        home = tmp_path / "home"
        nested = home / "notes" / "docs"
        nested.mkdir(parents=True)
        monkeypatch.setenv("HOME", str(home))
        monkeypatch.setenv("USERPROFILE", str(home))
        (home / ".fsg.toml").write_text("depth = 2\n", encoding="utf-8")
        assert Config.find(nested).depth == 2
        (home / ".fsg.toml").unlink()
        assert Config.find(nested).source is None

    def test_searches_only_start_outside_home(self, tmp_path: Path, monkeypatch) -> None:
        """Searches nothing but the start directory when it lies outside the home directory and any repository."""

        (tmp_path / ".fsg.toml").write_text("depth = 4\n", encoding="utf-8")
        nested = tmp_path / "data"
        nested.mkdir()
        monkeypatch.setenv("HOME", str(tmp_path / "elsewhere"))
        monkeypatch.setenv("USERPROFILE", str(tmp_path / "elsewhere"))
        assert Config.find(nested).source is None