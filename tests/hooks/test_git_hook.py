import os
import shutil
import subprocess
from pathlib import Path

import pytest

from fsg.hooks import GitHook
from fsg.hooks.git_hook import MARKER
from tests.conftest import init_repository, requires_git


@pytest.fixture
def repository(tmp_path: Path) -> Path:
    """Returns an initialized git repository."""

    init_repository(tmp_path)
    return tmp_path


@requires_git
class TestLocation:
    """Covers locating the pre-commit script."""

    def test_uses_default_hooks_directory(self, repository: Path) -> None:
        """Returns the pre-commit script inside .git/hooks."""

        assert GitHook(repository, "README.md").location() == repository / ".git" / "hooks" / "pre-commit"

    def test_honours_hooks_path(self, repository: Path) -> None:
        """Returns the script inside the directory configured as core.hooksPath."""

        subprocess.run(["git", "config", "core.hooksPath", "githooks"], cwd=repository, check=True)
        assert GitHook(repository, "README.md").location() == repository / "githooks" / "pre-commit"


@requires_git
class TestInstall:
    """Covers writing the fsg step into the script."""

    def test_creates_executable_script(self, repository: Path) -> None:
        """Writes a new shell script with the fsg step and marks it executable."""

        hook = GitHook(repository, "README.md")
        assert hook.install() is True
        text = hook.location().read_text(encoding="utf-8")
        assert text.startswith("#!/bin/sh\n" + MARKER)
        assert "fsg --update README.md" in text
        if os.name == "posix":
            assert os.access(hook.location(), os.X_OK)

    def test_creates_missing_hooks_directory(self, repository: Path) -> None:
        """Creates the configured hooks directory when it does not exist yet."""

        subprocess.run(["git", "config", "core.hooksPath", "githooks"], cwd=repository, check=True)
        assert GitHook(repository, "README.md").install() is True
        assert (repository / "githooks" / "pre-commit").is_file()

    def test_appends_to_existing_script(self, repository: Path) -> None:
        """Keeps the existing commands and adds the step after them."""

        hook = GitHook(repository, "README.md")
        hook.location().write_text("#!/bin/sh\nruff check .\n", encoding="utf-8")
        hook.install()
        text = hook.location().read_text(encoding="utf-8")
        assert text.startswith("#!/bin/sh\nruff check .\n" + MARKER)

    def test_inserts_before_final_exit(self, repository: Path) -> None:
        """Places the step before a closing exit line so it still runs."""

        hook = GitHook(repository, "README.md")
        hook.location().write_text("#!/bin/sh\nruff check .\nexit 0\n", encoding="utf-8")
        hook.install()
        text = hook.location().read_text(encoding="utf-8")
        assert text.index(MARKER) < text.index("exit 0\n")
        assert text.endswith("fi\nexit 0\n")

    def test_adds_missing_final_newline(self, repository: Path) -> None:
        """Ends the last line of the existing script before appending."""

        hook = GitHook(repository, "README.md")
        hook.location().write_text("#!/bin/sh\nruff check .", encoding="utf-8")
        hook.install()
        assert "ruff check .\n" + MARKER in hook.location().read_text(encoding="utf-8")

    def test_skips_existing_step(self, repository: Path) -> None:
        """Returns False and leaves the script untouched on a second run."""

        hook = GitHook(repository, "README.md")
        hook.install()
        text = hook.location().read_text(encoding="utf-8")
        assert hook.install() is False
        assert hook.location().read_text(encoding="utf-8") == text

    def test_quotes_target_for_the_shell(self, repository: Path) -> None:
        """Quotes a target containing spaces."""

        hook = GitHook(repository, "docs/my file.md")
        hook.install()
        assert "fsg --update 'docs/my file.md'" in hook.location().read_text(encoding="utf-8")
    def test_quotes_target_in_message(self, repository: Path) -> None:
        """Passes the target to printf as a quoted argument so shell syntax in the name is not executed."""

        hook = GitHook(repository, 'a"$(touch PWNED)".md')
        hook.install()
        text = hook.location().read_text(encoding="utf-8")
        assert "printf 'fsg: add %s and commit again\\n' 'a\"$(touch PWNED)\".md'" in text
        assert 'echo' not in text

    @pytest.mark.skipif(shutil.which("sh") is None, reason="sh is not installed")
    def test_message_does_not_run_shell_syntax(self, repository: Path) -> None:
        """Prints the target literally when the generated step runs."""

        hook = GitHook(repository, "$(touch PWNED).md")
        step = hook._step().replace("fsg --check", "false").replace("fsg --update", "true")
        result = subprocess.run(
            ["sh", "-c", f"command() {{ return 0; }}; {step}"],
            check=False,
            cwd=repository,
            capture_output=True,
            text=True,
        )
        assert result.stdout == "fsg: add $(touch PWNED).md and commit again\n"
        assert not (repository / "PWNED").exists()

    def test_keeps_permissions_of_existing_script(self, repository: Path) -> None:
        """Leaves the permission bits of an existing script unchanged."""

        hook = GitHook(repository, "README.md")
        hook.location().write_text("#!/bin/sh\n", encoding="utf-8")
        hook.location().chmod(0o750)
        hook.install()
        if os.name == "posix":
            assert hook.location().stat().st_mode & 0o777 == 0o750