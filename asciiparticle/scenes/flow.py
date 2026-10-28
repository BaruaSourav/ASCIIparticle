"""Ink Flow: dense neon particles poured into curl-noise currents and a vortex."""
from __future__ import annotations

import math

from .. import color as C
from ..engine import Scene
from ..forces import FlowField, Vortex
from ..noise import Noise
from ..particles import Emitter, ParticleSystem

PALETTES = [
    ("neon", [
        [201, 200, 199, 163, 126, 89, 53],
        [46, 40, 34, 28, 22],
        [51, 45, 39, 31, 25, 24, 17],
        [231, 255, 252, 248, 244, 240],
    ]),
    ("ember", [
        C.gradient(["#ffffaf", "#ffaf00", "#d75f00", "#5f0000"], 7),
        C.gradient(["#ff5f5f", "#af0000", "#5f0000", "#262626"], 6),
        C.gradient(["#ffd787", "#d78700", "#875f00", "#3a3a3a"], 6),
    ]),
    ("ocean", [
        C.gradient(["#d7ffff", "#5fd7ff", "#0087d7", "#00005f"], 7),
        C.gradient(["#afffd7", "#00d787", "#005f5f", "#000000"], 6),
        C.gradient(["#ffffff", "#87afd7", "#5f5f87", "#262626"], 6),
    ]),
]
GLYPHS = [
    ("dense", "@#%&$*+=-:.", "life"),
    ("crawl", "CRAWL", "random"),
    ("binary", "01", "random"),
    ("brackets", "{}[]()<>/\\", "random"),
    ("dots", "Oo*+:..", "life"),
]


class FlowScene(Scene):
    name = "flow"
    title = "Ink Flow - curl-noise currents around a vortex"
    help_lines = (
        "Space        reverse the swirl",
        "C            cycle colour palette",
        "G            cycle glyph set",
        "Left/Right   weaker / stronger swirl",
        "D            toggle ink drips",
    )

    def setup(self) -> None:
        rng = self.rng
        self.noise = Noise(rng.randrange(1 << 30))
        self.fx = ParticleSystem(rng, max_particles=3200)
        self.flow = FlowField(self.noise, strength=7.0, scale=0.04, cell=4, follow=1.2)
        self.vortex = Vortex(0, 0, strength=26.0, pull=1.2, radius=18.0)
        self.fx.forces += [self.flow, self.vortex]
        self.palette = 0
        self.glyphs = 0
        self.drips_on = True
        self.sources = []
        for i in range(3):
            self.sources.append(self.fx.add(Emitter(
                rate=210, shape="circle", width=3.0, life=(4.0, 7.0), speed=(0.5, 2.0), drag=0.5, tag=i,
                on_spawn=self._tint)))
        self.drips = self.fx.attach(Emitter(
            life=(1.5, 3.0), speed=0, chars="|:'.", gravity=7.0, drag=1.2, forces=False))
        self._apply_glyphs()
        self.resize(self.width, self.height)

    def resize(self, width: int, height: int) -> None:
        self.fx.bounds = (width, height)
        self.vortex.radius = max(10.0, width * 0.22)

    def _apply_glyphs(self) -> None:
        _, chars, mode = GLYPHS[self.glyphs]
        for e in self.sources:
            e.chars, e.char_mode = chars, mode

    def _tint(self, p) -> None:
        bands = PALETTES[self.palette][1]
        p.ramp = bands[(int(self.time * 0.8) + p.em.tag) % len(bands)]

    def update(self, dt: float) -> None:
        inp = self.input
        if inp.pressed("space"):
            self.vortex.strength = -self.vortex.strength
        if inp.pressed("c"):
            self.palette = (self.palette + 1) % len(PALETTES)
        if inp.pressed("g"):
            self.glyphs = (self.glyphs + 1) % len(GLYPHS)
            self._apply_glyphs()
        if inp.pressed("d"):
            self.drips_on = not self.drips_on
        if inp.pressed("left"):
            self.vortex.strength *= 0.75
        if inp.pressed("right"):
            self.vortex.strength *= 1.3
        w, h = self.width, self.height
        cx, cy = w * 0.5, h * 0.45
        self.vortex.x, self.vortex.y = cx, cy
        t = self.time
        for i, e in enumerate(self.sources):
            a = t * 0.22 + i * math.tau / 3
            e.x = cx + math.cos(a) * w * 0.26
            e.y = cy + math.sin(a * 1.3) * h * 0.28
        self.flow.update(dt, w, h)
        parts = self.fx.particles
        if self.drips_on and parts and self.rng.random() < dt * 20.0:
            p = self.rng.choice(parts)
            if p.em is not self.drips and p.age < p.life * 0.5:
                d = self.drips.emit(1, p.x, p.y + 1.0)[0]
                d.ramp = p.ramp
        self.fx.update(dt)

    def draw(self, c) -> None:
        self.fx.draw(c)

    def hud(self) -> str:
        return "palette %s  glyphs %s  particles %d" % (
            PALETTES[self.palette][0], GLYPHS[self.glyphs][0], len(self.fx))
