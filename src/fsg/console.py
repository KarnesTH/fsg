from __future__ import annotations

import os
import sys
from typing import TextIO

from fsg.errors import FsgError

RESET = "\033[0m"
GREEN = "\033[32m"
RED = "\033[31m"
DIM = "\033[2m"

UNICODE_SYMBOLS = {"success": "✔", "info": "•", "failure": "✖"}
ASCII_SYMBOLS = {"success": "[ok]", "info": "[info]", "failure": "[error]"}


class Console:
    """Prints status lines with a leading symbol and an optional hint, colored when the stream is a terminal."""

    def __init__(self, stdout: TextIO | None = None, stderr: TextIO | None = None, use_ascii: bool = False) -> None:
        """Stores the output streams, selects the symbol set and decides per stream whether colors are used.

        Args:
            stdout: Stream for results and success messages, defaults to sys.stdout.
            stderr: Stream for failures and errors, defaults to sys.stderr.
            use_ascii: Uses bracketed words instead of Unicode symbols.
        """

        self.stdout = stdout or sys.stdout
        self.stderr = stderr or sys.stderr
        self.symbols = ASCII_SYMBOLS if use_ascii else UNICODE_SYMBOLS
        self.colors = {self.stdout: self._supports_color(self.stdout), self.stderr: self._supports_color(self.stderr)}

    def output(self, text: str) -> None:
        """Writes the text unchanged to stdout, followed by a line break.

        Args:
            text: Text to write.
        """

        print(text, file=self.stdout)

    def success(self, message: str, hint: str | None = None) -> None:
        """Writes the message with the success symbol in green to stdout.

        Args:
            message: Status line.
            hint: Indented line below the message, or None.
        """

        self._line(self.stdout, "success", GREEN, message, hint)

    def info(self, message: str, hint: str | None = None) -> None:
        """Writes the whole message dimmed with the info symbol to stdout.

        Args:
            message: Status line.
            hint: Indented line below the message, or None.
        """

        self._line(self.stdout, "info", DIM, message, hint, dim_message=True)

    def failure(self, message: str, hint: str | None = None) -> None:
        """Writes the message with the failure symbol in red to stderr.

        Args:
            message: Status line.
            hint: Indented line below the message, or None.
        """

        self._line(self.stderr, "failure", RED, message, hint)

    def error(self, error: FsgError) -> None:
        """Writes the message and hint of the error as a failure.

        Args:
            error: Error to report.
        """

        self.failure(error.message, error.hint)

    def _line(self, stream: TextIO, kind: str, color: str, message: str, hint: str | None, dim_message: bool = False) -> None:
        """Writes the symbol, the message and the hint line, wrapping them in color codes when the stream supports it.

        Args:
            stream: Stream to write to.
            kind: Key of the symbol to use.
            color: Colour code for the symbol.
            message: Status line.
            hint: Indented line below the message, or None.
            dim_message: Dims the message as well as the symbol.
        """

        symbol = self.symbols[kind]
        if self.colors[stream]:
            symbol = f"{color}{symbol}{RESET}"
            if dim_message:
                message = f"{DIM}{message}{RESET}"
        print(f"{symbol} {message}", file=stream)
        if hint:
            line = f"  hint: {hint}"
            print(f"{DIM}{line}{RESET}" if self.colors[stream] else line, file=stream)

    @staticmethod
    def _supports_color(stream: TextIO) -> bool:
        """Returns whether color codes should be written to the stream.

        NO_COLOR disables colors and FORCE_COLOR enables them, each when set to a non-empty value.
        Otherwise, colors are used for terminals other than TERM=dumb; on Windows the virtual terminal
        mode of the console is switched on first and colors stay off when that fails.

        Args:
            stream: Stream to check.
        """

        if os.environ.get("NO_COLOR"):
            return False
        if os.environ.get("FORCE_COLOR"):
            return True
        if os.environ.get("TERM") == "dumb" or not hasattr(stream, "isatty") or not stream.isatty():
            return False
        if os.name == "nt":
            return Console._enable_windows_ansi(stream)
        return True

    @staticmethod
    def _enable_windows_ansi(stream: TextIO) -> bool:
        """Switches on virtual terminal processing for the console behind the stream and returns whether it succeeded.

        Args:
            stream: Console stream on Windows.
        """

        try:
            import ctypes
            import msvcrt

            kernel32 = ctypes.windll.kernel32
            handle = msvcrt.get_osfhandle(stream.fileno())
            mode = ctypes.c_uint32()
            if not kernel32.GetConsoleMode(handle, ctypes.byref(mode)):
                return False
            return bool(kernel32.SetConsoleMode(handle, mode.value | 0x0004))
        except (AttributeError, OSError, ValueError):
            return False