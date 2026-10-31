class FsgError(Exception):
    """Base error of fsg, carrying a message for the user and an optional hint on how to fix it."""

    def __init__(self, message: str, hint: str | None = None) -> None:
        """Stores the message and the hint.

        Args:
            message: Description of what went wrong.
            hint: Suggestion on how to fix it, or None.
        """

        super().__init__(message)
        self.message = message
        self.hint = hint


class ConfigError(FsgError):
    """Raised when a config file is not valid TOML or holds an invalid option."""


class FileError(FsgError):
    """Raised when a file is missing, is not UTF-8 text, or cannot be read or written."""


class MarkerError(FsgError):
    """Raised when the fsg start or end marker is missing from a file."""


class PathError(FsgError):
    """Raised when the directory to render does not exist or is not a directory."""


class GitError(FsgError):
    """Raised when git is not installed or a git command fails."""


class HookError(FsgError):
    """Raised when the commit hook cannot be set up."""