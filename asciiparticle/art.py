"""Sprite art used by the bundled scenes."""
from __future__ import annotations

from .sprite import Animation, Frame, Sprite

HERO_PALETTE = {"h": 230, "c": 51, "l": 39}
HERO_MASK = " h \nccc\nlll"


def _hero(*rows: str) -> Frame:
    return Frame.from_art("\n".join(rows), HERO_MASK, HERO_PALETTE)


def hero() -> Sprite:
    """3x3 stick-figure wanderer, facing right."""
    return Sprite({
        "idle": Animation([_hero(" o ", "/|\\", "/ \\"), _hero(" o ", "/|\\", "| |")], fps=1.5),
        "walk": Animation([
            _hero(" o ", "/|\\", "/ \\"),
            _hero(" o ", "-|\\", " |\\"),
            _hero(" o ", "/|\\", " | "),
            _hero(" o ", "/|-", "/| "),
        ], fps=10),
        "jump": Animation([_hero("\\o/", " | ", "/ \\")], fps=1),
        "fall": Animation([_hero(" o ", "/|\\", "< >")], fps=1),
        "cast": Animation([_hero(" o_", "/| ", "/ \\")], fps=1),
    }, start="idle")


MOON = Frame.from_art(
    """
  .-~~-.
 /  ::  \\
|  ::::  |
 \\  ::  /
  '-..-'
""",
    """
  mmmmmm
 mmmddmmm
mmmddddmmm
 mmmddmmm
  mmmmmm
""",
    {"m": 230, "d": 187},
    solid=True,
)

TREE = Frame.from_art(
    """
    ^
   /^\\
  /^^^\\
 /^^^^^\\
/^^^^^^^\\
   |||
""",
    """
    a
   bab
  bbabb
 bbbabbb
bbbbabbbb
   ttt
""",
    {"a": 34, "b": 28, "t": 94},
)

LOGS = Frame.from_art(
    " \\ / \n(=X=)",
    " b b \nbbxbb",
    {"b": 130, "x": 208},
)
