from __future__ import annotations

import os
from functools import cache
from pathlib import Path


class Executable:
    """Locates programs on PATH without considering the current directory."""

    @staticmethod
    @cache
    def find(name: str) -> str | None:
        """Returns the absolute path of the first executable with the name in the absolute PATH entries, or None.

        Relative entries and the current directory are skipped. On Windows every extension listed in PATHEXT is tried.

        Args:
            name: Program name without extension.
        """

        names = [name]
        if os.name == "nt":
            extensions = os.environ.get("PATHEXT", ".COM;.EXE;.BAT;.CMD").split(os.pathsep)
            names = [f"{name}{extension.lower()}" for extension in extensions if extension]
        for entry in os.environ.get("PATH", "").split(os.pathsep):
            directory = Path(entry)
            if not entry or not directory.is_absolute():
                continue
            for candidate_name in names:
                candidate = directory / candidate_name
                if candidate.is_file() and os.access(candidate, os.X_OK):
                    return str(candidate)
        return None