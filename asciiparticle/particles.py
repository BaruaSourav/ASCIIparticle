"""Particle system: emitters spawn particles, forces push them, the canvas shows them.

Velocities are in cells per second. Terminal cells are roughly twice as tall
as they are wide, so emitters squash vertical launch speeds by ``aspect``
(0.5 by default) to make bursts look round instead of tall.
"""
from __future__ import annotations

import math
import random
from typing import Callable, List, Optional, Sequence, Tuple, Union

from .canvas import Canvas
from .color import DEFAULT

Range = Union[float, Tuple[float, float]]


def _pick(rng: random.Random, spec: Range) -> float:
    if isinstance(spec, (tuple, list)):
        return rng.uniform(spec[0], spec[1])
    return float(spec)


def dir_char(vx: float, vy: float) -> str:
    """A line character that points along a velocity."""
    ax = abs(vx)
    ay = abs(vy) * 2.0
    if ax > ay * 2.0:
        return "-"
    if ay > ax * 2.0:
        return "|"
    return "\\" if (vx > 0) == (vy > 0) else "/"


class Particle:
    __slots__ = ("x", "y", "vx", "vy", "age", "life", "em", "k", "ramp", "data")

    def __init__(self, x: float, y: float, vx: float, vy: float, life: float,
                 em: "Emitter", k: float, ramp: Optional[Sequence[int]] = None, data=None) -> None:
        self.x = x
        self.y = y
        self.vx = vx
        self.vy = vy
        self.age = 0.0
        self.life = life
        self.em = em
        self.k = k              # per-particle random in [0, 1) for variety
        self.ramp = ramp        # optional colour ramp overriding the emitter's
        self.data = data        # free slot for scene/force specific state


class Emitter:
    """Describes how particles are born and how they look.

    ``char_mode`` / ``color_mode`` choose glyphs and colours by ``"life"``
    (ramp from birth to death), ``"random"`` (fixed per particle) or, for
    glyphs only, ``"dir"`` (a line pointing along the velocity).
    """

    def __init__(self, x: float = 0.0, y: float = 0.0, *, rate: float = 0.0,
                 life: Range = (1.0, 2.0), speed: Range = (1.0, 4.0), angle: Range = (0.0, 360.0),
                 shape: str = "point", width: float = 0.0, height: float = 0.0,
                 chars: str = "*", colors: Sequence[int] = (15,), char_mode: str = "life",
                 color_mode: str = "life", gravity: float = 0.0, drag: float = 0.0,
                 wind: float = 0.0, forces: bool = True, collide: Optional[str] = None,
                 bounce: float = 0.4, aspect: float = 0.5, velocity: Tuple[float, float] = (0.0, 0.0),
                 bg: Optional[int] = None, active: bool = True, tag=None,
                 on_spawn: Optional[Callable[[Particle], None]] = None,
                 on_death: Optional[Callable[[Particle], None]] = None) -> None:
        self.x = x
        self.y = y
        self.rate = rate
        self.life = life
        self.speed = speed
        self.angle = angle
        self.shape = shape
        self.width = width
        self.height = height
        self.chars = chars
        self.colors = list(colors)
        self.char_mode = char_mode
        self.color_mode = color_mode
        self.gravity = gravity
        self.drag = drag
        self.wind = wind
        self.forces = forces
        self.collide = collide
        self.bounce = bounce
        self.aspect = aspect
        self.velocity = velocity
        self.bg = bg
        self.active = active
        self.tag = tag
        self.on_spawn = on_spawn
        self.on_death = on_death
        self.system: Optional["ParticleSystem"] = None
        self._acc = 0.0

    def update(self, dt: float) -> None:
        if not self.active or self.rate <= 0 or self.system is None:
            return
        self._acc += self.rate * dt
        n = int(self._acc)
        if n:
            self._acc -= n
            self.emit(n)

    def emit(self, n: int = 1, x: Optional[float] = None, y: Optional[float] = None) -> List[Particle]:
        system = self.system
        if system is None:
            raise RuntimeError("emitter is not attached to a ParticleSystem")
        rng = system.rng
        ox = self.x if x is None else x
        oy = self.y if y is None else y
        out = []
        for _ in range(n):
            px, py = ox, oy
            shape = self.shape
            if shape == "line":
                px += rng.uniform(-self.width / 2, self.width / 2)
            elif shape == "rect":
                px += rng.uniform(-self.width / 2, self.width / 2)
                py += rng.uniform(-self.height / 2, self.height / 2)
            elif shape == "circle":
                r = self.width / 2 * math.sqrt(rng.random())
                a = rng.uniform(0.0, math.tau)
                px += math.cos(a) * r
                py += math.sin(a) * r * self.aspect
            a = math.radians(_pick(rng, self.angle))
            s = _pick(rng, self.speed)
            p = Particle(px, py,
                         math.cos(a) * s + self.velocity[0],
                         -math.sin(a) * s * self.aspect + self.velocity[1],
                         max(0.01, _pick(rng, self.life)), self, rng.random())
            if self.on_spawn is not None:
                self.on_spawn(p)
            system.particles.append(p)
            out.append(p)
        return out


