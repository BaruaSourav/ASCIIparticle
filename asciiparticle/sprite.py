r"""ASCII-art sprites with per-character colours, animation and mirroring.

A frame is drawn from two same-shaped blocks of text: the art and a colour
mask whose characters are keys into a palette::

    cat = Frame.from_art(r'''
     /\_/\
    ( o.o )
     > ^ <
    ''', colors='''
     yyyyy
    yyggyyy
     yyyyy
    ''', palette={"y": 215, "g": 46})

Spaces in the art are transparent (see ``solid`` to fill them in).
"""
from __future__ import annotations

from typing import Dict, List, Mapping, Optional, Sequence, Tuple, Union

from .canvas import Canvas
from .color import DEFAULT

MIRROR = str.maketrans("/\\()<>[]{}", "\\/)(><][}{")

Cell = Tuple[int, int, str, int]


def _lines(text: str) -> List[str]:
    lines = text.split("\n")
    if lines and lines[0].strip() == "" and len(lines) > 1:
        lines = lines[1:]
    if lines and lines[-1].strip() == "":
        lines = lines[:-1]
    return lines


class Frame:
    """One still image. Drawn so that its ``anchor`` lands on (x, y)."""

    __slots__ = ("cells", "width", "height", "anchor")

    def __init__(self, cells: List[Cell], width: int, height: int,
                 anchor: Optional[Tuple[int, int]] = None) -> None:
        self.cells = cells
        self.width = width
        self.height = height
        self.anchor = anchor if anchor is not None else (width // 2, height - 1)

    @classmethod
    def from_art(cls, art: str, colors: Optional[str] = None,
                 palette: Optional[Mapping[str, int]] = None, default: int = 15,
                 transparent: str = " ", anchor: Optional[Tuple[int, int]] = None,
                 solid: bool = False) -> "Frame":
        """Build a frame from text art.

        With ``solid=True`` gaps between a row's first and last character are
        painted as blank cells, so whatever is behind doesn't show through.
        """
        lines = _lines(art)
        masks = _lines(colors) if colors else []
        palette = palette or {}
        cells: List[Cell] = []
        for y, line in enumerate(lines):
            mask = masks[y] if y < len(masks) else ""
            body = line.strip(transparent)
            first = len(line) - len(line.lstrip(transparent))
            last = first + len(body) - 1
            for x, ch in enumerate(line):
                if ch == transparent:
                    if solid and first < x < last:
                        cells.append((x, y, " ", default))
                    continue
                key = mask[x] if x < len(mask) else " "
                cells.append((x, y, ch, palette.get(key, default)))
        width = max((len(line) for line in lines), default=0)
        return cls(cells, width, len(lines), anchor)

    def flipped(self) -> "Frame":
        w = self.width
        cells = [(w - 1 - x, y, ch.translate(MIRROR), fg) for x, y, ch, fg in self.cells]
        return Frame(cells, w, self.height, (w - 1 - self.anchor[0], self.anchor[1]))

    def draw(self, canvas: Canvas, x: float, y: float, tint: Optional[int] = None,
             bg: Optional[int] = None) -> None:
        ox = int(round(x)) - self.anchor[0]
        oy = int(round(y)) - self.anchor[1]
        put = canvas.put
        for cx, cy, ch, fg in self.cells:
            put(ox + cx, oy + cy, ch, fg if tint is None else tint, bg)


class Animation:
    def __init__(self, frames: Sequence[Frame], fps: float = 8.0, loop: bool = True) -> None:
        self.frames = list(frames)
        self.fps = fps
        self.loop = loop
        self._flipped: Optional[List[Frame]] = None

    def flipped_frames(self) -> List[Frame]:
        if self._flipped is None:
            self._flipped = [f.flipped() for f in self.frames]
        return self._flipped

    @property
    def duration(self) -> float:
        return len(self.frames) / self.fps


class Sprite:
    """A set of named animations with a play head."""

    def __init__(self, animations: Union[Frame, Animation, Dict[str, Animation]],
                 start: Optional[str] = None) -> None:
        if isinstance(animations, Frame):
            animations = Animation([animations])
        if isinstance(animations, Animation):
            animations = {"default": animations}
        self.animations: Dict[str, Animation] = dict(animations)
        self.current = start or next(iter(self.animations))
        self.time = 0.0
        self.speed = 1.0

    def play(self, name: str, restart: bool = False) -> None:
        if name != self.current or restart:
            self.current = name
            self.time = 0.0

    def update(self, dt: float) -> None:
        self.time += dt * self.speed

    @property
    def animation(self) -> Animation:
        return self.animations[self.current]

    @property
    def finished(self) -> bool:
        anim = self.animation
        return not anim.loop and self.time >= anim.duration

    def frame(self, flip: bool = False) -> Frame:
        anim = self.animation
        frames = anim.flipped_frames() if flip else anim.frames
        i = int(self.time * anim.fps)
        i = i % len(frames) if anim.loop else min(i, len(frames) - 1)
        return frames[i]

    def draw(self, canvas: Canvas, x: float, y: float, flip: bool = False,
             tint: Optional[int] = None) -> None:
        self.frame(flip).draw(canvas, x, y, tint)


def tint_all(frame: Frame, fg: int = DEFAULT) -> Frame:
    return Frame([(x, y, ch, fg) for x, y, ch, _ in frame.cells], frame.width, frame.height, frame.anchor)
