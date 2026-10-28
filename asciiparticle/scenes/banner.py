"""Banner: words built from spring-loaded particles that you can blow apart."""
from __future__ import annotations

from .. import color as C
from ..engine import Scene
from ..font import block_points
from ..forces import HomeSpring, Vortex, WindField
from ..noise import Noise
from ..particles import Emitter, ParticleSystem

PHRASES = [("ASCII", "PARTICLE"), ("WIND", "& GRASS"), ("MADE OF", "DOTS"), ("HELLO", "MAC")]
SPECTRUM = C.gradient(["#ff00ff", "#af00ff", "#00afff", "#00ffaf", "#87ff00"], 24)
DUST = [236, 238, 240, 242, 240, 238]


class BannerScene(Scene):
    name = "banner"
    title = "Banner - text made of particles"
    help_lines = (
        "Space        blow the letters apart",
        "Enter        next phrase",
        "V            toggle the vortex",
        "Left/Right   change the wind",
    )

    def setup(self) -> None:
        rng = self.rng
        self.noise = Noise(rng.randrange(1 << 30))
        self.wind = WindField(self.noise, base=0.0, gust=6.0, turbulence=0.8)
        self.fx = ParticleSystem(rng, wind=self.wind, max_particles=6000)
        self.spring = HomeSpring(strength=22.0, damping=5.0)
        self.vortex = Vortex(0, 0, strength=40.0, pull=0.6, radius=20.0, enabled=False)
        self.fx.forces += [self.spring, self.vortex]
        self.letters = self.fx.attach(Emitter(chars="#@%&", char_mode="random", wind=0.25))
        self.dust = self.fx.add(Emitter(
            rate=10, shape="rect", life=(3.0, 6.0), speed=(0.0, 1.0), chars=".-~-.",
            colors=DUST, wind=1.5, forces=False))
        self.phrase = 0
        self.idle = 0.0
        self.resize(self.width, self.height)

    def resize(self, width: int, height: int) -> None:
        self.dust.x, self.dust.y = width / 2, height / 2
        self.dust.width, self.dust.height = width, height
        self.vortex.x, self.vortex.y = width / 2, height / 2
        self.build()

    def build(self) -> None:
        """Assign home points for the current phrase, reusing existing particles."""
        rng = self.rng
        w, h = self.width, self.height
        homes = block_points(PHRASES[self.phrase], w, h)
        rng.shuffle(homes)
        mine = [p for p in self.fx.particles if p.em is self.letters and p.data is not None]
        rng.shuffle(mine)
        for p, home in zip(mine, homes):
            p.data = home
            p.ramp = [self._hue(home[0])]
        for p in mine[len(homes):]:
            p.data = None
            p.life = p.age + rng.uniform(0.3, 1.2)
        for home in homes[len(mine):]:
            x = rng.choice((rng.uniform(-10, 0), rng.uniform(w, w + 10), rng.uniform(0, w)))
            y = rng.uniform(-6, h + 6) if x < 0 or x > w else rng.choice((-3.0, h + 3.0))
            self.fx.spawn(self.letters, x, y, 0.0, 0.0, 1e9,
                          [self._hue(home[0])], home)

    def _hue(self, x: float) -> int:
        t = min(1.0, max(0.0, x / max(1, self.width)))
        return SPECTRUM[int(t * (len(SPECTRUM) - 1))]

    def explode(self) -> None:
        rng = self.rng
        cx, cy = self.width / 2, self.height / 2
        for p in self.fx.particles:
            if p.em is self.letters:
                dx, dy = p.x - cx, (p.y - cy) * 2.0
                r = max(1.0, (dx * dx + dy * dy) ** 0.5)
                v = rng.uniform(25.0, 55.0)
                p.vx += dx / r * v
                p.vy += dy / r * v * 0.5
        self.spring.scale = 0.0

    def update(self, dt: float) -> None:
        inp = self.input
        self.idle += dt
        if inp.events:
            self.idle = 0.0
        if inp.pressed("space"):
            self.explode()
        if inp.pressed("enter") or self.idle > 9.0:
            if self.idle > 9.0:
                self.explode()
                self.idle = 0.0
            self.phrase = (self.phrase + 1) % len(PHRASES)
            self.build()
        if inp.pressed("v"):
            self.vortex.enabled = not self.vortex.enabled
        if inp.pressed("left"):
            self.wind.base -= 4.0
        if inp.pressed("right"):
            self.wind.base += 4.0
        target = 0.25 if self.vortex.enabled else 1.0
        self.spring.scale = min(target, self.spring.scale + dt * 0.7)
        rng = self.rng
        for p in self.fx.particles:
            if p.em is self.letters and rng.random() < 0.03:
                p.k = rng.random()
        self.wind.update(dt, self.width)
        self.fx.update(dt)

    def draw(self, c) -> None:
        self.fx.draw(c)

    def hud(self) -> str:
        return "Space explode  Enter next  V vortex"
