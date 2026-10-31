import pytest

from fsg.constants import STYLES
from fsg.errors import ConfigError
from fsg.glyphs import Glyphs


class TestFromStyle:
    """Covers building glyphs from a style and overrides."""

    @pytest.mark.parametrize("style", list(STYLES))
    def test_builds_every_style(self, style: str) -> None:
        """Returns the four glyphs of each built-in style with equal width."""

        glyphs = Glyphs.from_style(style)
        assert (glyphs.branch, glyphs.last, glyphs.pipe, glyphs.space) == tuple(STYLES[style].values())
        assert len({Glyphs.width(value) for value in STYLES[style].values()}) == 1

    def test_defaults_to_unicode(self) -> None:
        """Uses the unicode style without arguments."""

        assert Glyphs.from_style() == Glyphs("├── ", "└── ", "│   ", "    ")

    def test_applies_overrides(self) -> None:
        """Replaces single glyphs and keeps the others of the style."""

        glyphs = Glyphs.from_style("ascii", {"branch": "+-- ", "last": "\\-- "})
        assert glyphs == Glyphs("+-- ", "\\-- ", "|   ", "    ")

    def test_rejects_unknown_style(self) -> None:
        """Raises ConfigError listing the available styles."""

        with pytest.raises(ConfigError, match="unknown style 'fancy'") as error:
            Glyphs.from_style("fancy")
        assert "rounded" in error.value.hint

    def test_rejects_unknown_glyph(self) -> None:
        """Raises ConfigError for an override key that is no glyph."""

        with pytest.raises(ConfigError, match="unknown glyph 'stem'"):
            Glyphs.from_style("unicode", {"stem": "|   "})

    @pytest.mark.parametrize("override", [{"branch": "+-"}, {"pipe": ""}, {"space": "   \n"}])
    def test_rejects_unequal_widths(self, override: dict) -> None:
        """Raises ConfigError with the widths when the glyphs do not line up."""

        with pytest.raises(ConfigError, match="same width") as error:
            Glyphs.from_style("unicode", override)
        assert "pad" in error.value.hint

    def test_counts_wide_characters_twice(self) -> None:
        """Rejects a glyph with a wide character next to glyphs of the same character count."""

        with pytest.raises(ConfigError, match="branch=5"):
            Glyphs.from_style("unicode", {"branch": "📁── "})


class TestWidth:
    """Covers measuring display width."""

    @pytest.mark.parametrize(("text", "width"), [("├── ", 4), ("abc", 3), ("📁", 2), ("e\u0301", 1), ("", 0)])
    def test_measures_columns(self, text: str, width: int) -> None:
        """Counts wide characters twice and combining characters not at all."""

        assert Glyphs.width(text) == width


def test_characters_returns_used_characters() -> None:
    """Returns the set of characters in all four glyphs."""

    assert Glyphs.from_style("ascii").characters() == {"|", "-", "`", " "}