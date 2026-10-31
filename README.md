<p align="center">
  <img src="assets/logo.svg" alt="fsg logo" width="128" />
</p>

<h1 align="center">fsg</h1>

<p align="center">
  <img src="https://img.shields.io/badge/version-0.1.0-blue" alt="Version 0.1.0" />
  <img src="https://img.shields.io/badge/python-3.11%2B-3776AB?logo=python&logoColor=white" alt="Python 3.11+" />
  <img src="https://img.shields.io/badge/dependencies-none-brightgreen" alt="No dependencies" />
  <img src="https://img.shields.io/badge/license-MIT-green" alt="MIT License" />
</p>

<p align="center">Generates clean directory trees that respect .gitignore and keep your docs up to date.</p>

## Features

- Inside a git repository, only files git tracks or would track are listed (`.gitignore` is respected)
- Outside a repository, common generated and tool directories are skipped (`.venv`, `__pycache__`, `node_modules`, `target`, `.idea`, …)
- Directories first, entries sorted case-insensitively, empty directories omitted
- Limit the depth, render directories only or exclude entries by glob pattern
- Output is wrapped in a `plaintext` code fence (optional) and always written as UTF-8
- Optional ASCII branches (`|--`, `` `-- ``) for environments without Unicode support

## Installation

Requires [uv](https://docs.astral.sh/uv/) and git (optional, for `.gitignore` support).

```bash
git clone https://github.com/KarnesTH/fsg.git
cd fsg
uv tool install .
```

## Usage

```bash
fsg [-h] [-d N] [--dirs-only] [-e PATTERN] [--no-fence] [--ascii] [-V] [path]
```

| Argument                  | Description                                                                 |
|---------------------------|-----------------------------------------------------------------------------|
| `path`                    | Directory to render (default: current directory)                            |
| `-d N`, `--depth N`       | Render only the first N levels below the root                               |
| `--dirs-only`             | Render directories only                                                     |
| `-e`, `--exclude PATTERN` | Leave out entries whose name or relative path matches the glob (repeatable) |
| `--no-fence`              | Print the tree without the Markdown code fence                              |
| `--ascii`                 | Draw the tree with ASCII instead of box-drawing characters                  |
| `-h`, `--help`            | Show the help text and exit                                                 |
| `-V`, `--version`         | Show the version and exit                                                   |

Example:

```bash
fsg src > tree.md
```

```plaintext
src/
└── fsg/
    ├── trees/
    │   ├── __init__.py
    │   ├── git_project_tree.py
    │   ├── plain_project_tree.py
    │   └── project_tree.py
    ├── __init__.py
    ├── __main__.py
    ├── cli.py
    └── constants.py
```

## Development

```bash
uv sync
uv run pytest
```