class ParticleSystem:
    """Owns particles, emitters and forces.

    A force is any object with ``apply(particle, dt)``; see ``forces.py``.
    ``wind`` is a ``WindField``; each emitter's ``wind`` sets how strongly its
    particles follow it. ``floor`` is the y particles with ``collide`` hit.
    """

    def __init__(self, rng: Optional[random.Random] = None, *, max_particles: int = 4000,
                 wind=None, floor: Optional[float] = None) -> None:
        self.rng = rng or random.Random()
        self.max_particles = max_particles
        self.wind = wind
        self.floor = floor
        self.bounds: Optional[Tuple[int, int]] = None
        self.particles: List[Particle] = []
        self.emitters: List[Emitter] = []
        self.forces: list = []

    def add(self, emitter: Emitter) -> Emitter:
        """Attach an emitter that spawns continuously at its ``rate``."""
        emitter.system = self
        self.emitters.append(emitter)
        return emitter

    def attach(self, emitter: Emitter) -> Emitter:
        """Attach an emitter used only for manual ``emit``/``spawn`` calls."""
        emitter.system = self
        return emitter

    def remove(self, emitter: Emitter) -> None:
        if emitter in self.emitters:
            self.emitters.remove(emitter)

    def burst(self, x: float, y: float, n: int, **kwargs) -> List[Particle]:
        """One-shot explosion of ``n`` particles configured like an Emitter."""
        em = self.attach(Emitter(x, y, **kwargs))
        return em.emit(n)

    def spawn(self, em: Emitter, x: float, y: float, vx: float, vy: float, life: float,
              ramp: Optional[Sequence[int]] = None, data=None) -> Particle:
        """Add a single particle with an exact velocity."""
        em.system = self
        p = Particle(x, y, vx, vy, life, em, self.rng.random(), ramp, data)
        self.particles.append(p)
        return p

    def clear(self) -> None:
        self.particles = []

    def update(self, dt: float) -> None:
        for e in self.emitters:
            e.update(dt)
        wind = self.wind
        forces = self.forces
        floor = self.floor
        bounds = self.bounds
        if bounds is not None:
            min_x, max_x = -bounds[0] * 0.5, bounds[0] * 1.5
            min_y, max_y = -bounds[1] * 1.5, bounds[1] + 2.0
        alive: List[Particle] = []
        append = alive.append
        # on_death callbacks may append to self.particles while we iterate; the
        # new particles are picked up by this same loop.
        for p in self.particles:
            p.age += dt
            em = p.em
            if p.age >= p.life:
                if em.on_death is not None:
                    em.on_death(p)
                continue
            if em.wind and wind is not None:
                wx, wy = wind.sample(p.x, p.y)
                k = em.wind * dt
                if k > 1.0:
                    k = 1.0
                p.vx += (wx - p.vx) * k
                p.vy += (wy - p.vy) * k
            if em.forces:
                for f in forces:
                    f.apply(p, dt)
            if em.drag:
                d = 1.0 - em.drag * dt
                if d < 0.0:
                    d = 0.0
                p.vx *= d
                p.vy *= d
            p.vy += em.gravity * dt
            p.x += p.vx * dt
            p.y += p.vy * dt
            if em.collide is not None and floor is not None and p.y >= floor:
                if em.collide == "die":
                    p.y = floor
                    if em.on_death is not None:
                        em.on_death(p)
                    continue
                p.y = floor - (p.y - floor)
                p.vy = -abs(p.vy) * em.bounce
                p.vx *= 0.8
            if bounds is not None and not (min_x < p.x < max_x and min_y < p.y < max_y):
                continue
            append(p)
        if len(alive) > self.max_particles:
            alive = alive[-self.max_particles:]
        self.particles = alive

    def draw(self, canvas: Canvas) -> None:
        put = canvas.put
        for p in self.particles:
            em = p.em
            t = p.age / p.life
            chars = em.chars
            mode = em.char_mode
            if mode == "life":
                ch = chars[int(t * len(chars))]
            elif mode == "random":
                ch = chars[int(p.k * len(chars))]
            else:
                ch = dir_char(p.vx, p.vy)
            if ch == " ":
                continue
            ramp = p.ramp or em.colors
            if em.color_mode == "life":
                col = ramp[int(t * len(ramp))]
            else:
                col = ramp[int(p.k * len(ramp))]
            put(p.x, p.y, ch, col if col is not None else DEFAULT, em.bg)

    def __len__(self) -> int:
        return len(self.particles)
