import pytest

from fsg.constants import STYLES
from fsg.glyphs import Glyphs
from fsg.tree_comments import TreeComments


class TestParse:
    """Covers reading comments from a rendered tree."""

    def test_maps_comments_to_paths(self) -> None:
        """Returns the comments of root, directories and nested files keyed by relative path."""

        block = (
            "\n```plaintext\n"
            "src/          # sources\n"
            "├── fsg/      # package\n"
            "│   ├── a.py\n"
            "│   └── cli.py  # entry point\n"
            "└── main.py   # script\n"
            "```\n"
        )
        assert TreeComments().parse(block) == {
            "": "sources",
            "fsg": "package",
            "fsg/cli.py": "entry point",
            "main.py": "script",
        }

    @pytest.mark.parametrize("style", list(STYLES))
    def test_reads_every_style(self, style: str) -> None:
        """Finds the entry names behind the glyphs of every built-in style."""

        glyphs = Glyphs.from_style(style)
        block = (
            f"root/\n"
            f"{glyphs.branch}a/\n"
            f"{glyphs.pipe}{glyphs.last}deep.py  # deep\n"
            f"{glyphs.last}b.py  # top\n"
        )
        assert TreeComments().parse(block) == {"a/deep.py": "deep", "b.py": "top"}

    def test_reads_custom_glyphs(self) -> None:
        """Uses the characters of custom glyphs passed to the constructor."""

        block = "root/\n*~~ a/\n:   *~~ x.py  # x\n"
        assert TreeComments({"*", "~", ":"}).parse(block) == {"a/x.py": "x"}

    def test_keeps_names_starting_with_glyph_characters(self) -> None:
        """Takes the name from after the last space of the connector, so leading dashes stay part of the name."""

        block = "root/\n|-- -config  # flags\n`-- --x/\n    `-- y  # nested\n"
        assert TreeComments().parse(block) == {"-config": "flags", "--x/y": "nested"}

    def test_requires_two_spaces_before_hash(self) -> None:
        """Treats a hash after a single space as part of the name."""

        assert TreeComments().parse("root/\n└── c#.md # no\n") == {}

    def test_skips_summary_line(self) -> None:
        """Ignores the summary below the tree."""

        block = "root/\n└── a.py  # x\n\n1 directory, 1 file\n"
        assert TreeComments().parse(block) == {"a.py": "x"}

    def test_returns_nothing_for_empty_block(self) -> None:
        """Returns an empty mapping for a block without lines."""

        assert TreeComments().parse("\n") == {}