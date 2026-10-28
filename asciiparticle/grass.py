"""Wind-blown grass: one spring-driven blade per column."""
from __future__ import annotations

import math
import random
from typing import List, Optional, Sequence, Tuple

from . import color as C
from .canvas import Canvas
from .forces import WindField

GREENS = C.gradient(["#005f00", "#008700", "#5faf00", "#afd75f", "#d7ff87"], 6)
FLOWERS = ((("*", 213), ("*", 219), ("o", 228), ("@", 225), ("*", 159), ("o", 216)))
DIRT_CHARS = " .,:'`;"
DIRT_COLORS = (94, 130, 58, 95, 136)


class Blade:
    __slots__ = ("x", "height", "stiff", "angle", "vel", "phase", "ramp", "tip")

    def __init__(self, x: int, height: int, stiff: float, phase: float,
                 ramp: List[int], tip: Optional[Tuple[str, int]]) -> None:
        self.x = x
        self.height = height
        self.stiff = stiff
        self.phase = phase
        self.ramp = ramp
        self.tip = tip
        self.angle = 0.0
        self.vel = 0.0


def _blade_char(lean: float) -> str:
    if lean > 1.05:
        return "~"
    if lean > 0.3:
        return "/"
    if lean < -1.05:
        return "~"
    if lean < -0.3:
        return "\\"
    return "|"


class GrassField:
    """A row of grass blades rooted on ``ground_y``.

    Blades are damped springs: wind from a ``WindField`` sets where they want
    to lean, ``disturb`` lets players and spells shove them around.
    """

    def __init__(self, rng: random.Random, width: int, ground_y: int, *, density: float = 0.92,
                 heights: Tuple[int, int] = (1, 4), flowers: float = 0.05,
                 ramp: Sequence[int] = GREENS) -> None:
        self.rng = rng
        self.density = density
        self.heights = heights
        self.flowers = flowers
        self.palette = list(ramp)
        self.time = 0.0
        self.blades: List[Blade] = []
        self.dirt: List[Tuple[str, int]] = []
        self.regenerate(width, ground_y)

    def regenerate(self, width: int, ground_y: int) -> None:
        rng = self.rng
        self.width = width
        self.ground_y = ground_y
        lo, hi = self.heights
        pal = self.palette
        blades = []
        for x in range(width):
            if rng.random() > self.density:
                continue
            h = rng.randint(lo, hi)
            if rng.random() < 0.15:
                h += 1
            start = rng.randint(0, 1)
            ramp = [pal[min(len(pal) - 1, start + int(i * (len(pal) - start) / h))] for i in range(h)]
            tip = rng.choice(FLOWERS) if rng.random() < self.flowers else None
            blades.append(Blade(x, h, rng.uniform(0.7, 1.4), rng.uniform(0, math.tau), ramp, tip))
        self.blades = blades
        self.dirt = [(rng.choice(DIRT_CHARS), rng.choice(DIRT_COLORS)) for _ in range(width * 8)]

    def clear_range(self, x0: float, x1: float) -> None:
        self.blades = [b for b in self.blades if not (x0 <= b.x <= x1)]

    def disturb(self, x: float, radius: float, push: float, direction: Optional[int] = None) -> None:
        """Shove blades within ``radius`` of ``x``: away from it, or toward ``direction``."""
        for b in self.blades:
            d = b.x - x
            if -radius < d < radius:
                sign = direction if direction is not None else (1 if d >= 0 else -1)
                b.vel += push * (1.0 - abs(d) / radius) * sign

    def update(self, dt: float, wind: Optional[WindField] = None) -> None:
        self.time += dt
        t = self.time
        for b in self.blades:
            w = wind.strength_at(b.x) if wind is not None else 0.0
            target = w / (9.0 * b.stiff) + 0.07 * math.sin(t * 3.0 + b.phase)
            if target > 1.4:
                target = 1.4
            elif target < -1.4:
                target = -1.4
            acc = (target - b.angle) * 32.0 * b.stiff - b.vel * 5.0
            b.vel += acc * dt
            b.angle += b.vel * dt
            if b.angle > 1.6:
                b.angle, b.vel = 1.6, 0.0
            elif b.angle < -1.6:
                b.angle, b.vel = -1.6, 0.0

    def tip(self, b: Blade) -> Tuple[float, float]:
        off = 0.0
        for seg in range(b.height):
            off += b.angle * (seg + 1) / b.height * 0.85
        return b.x + off, self.ground_y - b.height + 1

    def draw(self, canvas: Canvas) -> None:
        gy = self.ground_y
        put = canvas.put
        for b in self.blades:
            a = b.angle
            h = b.height
            off = 0.0
            for seg in range(h):
                lean = a * (seg + 1) / h
                off += lean * 0.85
                if seg == h - 1 and b.tip is not None:
                    ch, col = b.tip
                else:
                    ch, col = _blade_char(lean), b.ramp[seg]
                put(b.x + round(off), gy - seg, ch, col)

    def draw_ground(self, canvas: Canvas, bottom: int) -> None:
        dirt = self.dirt
        w = self.width
        n = len(dirt)
        for row, y in enumerate(range(self.ground_y + 1, bottom)):
            for x in range(min(w, canvas.width)):
                ch, col = dirt[(row * w + x) % n]
                canvas.put(x, y, ch, col, 233)
