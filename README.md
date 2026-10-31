<p align="center">
  <img src="https://raw.githubusercontent.com/KarnesTH/fsg/main/assets/logo.svg" alt="fsg logo" width="128" />
</p>

<h1 align="center">fsg</h1>

<p align="center">
  <img src="https://img.shields.io/badge/version-0.4.0-blue" alt="Version 0.4.0" />
  <img src="https://img.shields.io/badge/python-3.11%2B-3776AB?logo=python&logoColor=white" alt="Python 3.11+" />
  <img src="https://img.shields.io/badge/dependencies-none-brightgreen" alt="No dependencies" />
  <img src="https://img.shields.io/badge/license-MIT-green" alt="MIT License" />
</p>

<p align="center">Generates clean directory trees that respect .gitignore and keep your docs up to date.</p>

<p align="center">
  <img src="https://raw.githubusercontent.com/KarnesTH/fsg/main/docs/demo.gif" alt="fsg demo" />
</p>

## Features

- Inside a git repository, only files git tracks or would track are listed (`.gitignore` is respected)
- Outside a repository, common generated and tool directories are skipped (`.venv`, `__pycache__`, `node_modules`, `target`, `.idea`, …)
- Directories first, entries sorted case-insensitively, empty directories omitted
- Keeps marked sections of your README up to date, with a check mode for CI
- Comments next to entries survive every update and stay aligned
- Several trees per file, each with its own options in the start marker
- Sets up the commit hook for you: extends an existing `.pre-commit-config.yaml` or the native git hook, never overwrites
- Limit the depth, render directories only, or include and exclude entries by glob pattern
- Options can live in `.fsg.toml` or `[tool.fsg]` in `pyproject.toml`
- Output is wrapped in a `plaintext` code fence (optional) and always written as UTF-8
- Built-in styles (`unicode`, `ascii`, `rounded`, `heavy`, `double`) or your own glyphs
- Optional summary line with the number of directories and files
- Copies the tree to the clipboard with `--copy`

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

| Argument                        | Description                                                                               |
|---------------------------------|-------------------------------------------------------------------------------------------|
| `path`                          | Directory to render (default: current directory)                                          |
| `-d N`, `--depth N`             | Render only the first N levels below the root                                             |
| `--dirs-only`, `--no-dirs-only` | Render directories only                                                                   |
| `-e`, `--exclude PATTERN`       | Leave out entries whose name or relative path matches the glob (repeatable)               |
| `-i`, `--include PATTERN`       | Show only entries whose name or relative path matches the glob (repeatable, exclude wins) |
| `--fence`, `--no-fence`         | Wrap the tree in a Markdown code fence (default: on)                                      |
| `--summary`, `--no-summary`     | Add a line with the number of directories and files (default: off)                        |
| `-s`, `--style NAME`            | Draw the tree in a built-in style: unicode, ascii, rounded, heavy, double                 |
| `--glyph KEY=VALUE`             | Replace one glyph of the style: branch, last, pipe or space (repeatable)                  |
| `--ascii`, `--no-ascii`         | Short for `--style ascii`, also uses ASCII status symbols                                 |
| `--copy`                        | Copy the tree to the clipboard instead of printing it                                     |
| `-u`, `--update FILE`           | Write the tree between the fsg markers of FILE                                            |
| `-c`, `--check FILE`            | Exit with status 1 when the tree in FILE is out of date                                   |
| `--setup-hook FILE`             | Run `fsg --update FILE` on every commit                                                   |
| `-h`, `--help`                  | Show the help text and exit                                                               |
| `-V`, `--version`               | Show the version and exit                                                                 |

Example:

```bash
fsg src --depth 2
```
<!-- fsg:start -->
```plaintext
src/
└── fsg/
    ├── hooks/            # commit hook setup
    ├── trees/            # git and plain directory walk
    ├── __init__.py
    ├── __main__.py
    ├── cli.py            # arguments and modes
    ├── clipboard.py      # --copy
    ├── config.py         # .fsg.toml and [tool.fsg]
    ├── console.py        # status lines
    ├── constants.py      # styles and ignored names
    ├── errors.py         # errors with hints
    ├── executable.py     # safe PATH lookup
    ├── git.py            # git commands
    ├── glyphs.py         # tree styles
    ├── marked_file.py    # marker blocks
    ├── section.py        # marker options
    ├── text_file.py      # atomic UTF-8 writes
    └── tree_comments.py  # comments kept on update
```
<!-- fsg:end -->

### Filter

<p align="center">
  <img src="https://raw.githubusercontent.com/KarnesTH/fsg/main/docs/demos/filter.gif" alt="fsg include and exclude demo" />
</p>

### Styles and summary

<p align="center">
  <img src="https://raw.githubusercontent.com/KarnesTH/fsg/main/docs/demos/styles.gif" alt="fsg styles demo" />
</p>

Your own glyphs must all have the same width:

```bash
fsg --glyph branch="+-- " --glyph last="\\-- " --glyph pipe=":   "
```

## Configuration

With `--update` and `--check`, the path and all options not given on the command line are read from the start marker
of each block, then from `.fsg.toml` or the `[tool.fsg]` table in `pyproject.toml`, searched from the directory of the
target file upwards. `path` is relative to the config file. Command line options take precedence over marker options,
marker options over the config; include and exclude patterns are combined. Plain `fsg` ignores the config.

```toml
[tool.fsg]
path = "src"
depth = 2
dirs-only = false
exclude = ["*.log", "docs/api"]
include = []
fence = true
summary = false
style = "unicode"

[tool.fsg.glyphs]
last = "╰── "
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

<p align="center">
  <img src="https://raw.githubusercontent.com/KarnesTH/fsg/main/docs/demos/update-check.gif" alt="fsg update and check demo" />
</p>

Comments written after an entry, separated by at least two spaces, are kept on every update and aligned:

```plaintext
src/
├── cli.py     # argument parsing
└── config.py  # .fsg.toml and [tool.fsg]
```

### Several trees per file

Every marker pair is updated separately. Options in the start marker apply to that tree only;
`path` is relative to the file and must stay inside the repository:

```markdown
<!-- fsg:start path=backend depth=2 -->
<!-- fsg:end -->

<!-- fsg:start path=frontend/src dirs-only summary exclude=*.test.ts,mocks -->
<!-- fsg:end -->
```

Marker options: `path`, `depth`, `dirs-only`, `exclude`, `include`, `fence`, `style`, `summary`.

<p align="center">
  <img src="https://raw.githubusercontent.com/KarnesTH/fsg/main/docs/demos/sections.gif" alt="fsg sections demo" />
</p>

### Commit hook

`--setup-hook` adds fsg to an existing `.pre-commit-config.yaml`. Without one, it adds a step to the git
`pre-commit` hook that updates the tree and stops the commit so you can stage the change.

### pre-commit

To add the hook by hand:

```yaml
repos:
  - repo: https://github.com/KarnesTH/fsg
    rev: v0.4.0
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