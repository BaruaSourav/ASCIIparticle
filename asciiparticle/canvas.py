"""A grid of character cells that scenes draw into each frame."""
from __future__ import annotations

from typing import List, Optional, Tuple

from .color import DEFAULT


class Canvas:
    """Flat arrays of characters, foreground and background colours.

    Coordinates are floats or ints; anything outside the grid is clipped, so
    callers never need to bounds-check particles themselves.
    """

    __slots__ = ("width", "height", "chars", "fg", "bg")

    def __init__(self, width: int, height: int) -> None:
        self.width = max(1, int(width))
        self.height = max(1, int(height))
        self.clear()

    def resize(self, width: int, height: int) -> None:
        self.width = max(1, int(width))
        self.height = max(1, int(height))
        self.clear()

    def clear(self, bg: int = DEFAULT) -> None:
        n = self.width * self.height
        self.chars: List[str] = [" "] * n
        self.fg: List[int] = [DEFAULT] * n
        self.bg: List[int] = [bg] * n

    def put(self, x: float, y: float, ch: str, fg: int = DEFAULT, bg: Optional[int] = None) -> None:
        """Draw one character. ``bg=None`` keeps whatever background is there."""
        if x < 0 or y < 0:
            return
        xi = int(x)
        yi = int(y)
        if xi >= self.width or yi >= self.height:
            return
        i = yi * self.width + xi
        self.chars[i] = ch
        self.fg[i] = fg
        if bg is not None:
            self.bg[i] = bg

    def set_bg(self, x: float, y: float, bg: int) -> None:
        if x < 0 or y < 0:
            return
        xi = int(x)
        yi = int(y)
        if xi < self.width and yi < self.height:
            self.bg[yi * self.width + xi] = bg

    def get(self, x: int, y: int) -> Optional[Tuple[str, int, int]]:
        if 0 <= x < self.width and 0 <= y < self.height:
            i = y * self.width + x
            return self.chars[i], self.fg[i], self.bg[i]
        return None

    def text(self, x: float, y: float, s: str, fg: int = DEFAULT, bg: Optional[int] = None) -> None:
        for i, ch in enumerate(s):
            self.put(x + i, y, ch, fg, bg)

    def fill(self, x: int, y: int, w: int, h: int, ch: str = " ",
             fg: int = DEFAULT, bg: Optional[int] = None) -> None:
        for yy in range(max(0, y), min(self.height, y + h)):
            for xx in range(max(0, x), min(self.width, x + w)):
                self.put(xx, yy, ch, fg, bg)

    def lines(self) -> List[str]:
        w = self.width
        return ["".join(self.chars[y * w:(y + 1) * w]) for y in range(self.height)]
