from __future__ import annotations

import shlex
from dataclasses import dataclass, field

from fsg.errors import MarkerError


@dataclass
class Section:
    """Position and options of one block between an fsg start and end marker."""

    inner_start: int
    inner_end: int
    line: int
    options: dict[str, str] = field(default_factory=dict)

    @staticmethod
    def parse_options(text: str, location: str) -> dict[str, str]:
        """Returns the options written in a start marker as key-value strings.

        Tokens are split like a shell command line; "key=value" sets a value and a bare "key" sets "true".

        Args:
            text: Text between "fsg:start" and "-->".
            location: File and line used in error messages.

        Raises:
            MarkerError: The text has an unclosed quote or a token without key.
        """

        try:
            tokens = shlex.split(text)
        except ValueError as error:
            raise MarkerError(f"{location}: invalid marker options: {error}") from None
        options: dict[str, str] = {}
        for token in tokens:
            key, separator, value = token.partition("=")
            if not key:
                raise MarkerError(f"{location}: invalid marker option '{token}'", "write options as key=value")
            options[key.lower()] = value if separator else "true"
        return options