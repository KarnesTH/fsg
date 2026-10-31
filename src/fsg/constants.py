UNICODE_GLYPHS = {"branch": "├── ", "last": "└── ", "pipe": "│   ", "space": "    "}
ASCII_GLYPHS = {"branch": "|-- ", "last": "`-- ", "pipe": "|   ", "space": "    "}

IGNORED = {
    ".git", ".svn", ".hg",
    ".idea", ".vscode",
    "__pycache__", ".mypy_cache", ".pytest_cache", ".ruff_cache",
    ".venv", "venv", "env",
    "node_modules", "target", "dist", "build", "out",
    ".godot", ".import",
    ".DS_Store", "Thumbs.db",
    "uv.lock",
}