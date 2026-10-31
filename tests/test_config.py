import argparse
from pathlib import Path

import pytest

from fsg.config import Config


def namespace(**overrides: object) -> argparse.Namespace:
    """Returns parsed arguments with every config-backed option unset, updated with the given values.

    Args:
        **overrides: Attribute values replacing the defaults.
    """

    values = {"depth": None, "dirs_only": None, "exclude": [], "fence": None, "use_ascii": None}
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

        assert Config({"path": "src"}, tmp_path / ".fsg.toml").path == tmp_path / "src"

    def test_keeps_path_without_source(self) -> None:
        """Stores the path as given when the values come from no file."""

        assert Config({"path": "src"}).path == Path("src")

    def test_rejects_non_string_path(self) -> None:
        """Raises ValueError when path is not a string."""

        with pytest.raises(ValueError, match="path"):
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

        with pytest.raises(ValueError, match="depth"):
            Config({"depth": depth})

    @pytest.mark.parametrize("key", ["dirs-only", "fence", "ascii"])
    def test_rejects_non_boolean_switch(self, key: str) -> None:
        """Raises ValueError when a switch is not true or false."""

        with pytest.raises(ValueError, match=key):
            Config({key: "yes"})

    @pytest.mark.parametrize("exclude", ["*.log", [1, 2], ["*.log", None]])
    def test_rejects_invalid_exclude(self, exclude: object) -> None:
        """Raises ValueError when exclude is not a list of strings."""

        with pytest.raises(ValueError, match="exclude"):
            Config({"exclude": exclude})

    def test_rejects_unknown_option(self) -> None:
        """Raises ValueError naming the unknown key."""

        with pytest.raises(ValueError, match="unknown option 'dirs_only'"):
            Config({"dirs_only": True})

    def test_names_source_in_errors(self, tmp_path: Path) -> None:
        """Mentions the config file in the error message."""

        with pytest.raises(ValueError, match="pyproject.toml"):
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

        (tmp_path / ".fsg.toml").write_text("depth = 4\n", encoding="utf-8")
        nested = tmp_path / "pkg"
        nested.mkdir()
        (nested / "pyproject.toml").write_text('[project]\nname = "pkg"\n', encoding="utf-8")
        assert Config.find(nested).depth == 4

    def test_searches_parent_directories(self, tmp_path: Path) -> None:
        """Finds the config of the project root when rendering a subdirectory."""

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
        with pytest.raises(ValueError, match="invalid TOML"):
            Config.find(tmp_path)


class TestMerge:
    """Covers combining the config with the command line arguments."""

    def test_uses_defaults_without_config_and_arguments(self) -> None:
        """Returns the built-in defaults when nothing is set."""

        assert Config().merge(namespace()) == {
            "depth": None, "dirs_only": False, "exclude": [], "fence": True, "use_ascii": False,
        }

    def test_uses_config_values(self) -> None:
        """Returns the configured values when no argument is given."""

        config = Config({"depth": 2, "dirs-only": True, "fence": False, "ascii": True})
        assert config.merge(namespace()) == {
            "depth": 2, "dirs_only": True, "exclude": [], "fence": False, "use_ascii": True,
        }

    def test_arguments_override_config(self) -> None:
        """Prefers given arguments, including switched-off ones, over the config."""

        config = Config({"depth": 2, "dirs-only": True, "fence": False, "ascii": True})
        merged = config.merge(namespace(depth=4, dirs_only=False, fence=True, use_ascii=False))
        assert merged == {"depth": 4, "dirs_only": False, "exclude": [], "fence": True, "use_ascii": False}

    def test_combines_exclude_patterns(self) -> None:
        """Returns the configured patterns followed by the ones from the arguments."""

        merged = Config({"exclude": ["*.log"]}).merge(namespace(exclude=["tests"]))
        assert merged["exclude"] == ["*.log", "tests"]