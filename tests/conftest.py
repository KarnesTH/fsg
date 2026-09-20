import os
import shutil
import subprocess
from pathlib import Path

import pytest

requires_git = pytest.mark.skipif(shutil.which("git") is None, reason="git is not installed")

requires_unprivileged_user = pytest.mark.skipif(
    not hasattr(os, "geteuid") or os.geteuid() == 0,
    reason="file permissions do not apply to this user",
)


def create_files(root: Path, paths: list[str]) -> None:
    """Creates every given relative path below the root, including its parent directories.

    Args:
        root: Base directory the paths are created in.
        paths: Relative path strings, using forward slashes.
    """

    for path in paths:
        target = root / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.touch()


def init_repository(root: Path) -> None:
    """Initializes an empty git repository in the given directory.

    Args:
        root: Directory the repository is created in.
    """

    subprocess.run(["git", "init", "-q", "."], cwd=root, check=True)


@pytest.fixture
def project(tmp_path: Path) -> Path:
    """Returns a project directory holding source files next to generated files and tool directories."""

    create_files(
        tmp_path,
        [
            "main.py",
            "README.md",
            "gui/__init__.py",
            "gui/main_window.py",
            "gui/__pycache__/main_window.cpython-314.pyc",
            "gui/widgets/chip.py",
            "assets/icons/home.svg",
            ".idea/misc.xml",
            ".idea/.gitignore",
            ".venv/lib/site.py",
            "node_modules/pkg/index.js",
        ],
    )
    return tmp_path