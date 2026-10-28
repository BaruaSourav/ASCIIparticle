"""Fireworks over a city skyline."""
from __future__ import annotations

import math

from .. import color as C
from ..engine import Scene
from ..forces import WindField
from ..noise import Noise
from ..particles import Emitter, ParticleSystem

RAMPS = [
    [231, 224, 217, 210, 203, 196, 160, 124, 88, 52],
    [231, 230, 229, 228, 220, 214, 208, 172, 130, 94],
    [231, 194, 157, 120, 83, 46, 40, 34, 28, 22],
    [231, 195, 159, 117, 75, 33, 27, 26, 19, 17],
    [231, 225, 219, 213, 207, 201, 165, 129, 91, 54],
    [231, 195, 159, 123, 87, 51, 44, 37, 30, 23],
]
GOLD = C.gradient(["#ffffff", "#ffd75f", "#d78700", "#5f3700"], 8)
SMOKE = [240, 239, 238, 237, 236, 235]


class FireworksScene(Scene):
    name = "fireworks"
    title = "Fireworks - peonies, rings, willows and palms"
    help_lines = (
        "Space        launch a rocket",
        "A            toggle automatic launches",
        "Left/Right   change the wind",
    )

    def setup(self) -> None:
        rng = self.rng
        self.noise = Noise(rng.randrange(1 << 30))
        self.wind = WindField(self.noise, base=1.5, gust=2.5, turbulence=0.5)
        self.fx = ParticleSystem(rng, wind=self.wind, max_particles=3500)
        self.rocket = self.fx.attach(Emitter(chars="|", colors=[230], on_death=self._explode, wind=0.05))
        self.trail = self.fx.attach(Emitter(
            life=(0.3, 0.7), speed=(0.0, 2.0), angle=(240, 300), chars="'.", colors=GOLD[2:],
            gravity=4.0, drag=2.0, wind=0.3))
        self.star = self.fx.attach(Emitter(chars="@@**++:'.", gravity=7.0, drag=1.1, wind=0.25))
        self.willow = self.fx.attach(Emitter(chars="*:'.,.", gravity=4.0, drag=2.2, wind=0.4))
        self.crackle = self.fx.attach(Emitter(chars="*+.", gravity=7.0, drag=1.3, wind=0.25,
                                              on_death=self._crackle))
        self.sparkle = self.fx.attach(Emitter(life=(0.1, 0.3), speed=(1.0, 4.0), chars="+.",
                                              colors=[231, 255, 229]))
        self.smoke = self.fx.attach(Emitter(life=(2.5, 4.0), speed=(0.5, 2.0), chars="o:..",
                                            colors=SMOKE[2:], wind=1.2, drag=0.6, gravity=-0.6))
        self.flash = self.fx.attach(Emitter(chars="@", colors=[231]))
        self.auto = True
        self.rockets = []
        self.next_launch = 0.3
        self.resize(self.width, self.height)

    def resize(self, width: int, height: int) -> None:
        rng = self.rng
        self.fx.bounds = (width, height)
        self.buildings = []
        x = 0
        while x < width:
            bw = rng.randint(4, 10)
            bh = rng.randint(2, max(3, height // 4))
            lit = [[rng.random() < 0.35 for _ in range(bw)] for _ in range(bh)]
            self.buildings.append((x, bw, bh, lit))
            x += bw + rng.randint(0, 2)

    def launch(self, x=None) -> None:
        rng = self.rng
        h = self.height
        x = rng.uniform(self.width * 0.15, self.width * 0.85) if x is None else x
        g = 22.0
        apex = rng.uniform(h * 0.5, h * 0.8)
        v = math.sqrt(2.0 * g * apex)
        self.rocket.gravity = g
        p = self.fx.spawn(self.rocket, x, h - 1.0, rng.uniform(-2.0, 2.0), -v, v / g)
        self.rockets.append(p)

    def _explode(self, p) -> None:
        rng = self.rng
        fx = self.fx
        x, y = p.x, p.y
        kind = rng.choice(("peony", "peony", "ring", "willow", "palm", "crackle"))
        ramp = rng.choice(RAMPS)
        if kind == "ring":
            n = 56
            base = rng.uniform(20.0, 26.0)
            tilt = rng.uniform(0.6, 1.0)
            for i in range(n):
                a = math.tau * i / n
                s = base * rng.uniform(0.96, 1.04)
                fx.spawn(self.star, x, y, math.cos(a) * s, -math.sin(a) * s * 0.5 * tilt,
                         rng.uniform(1.2, 1.7), ramp)
        elif kind == "willow":
            for _ in range(90):
                a = rng.uniform(0, math.tau)
                s = rng.uniform(4.0, 20.0)
                fx.spawn(self.willow, x, y, math.cos(a) * s, -math.sin(a) * s * 0.5,
                         rng.uniform(2.4, 3.6), GOLD)
        elif kind == "palm":
            arms = rng.randint(6, 9)
            for i in range(arms):
                a = math.tau * i / arms + rng.uniform(-0.1, 0.1)
                for j in range(10):
                    s = 8.0 + j * 2.0
                    fx.spawn(self.star, x, y, math.cos(a) * s, -math.sin(a) * s * 0.5,
                             rng.uniform(1.3, 2.0), ramp)
        else:
            em = self.crackle if kind == "crackle" else self.star
            for _ in range(140):
                a = rng.uniform(0, math.tau)
                s = rng.uniform(4.0, 27.0) * (0.75 + 0.25 * rng.random())
                fx.spawn(em, x, y, math.cos(a) * s, -math.sin(a) * s * 0.5,
                         rng.uniform(1.1, 2.0), ramp)
        fx.spawn(self.flash, x, y, 0.0, 0.0, 0.12)
        self.smoke.emit(6, x, y)

    def _crackle(self, p) -> None:
        if self.rng.random() < 0.5:
            self.sparkle.emit(2, p.x, p.y)

    def update(self, dt: float) -> None:
        inp = self.input
        if inp.pressed("space"):
            self.launch()
        if inp.pressed("a"):
            self.auto = not self.auto
        if inp.pressed("left"):
            self.wind.base -= 3.0
        if inp.pressed("right"):
            self.wind.base += 3.0
        if self.auto:
            self.next_launch -= dt
            if self.next_launch <= 0:
                self.launch()
                self.next_launch = self.rng.uniform(0.5, 1.4)
        self.rockets = [p for p in self.rockets if p.age < p.life]
        for p in self.rockets:
            self.trail.emit(1, p.x, p.y + 0.5)
        self.wind.update(dt, self.width)
        self.fx.update(dt)

    def draw(self, c) -> None:
        h = self.height
        t = self.time
        for x0, bw, bh, lit in self.buildings:
            for row in range(bh):
                y = h - 1 - row
                for dx in range(bw):
                    x = x0 + dx
                    on = lit[row][dx] and dx % 2 == 1 and row % 2 == 1
                    if on and math.sin(t * 0.3 + x * 7.1 + y * 3.3) < -0.97:
                        on = False
                    c.put(x, y, " ", -1, 178 if on else 234)
        self.fx.draw(c)

    def hud(self) -> str:
        return "auto %s  wind %+.0f  sparks %d" % ("on" if self.auto else "off", self.wind.base, len(self.fx))
