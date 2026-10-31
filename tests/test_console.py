import io

import pytest

from fsg.console import Console
from fsg.errors import MarkerError


class Terminal(io.StringIO):
    """In-memory stream that reports itself as a terminal."""

    def isatty(self) -> bool:
        """Returns True."""

        return True


@pytest.fixture(autouse=True)
def plain_environment(monkeypatch) -> None:
    """Removes the color switches from the environment and pretends a POSIX system."""

    for name in ("NO_COLOR", "FORCE_COLOR", "TERM"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setattr("fsg.console.os.name", "posix")


def console(stream_type: type = io.StringIO, use_ascii: bool = False) -> Console:
    """Returns a console writing to two new in-memory streams of the given type.

    Args:
        stream_type: Stream class for stdout and stderr.
        use_ascii: Uses bracketed words instead of symbols.
    """

    return Console(stream_type(), stream_type(), use_ascii=use_ascii)


class TestPlainOutput:
    """Covers the output without colors."""

    def test_success_goes_to_stdout(self) -> None:
        """Writes the check mark and the message to stdout."""

        output = console()
        output.success("README.md: tree updated")
        assert output.stdout.getvalue() == "✔ README.md: tree updated\n"
        assert output.stderr.getvalue() == ""

    def test_info_goes_to_stdout(self) -> None:
        """Writes the bullet and the message to stdout."""

        output = console()
        output.info("README.md: tree already up to date")
        assert output.stdout.getvalue() == "• README.md: tree already up to date\n"

    def test_failure_with_hint_goes_to_stderr(self) -> None:
        """Writes the cross, the message and the indented hint to stderr."""

        output = console()
        output.failure("README.md: tree is out of date", "run fsg --update README.md")
        assert output.stderr.getvalue() == "✖ README.md: tree is out of date\n  hint: run fsg --update README.md\n"
        assert output.stdout.getvalue() == ""

    def test_error_uses_message_and_hint(self) -> None:
        """Reports an FsgError as failure with its hint."""

        output = console()
        output.error(MarkerError("README.md: missing marker", "add it"))
        assert output.stderr.getvalue() == "✖ README.md: missing marker\n  hint: add it\n"

    def test_output_is_unchanged(self) -> None:
        """Writes plain output without symbol."""

        output = console()
        output.output("tree")
        assert output.stdout.getvalue() == "tree\n"

    def test_ascii_symbols(self) -> None:
        """Uses bracketed words with use_ascii."""

        output = console(use_ascii=True)
        output.success("a")
        output.info("b")
        output.failure("c")
        assert output.stdout.getvalue() == "[ok] a\n[info] b\n"
        assert output.stderr.getvalue() == "[error] c\n"


class TestColors:
    """Covers when color codes are written."""

    def test_colors_terminal(self) -> None:
        """Colors the symbol and dims the hint on a terminal."""

        output = console(Terminal)
        output.failure("bad", "fix it")
        assert output.stderr.getvalue() == "\033[31m✖\033[0m bad\n\033[2m  hint: fix it\033[0m\n"

    def test_dims_info_message(self) -> None:
        """Dims the whole info line on a terminal."""

        output = console(Terminal)
        output.info("same")
        assert output.stdout.getvalue() == "\033[2m•\033[0m \033[2msame\033[0m\n"

    def test_no_colors_when_redirected(self) -> None:
        """Writes no color codes to a stream that is not a terminal."""

        output = console()
        output.success("ok")
        assert "\033" not in output.stdout.getvalue()

    def test_no_color_wins(self, monkeypatch) -> None:
        """Disables colors on a terminal when NO_COLOR is set."""

        monkeypatch.setenv("NO_COLOR", "1")
        output = console(Terminal)
        output.success("ok")
        assert output.stdout.getvalue() == "✔ ok\n"

    def test_force_color(self, monkeypatch) -> None:
        """Enables colors for a redirected stream when FORCE_COLOR is set."""

        monkeypatch.setenv("FORCE_COLOR", "1")
        output = console()
        output.success("ok")
        assert output.stdout.getvalue() == "\033[32m✔\033[0m ok\n"

    def test_dumb_terminal(self, monkeypatch) -> None:
        """Disables colours for TERM=dumb."""

        monkeypatch.setenv("TERM", "dumb")
        output = console(Terminal)
        output.success("ok")
        assert output.stdout.getvalue() == "✔ ok\n"