"""Forces and fields that move particles (and grass).

Every force has ``apply(particle, dt)`` so it can sit in
``ParticleSystem.forces``. ``WindField`` is special: particles follow it
through their emitter's ``wind`` coupling, and ``GrassField`` reads it to
bend blades, so grass and particles feel the same gusts.
"""
from __future__ import annotations

import math
from typing import List, Tuple

from .noise import Noise


class WindField:
    """Horizontal wind with gusts that roll across the screen downstream.

    ``base`` is the steady wind in cells/second (negative blows left),
    ``gust`` how much stronger gusts get, ``travel`` how fast gust fronts
    move. ``boost()`` adds a short burst on top.
    """

    def __init__(self, noise: Noise, base: float = 5.0, gust: float = 8.0, scale: float = 0.035,
                 travel: float = 14.0, turbulence: float = 1.5) -> None:
        self.noise = noise
        self.base = base
        self.gust = gust
        self.scale = scale
        self.travel = travel
        self.turbulence = turbulence
        self.time = 0.0
        self.extra = 0.0
        self._cols: List[float] = []

    @property
    def direction(self) -> int:
        return -1 if self.base < 0 else 1

    def boost(self, amount: float) -> None:
        self.extra += amount

    def update(self, dt: float, width: int) -> None:
        self.time += dt
        self.extra *= math.exp(-dt * 1.1)
        d = self.direction
        off = self.time * self.travel * d
        s = self.scale
        n1 = self.noise.noise1
        base = self.base + self.extra * d
        gust = self.gust * d
        cols = []
        for x in range(max(1, width)):
            g = n1((x - off) * s)
            g2 = n1((x - off) * s * 3.1 + 50.0)
            cols.append(base + gust * (max(0.0, g) * 1.4 + 0.25 * g2))
        self._cols = cols

    def strength_at(self, x: float) -> float:
        cols = self._cols
        if not cols:
            return self.base
        i = int(x)
        if i < 0:
            i = 0
        elif i >= len(cols):
            i = len(cols) - 1
        return cols[i]

    def mean(self) -> float:
        cols = self._cols
        return sum(cols) / len(cols) if cols else self.base

    def sample(self, x: float, y: float) -> Tuple[float, float]:
        wy = self.turbulence * math.sin(x * 0.21 + y * 0.7 + self.time * 2.3)
        return self.strength_at(x), wy


class Vortex:
    """Swirl around a point. Negative ``strength`` spins the other way."""

    def __init__(self, x: float, y: float, strength: float = 20.0, pull: float = 2.0,
                 radius: float = 25.0, aspect: float = 0.5, enabled: bool = True) -> None:
        self.x = x
        self.y = y
        self.strength = strength
        self.pull = pull
        self.radius = radius
        self.aspect = aspect
        self.enabled = enabled

    def apply(self, p, dt: float) -> None:
        if not self.enabled:
            return
        dx = p.x - self.x
        dy = (p.y - self.y) / self.aspect
        r = math.sqrt(dx * dx + dy * dy) + 0.5
        fall = 1.0 / (1.0 + (r / self.radius) ** 2)
        tx = -dy / r * self.strength * fall
        ty = dx / r * self.strength * fall
        rx = -dx / r * self.pull * fall * 10.0
        ry = -dy / r * self.pull * fall * 10.0
        p.vx += (tx + rx) * dt
        p.vy += (ty + ry) * self.aspect * dt


class Attractor:
    """Pull toward (or, with negative strength, push from) a point."""

    def __init__(self, x: float, y: float, strength: float = 30.0, radius: float = 12.0,
                 aspect: float = 0.5, enabled: bool = True) -> None:
        self.x = x
        self.y = y
        self.strength = strength
        self.radius = radius
        self.aspect = aspect
        self.enabled = enabled

    def apply(self, p, dt: float) -> None:
        if not self.enabled:
            return
        dx = self.x - p.x
        dy = (self.y - p.y) / self.aspect
        r = math.sqrt(dx * dx + dy * dy) + 0.5
        f = self.strength / (1.0 + (r / self.radius) ** 2)
        p.vx += dx / r * f * dt
        p.vy += dy / r * f * self.aspect * dt


class HomeSpring:
    """Spring each particle back to the home point stored in ``p.data``."""

    def __init__(self, strength: float = 24.0, damping: float = 5.0) -> None:
        self.strength = strength
        self.damping = damping
        self.scale = 1.0

    def apply(self, p, dt: float) -> None:
        home = p.data
        if home is None or self.scale <= 0.0:
            return
        k = self.strength * self.scale
        damp = self.damping * (0.4 + 0.6 * self.scale)
        p.vx += ((home[0] - p.x) * k - p.vx * damp) * dt
        p.vy += ((home[1] - p.y) * k - p.vy * damp) * dt


class FlowField:
    """Divergence-free curl-noise flow, sampled on a coarse grid for speed."""

    def __init__(self, noise: Noise, strength: float = 12.0, scale: float = 0.05,
                 evolve: float = 0.15, cell: int = 4, follow: float = 2.0, aspect: float = 0.5) -> None:
        self.noise = noise
        self.strength = strength
        self.scale = scale
        self.evolve = evolve
        self.cell = cell
        self.follow = follow
        self.aspect = aspect
        self.time = 0.0
        self._grid: List[List[Tuple[float, float]]] = []

    def update(self, dt: float, width: int, height: int) -> None:
        self.time += dt
        cell = self.cell
        gw = width // cell + 2
        gh = height // cell + 2
        n2 = self.noise.noise2
        s = self.scale
        t = self.time * self.evolve
        e = 0.35
        k = self.strength / (2.0 * e)
        grid = []
        for gy in range(gh):
            y = gy * cell * s * 2.0 + t * 0.7
            row = []
            for gx in range(gw):
                x = gx * cell * s + t
                vx = (n2(x, y + e) - n2(x, y - e)) * k
                vy = -(n2(x + e, y) - n2(x - e, y)) * k * self.aspect
                row.append((vx, vy))
            grid.append(row)
        self._grid = grid

    def at(self, x: float, y: float) -> Tuple[float, float]:
        grid = self._grid
        if not grid:
            return 0.0, 0.0
        gy = int(y / self.cell)
        gx = int(x / self.cell)
        gy = 0 if gy < 0 else (len(grid) - 1 if gy >= len(grid) else gy)
        row = grid[gy]
        gx = 0 if gx < 0 else (len(row) - 1 if gx >= len(row) else gx)
        return row[gx]

    def apply(self, p, dt: float) -> None:
        fx, fy = self.at(p.x, p.y)
        k = self.follow * dt
        p.vx += (fx - p.vx) * k
        p.vy += (fy - p.vy) * k
