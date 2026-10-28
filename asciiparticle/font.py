"""A 5x5 block font, used to turn text into particle targets."""
from __future__ import annotations

from typing import List, Sequence, Tuple

GLYPHS = {
    "A": (" ### ", "#   #", "#####", "#   #", "#   #"),
    "B": ("#### ", "#   #", "#### ", "#   #", "#### "),
    "C": (" ####", "#    ", "#    ", "#    ", " ####"),
    "D": ("#### ", "#   #", "#   #", "#   #", "#### "),
    "E": ("#####", "#    ", "#### ", "#    ", "#####"),
    "F": ("#####", "#    ", "#### ", "#    ", "#    "),
    "G": (" ####", "#    ", "#  ##", "#   #", " ####"),
    "H": ("#   #", "#   #", "#####", "#   #", "#   #"),
    "I": ("#####", "  #  ", "  #  ", "  #  ", "#####"),
    "J": ("#####", "   # ", "   # ", "#  # ", " ##  "),
    "K": ("#   #", "#  # ", "###  ", "#  # ", "#   #"),
    "L": ("#    ", "#    ", "#    ", "#    ", "#####"),
    "M": ("#   #", "## ##", "# # #", "#   #", "#   #"),
    "N": ("#   #", "##  #", "# # #", "#  ##", "#   #"),
    "O": (" ### ", "#   #", "#   #", "#   #", " ### "),
    "P": ("#### ", "#   #", "#### ", "#    ", "#    "),
    "Q": (" ### ", "#   #", "# # #", "#  # ", " ## #"),
    "R": ("#### ", "#   #", "#### ", "#  # ", "#   #"),
    "S": (" ####", "#    ", " ### ", "    #", "#### "),
    "T": ("#####", "  #  ", "  #  ", "  #  ", "  #  "),
    "U": ("#   #", "#   #", "#   #", "#   #", " ### "),
    "V": ("#   #", "#   #", "#   #", " # # ", "  #  "),
    "W": ("#   #", "#   #", "# # #", "## ##", "#   #"),
    "X": ("#   #", " # # ", "  #  ", " # # ", "#   #"),
    "Y": ("#   #", " # # ", "  #  ", "  #  ", "  #  "),
    "Z": ("#####", "   # ", "  #  ", " #   ", "#####"),
    "0": (" ### ", "#  ##", "# # #", "##  #", " ### "),
    "1": ("  #  ", " ##  ", "  #  ", "  #  ", " ### "),
    "2": (" ### ", "#   #", "  ## ", " #   ", "#####"),
    "3": ("#### ", "    #", " ### ", "    #", "#### "),
    "4": ("#   #", "#   #", "#####", "    #", "    #"),
    "5": ("#####", "#    ", "#### ", "    #", "#### "),
    "6": (" ### ", "#    ", "#### ", "#   #", " ### "),
    "7": ("#####", "    #", "   # ", "  #  ", "  #  "),
    "8": (" ### ", "#   #", " ### ", "#   #", " ### "),
    "9": (" ### ", "#   #", " ####", "    #", " ### "),
    "!": ("  #  ", "  #  ", "  #  ", "     ", "  #  "),
    "&": (" ##  ", "#  # ", " ## #", "#  # ", " ## #"),
    ".": ("     ", "     ", "     ", "     ", "  #  "),
    "-": ("     ", "     ", " ### ", "     ", "     "),
    "?": (" ### ", "#   #", "  ## ", "     ", "  #  "),
    " ": ("   ", "   ", "   ", "   ", "   "),
}

HEIGHT = 5


def text_width(text: str, sx: int = 1) -> int:
    widths = [len(GLYPHS.get(ch, GLYPHS["?"])[0]) for ch in text.upper()]
    return (sum(widths) + max(0, len(widths) - 1)) * sx


def text_points(text: str, x0: float = 0, y0: float = 0, sx: int = 1,
                sy: int = 1) -> List[Tuple[float, float]]:
    """Centres of the cells covered by every lit pixel, each ``sx`` by ``sy`` cells.

    Centres (x.5, y.5) rather than corners, so particles that settle a hair
    short of their target still land in the right cell.
    """
    pts = []
    cx = 0
    for ch in text.upper():
        rows = GLYPHS.get(ch, GLYPHS["?"])
        for ry, row in enumerate(rows):
            for rx, px in enumerate(row):
                if px != " ":
                    for k in range(sx):
                        for j in range(sy):
                            pts.append((x0 + (cx + rx) * sx + k + 0.5, y0 + ry * sy + j + 0.5))
        cx += len(rows[0]) + 1
    return pts


def block_points(lines: Sequence[str], width: int, height: int,
                 gap: int = 2) -> List[Tuple[float, float]]:
    """Points for several centred lines, scaled up as far as the area allows.

    Cells are about twice as tall as wide, so pixels are 2 cells wide when
    they fit, and 4x2 cells when there is room for that too.
    """
    widest = max(text_width(line) for line in lines)
    sx = 2 if widest * 2 <= width - 4 else 1
    sy = 1
    if sx == 2 and len(lines) * HEIGHT * 2 + (len(lines) - 1) * gap <= height - 4:
        sy = 2
        if widest * 4 <= width - 4:
            sx = 4
    total_h = len(lines) * HEIGHT * sy + (len(lines) - 1) * gap
    y = max(0, (height - total_h) // 2)
    pts: List[Tuple[float, float]] = []
    for line in lines:
        x = max(0, (width - text_width(line, sx)) // 2)
        pts.extend(text_points(line, x, y, sx, sy))
        y += HEIGHT * sy + gap
    return pts
