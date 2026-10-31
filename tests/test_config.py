import argparse
from pathlib import Path

import pytest

from fsg.config import Config
from fsg.errors import ConfigError
from fsg.glyphs import Glyphs
from tests.conftest import init_repository, requires_git


def namespace(**overrides: object) -> argparse.Namespace:
    """Returns parsed arguments with every config-backed option unset, updated with the given values.

    Args:
        **overrides: Attribute values replacing the defaults.
    """

    values = {
        "depth": None, "dirs_only": None, "exclude": [], "include": [], "fence": None, "use_ascii": None,
        "style": None, "glyph": [], "summary": None,
    }
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
            "depth": None, "dirs_only": False, "exclude": [], "include": [], "fence": True, "summary": False,
            "glyphs": Glyphs.from_style("unicode"),
        }

    def test_uses_config_values(self) -> None:
        """Returns the configured values when no argument is given."""

        config = Config({"depth": 2, "dirs-only": True, "fence": False, "ascii": True, "summary": True})
        assert config.merge(namespace()) == {
            "depth": 2, "dirs_only": True, "exclude": [], "include": [], "fence": False, "summary": True,
            "glyphs": Glyphs.from_style("ascii"),
        }

    def test_arguments_override_config(self) -> None:
        """Prefers given arguments, including switched-off ones, over the config."""

        config = Config({"depth": 2, "dirs-only": True, "fence": False, "ascii": True, "summary": True})
        merged = config.merge(namespace(depth=4, dirs_only=False, fence=True, use_ascii=False, summary=False))
        assert merged == {
            "depth": 4, "dirs_only": False, "exclude": [], "include": [], "fence": True, "summary": False,
            "glyphs": Glyphs.from_style("unicode"),
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


class TestStyle:
    """Covers choosing the style and glyphs from config and arguments."""

    def test_reads_style_and_glyphs(self) -> None:
        """Builds the glyphs from the configured style with configured overrides."""

        config = Config({"style": "heavy", "glyphs": {"last": "┗━━ "}})
        assert config.merge(namespace())["glyphs"] == Glyphs.from_style("heavy", {"last": "┗━━ "})

    def test_style_argument_wins(self) -> None:
        """Prefers --style over the configured style and the ascii switch."""

        config = Config({"style": "heavy", "ascii": True})
        assert config.merge(namespace(style="double"))["glyphs"] == Glyphs.from_style("double")

    def test_ascii_argument_wins_over_config_style(self) -> None:
        """Uses the ascii style for --ascii and the unicode style for --no-ascii."""

        config = Config({"style": "heavy"})
        assert config.merge(namespace(use_ascii=True))["glyphs"] == Glyphs.from_style("ascii")
        assert config.merge(namespace(use_ascii=False))["glyphs"] == Glyphs.from_style("unicode")

    def test_glyph_argument_overrides_config(self) -> None:
        """Replaces configured glyphs with --glyph values."""

        config = Config({"glyphs": {"branch": "+-- "}})
        glyphs = config.merge(namespace(glyph=["branch=*-- "]))["glyphs"]
        assert glyphs.branch == "*-- "

    def test_rejects_glyph_argument_without_equals(self) -> None:
        """Raises ConfigError for a --glyph value without key."""

        with pytest.raises(ConfigError, match="key=value"):
            Config().merge(namespace(glyph=["branch"]))

    @pytest.mark.parametrize(
        ("values", "match"),
        [
            ({"style": 3}, "style must be a string"),
            ({"glyphs": "x"}, "glyphs must be a table"),
            ({"glyphs": {"stem": "|   "}}, "unknown glyph 'stem'"),
            ({"summary": "yes"}, "summary must be true or false"),
        ],
    )
    def test_rejects_invalid_values(self, values: dict, match: str) -> None:
        """Raises ConfigError for invalid style, glyphs and summary values."""

        with pytest.raises(ConfigError, match=match):
            Config(values)


class TestWithMarker:
    """Covers applying start marker options on top of the config."""

    def test_applies_options(self, tmp_path: Path) -> None:
        """Converts the string values of the marker into config values."""

        (tmp_path / "src").mkdir()
        marker = {"path": "src", "depth": "2", "dirs-only": "true", "fence": "false", "summary": "true", "style": "rounded"}
        config = Config().with_marker(marker, tmp_path / "README.md", 3)
        assert (config.path, config.depth, config.dirs_only, config.fence, config.summary, config.style) == (
            (tmp_path / "src").resolve(), 2, True, False, True, "rounded",
        )

    def test_adds_patterns_to_config(self, tmp_path: Path) -> None:
        """Appends comma-separated marker patterns to the configured ones."""

        config = Config({"exclude": ["*.log"]}).with_marker({"exclude": "tests, docs", "include": "*.py"}, tmp_path / "a.md", 1)
        assert (config.exclude, config.include) == (["*.log", "tests", "docs"], ["*.py"])

    def test_leaves_original_config_unchanged(self, tmp_path: Path) -> None:
        """Returns a copy and keeps the patterns of the original config."""

        original = Config({"exclude": ["*.log"]})
        original.with_marker({"exclude": "tests", "depth": "1"}, tmp_path / "a.md", 1)
        assert (original.exclude, original.depth) == (["*.log"], None)

    def test_marker_overrides_config(self, tmp_path: Path) -> None:
        """Replaces configured single values with the marker values."""

        config = Config({"depth": 4, "style": "heavy"}).with_marker({"depth": "1", "style": "ascii"}, tmp_path / "a.md", 1)
        assert (config.depth, config.style) == (1, "ascii")

    def test_arguments_override_marker(self, tmp_path: Path) -> None:
        """Lets command line arguments win over marker options."""

        config = Config().with_marker({"depth": "1", "summary": "true"}, tmp_path / "a.md", 1)
        merged = config.merge(namespace(depth=3, summary=False))
        assert (merged["depth"], merged["summary"]) == (3, False)

    @requires_git
    def test_allows_path_inside_repository(self, tmp_path: Path) -> None:
        """Accepts a path leaving the directory of the file as long as it stays in the repository."""

        init_repository(tmp_path)
        (tmp_path / "docs").mkdir()
        (tmp_path / "src").mkdir()
        config = Config().with_marker({"path": "../src"}, tmp_path / "docs" / "a.md", 1)
        assert config.path == (tmp_path / "src").resolve()

    @requires_git
    def test_rejects_path_outside_repository(self, tmp_path: Path) -> None:
        """Raises ConfigError naming file and line when the path leaves the repository."""

        repository = tmp_path / "project"
        repository.mkdir()
        init_repository(repository)
        with pytest.raises(ConfigError, match="a.md:7: path must stay inside"):
            Config().with_marker({"path": ".."}, repository / "a.md", 7)

    def test_rejects_path_outside_file_directory_without_repository(self, tmp_path: Path) -> None:
        """Keeps the path inside the directory of the file outside a repository."""

        nested = tmp_path / "docs"
        nested.mkdir()
        with pytest.raises(ConfigError, match="must stay inside"):
            Config().with_marker({"path": "../"}, nested / "a.md", 1)

    @pytest.mark.parametrize(
        ("options", "match"),
        [
            ({"depth": "0"}, "depth must be an integer"),
            ({"depth": "two"}, "depth must be an integer"),
            ({"dirs-only": "yes"}, "dirs-only must be true or false"),
            ({"colour": "red"}, "unknown marker option 'colour'"),
        ],
    )
    def test_rejects_invalid_options(self, tmp_path: Path, options: dict, match: str) -> None:
        """Raises ConfigError for invalid marker values and unknown keys."""

        with pytest.raises(ConfigError, match=match):
            Config().with_marker(options, tmp_path / "a.md", 1)