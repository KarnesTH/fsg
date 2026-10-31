<p align="center">
  <img src="https://raw.githubusercontent.com/KarnesTH/fsg/main/assets/logo.svg" alt="fsg logo" width="128" />
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
- Keeps a marked section of your README up to date, with a check mode for CI
- Sets up the commit hook for you: extends an existing `.pre-commit-config.yaml` or the native git hook, never overwrites
- Limit the depth, render directories only or exclude entries by glob pattern
- Options can live in `.fsg.toml` or `[tool.fsg]` in `pyproject.toml`
- Output is wrapped in a `plaintext` code fence (optional) and always written as UTF-8
- Optional ASCII branches (`|--`, `` `-- ``) for environments without Unicode support

## Installation

Requires Python 3.11+ and git (optional, for `.gitignore` support).

```bash
uv tool install fsg   # or: pipx install fsg
uvx fsg               # run without installing
```

## Usage

```bash
fsg [options] [path]
```

| Argument                         | Description                                                                 |
|----------------------------------|-----------------------------------------------------------------------------|
| `path`                           | Directory to render (default: current directory)                            |
| `-d N`, `--depth N`              | Render only the first N levels below the root                               |
| `--dirs-only`, `--no-dirs-only`  | Render directories only                                                     |
| `-e`, `--exclude PATTERN`        | Leave out entries whose name or relative path matches the glob (repeatable) |
| `--fence`, `--no-fence`          | Wrap the tree in a Markdown code fence (default: on)                        |
| `--ascii`, `--no-ascii`          | Draw the tree with ASCII instead of box-drawing characters                  |
| `-u`, `--update FILE`            | Write the tree between the fsg markers of FILE                              |
| `-c`, `--check FILE`             | Exit with status 1 when the tree in FILE is out of date                     |
| `--setup-hook FILE`              | Run `fsg --update FILE` on every commit                                     |
| `-h`, `--help`                   | Show the help text and exit                                                 |
| `-V`, `--version`                | Show the version and exit                                                   |

Example:

```bash
fsg src --depth 2
```
<!-- fsg:start -->
```plaintext
src/
└── fsg/
    ├── hooks/
    ├── trees/
    ├── __init__.py
    ├── __main__.py
    ├── cli.py
    ├── config.py
    ├── constants.py
    └── readme_section.py
```
<!-- fsg:end -->

## Configuration

With `--update` and `--check`, the path and all options not given on the command line are read from `.fsg.toml`
or the `[tool.fsg]` table in `pyproject.toml`, searched from the directory of the target file upwards.
`path` is relative to the config file. Command line options take precedence, exclude patterns are combined.
Plain `fsg` ignores the config.

```toml
[tool.fsg]
path = "src"
depth = 2
dirs-only = false
exclude = ["*.log", "docs/api"]
fence = true
ascii = false
```

## Keep your README up to date

Add the markers where the tree should appear:

```markdown
<!-- fsg:start -->
<!-- fsg:end -->
```

```bash
fsg --update README.md       # writes the tree between the markers
fsg --check README.md        # exit 1 if outdated, 2 if the file or markers are missing
fsg --setup-hook README.md   # updates the tree on every commit
```

`--setup-hook` adds fsg to an existing `.pre-commit-config.yaml`. Without one, it adds a step to the git
`pre-commit` hook that updates the tree and stops the commit so you can stage the change.

### pre-commit

To add the hook by hand:

```yaml
repos:
  - repo: https://github.com/KarnesTH/fsg
    rev: v0.1.0
    hooks:
      - id: fsg          # updates README.md
      # - id: fsg-check  # only checks, e.g. in CI
```

Use `args` for another file, e.g. `args: [--update, docs/structure.md]`.

## Development

```bash
git clone https://github.com/KarnesTH/fsg.git
cd fsg
uv sync
uv run pytest
```