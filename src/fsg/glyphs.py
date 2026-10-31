from __future__ import annotations

import unicodedata
from dataclasses import dataclass

from fsg.constants import STYLES
from fsg.errors import ConfigError

KEYS = ("branch", "last", "pipe", "space")


@dataclass(frozen=True)
class Glyphs:
    """Holds the four strings a tree is drawn with: branch and last connectors, the pipe and the empty indent."""

    branch: str
    last: str
    pipe: str
    space: str

    @classmethod
    def from_style(cls, style: str = "unicode", overrides: dict[str, str] | None = None) -> Glyphs:
        """Returns the glyphs of a built-in style with single glyphs replaced by the overrides.

        Args:
            style: Name of a built-in style.
            overrides: Mapping of glyph key to replacement string.

        Raises:
            ConfigError: The style or an override key is unknown, or the glyphs differ in display width.
        """

        if style not in STYLES:
            raise ConfigError(f"unknown style '{style}'", f"use one of: {', '.join(STYLES)}")
        values = dict(STYLES[style])
        for key, value in (overrides or {}).items():
            if key not in KEYS:
                raise ConfigError(f"unknown glyph '{key}'", f"use one of: {', '.join(KEYS)}")
            values[key] = value
        glyphs = cls(**values)
        widths = {key: cls.width(value) for key, value in values.items()}
        if len(set(widths.values())) != 1 or 0 in widths.values() or any("\n" in value for value in values.values()):
            listed = ", ".join(f"{key}={widths[key]}" for key in KEYS)
            raise ConfigError(
                f"glyphs must all have the same width ({listed})",
                'pad the shorter glyphs with spaces, e.g. --glyph pipe="|   "',
            )
        return glyphs

    @staticmethod
    def width(text: str) -> int:
        """Returns the number of terminal columns the text occupies.

        Wide and fullwidth characters count two columns, combining characters none, everything else one.

        Args:
            text: Text to measure.
        """

        total = 0
        for character in text:
            if unicodedata.combining(character):
                continue
            total += 2 if unicodedata.east_asian_width(character) in ("W", "F") else 1
        return total

    def characters(self) -> set[str]:
        """Returns every character used by the four glyphs."""

        return set(self.branch + self.last + self.pipe + self.space)