from __future__ import annotations

from pathlib import Path

PRE_COMMIT_CONFIG = ".pre-commit-config.yaml"


class Hook:
    """Adds the fsg update step for one target file to the commit hooks of a git repository."""

    def __init__(self, repository: Path, target: str) -> None:
        """Stores the repository root and the target file path relative to it.

        Args:
            repository: Root directory of the git working tree.
            target: Path of the file holding the markers, relative to the repository root, using forward slashes.
        """

        self.repository = Path(repository)
        self.target = target

    @classmethod
    def for_repository(cls, repository: Path, target: str) -> Hook:
        """Returns a PreCommitHook when the repository root holds a .pre-commit-config.yaml, otherwise a GitHook.

        Args:
            repository: Root directory of the git working tree.
            target: Path of the file holding the markers, relative to the repository root, using forward slashes.
        """

        from fsg.hooks.git_hook import GitHook
        from fsg.hooks.pre_commit_hook import PreCommitHook

        if (Path(repository) / PRE_COMMIT_CONFIG).is_file():
            return PreCommitHook(repository, target)
        return GitHook(repository, target)

    def location(self) -> Path:
        """Returns the file the hook is written to."""

        raise NotImplementedError

    def install(self) -> bool:
        """Adds the fsg step to the hook file and returns False when it is already present."""

        raise NotImplementedError