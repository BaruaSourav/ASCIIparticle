"""Campfire: fire, smoke and embers in the wind, with rain, snow and lightning."""
from __future__ import annotations

import math

from .. import art
from .. import color as C
from ..engine import Scene
from ..forces import WindField
from ..grass import GrassField
from ..noise import Noise
from ..particles import Emitter, ParticleSystem

FIRE = [231, 230, 229, 227, 221, 214, 208, 202, 196, 160, 124, 88]
EMBER = [230, 228, 214, 208, 202, 166, 130]
SMOKE = [247, 246, 245, 244, 243, 242, 241, 240, 239, 238, 237, 236]
RAIN = [39, 33, 32, 31, 25]
SNOW = [255, 254, 231, 252, 250]
BOLT = [231, 195, 189]


class CampfireScene(Scene):
    name = "campfire"
    title = "Campfire - fire, smoke and weather"
    help_lines = (
        "Space        stoke the fire",
        "R            toggle rain",
        "S            toggle snow",
        "L            lightning",
        "Left/Right   change the wind",
    )

    def setup(self) -> None:
        rng = self.rng
        self.noise = Noise(rng.randrange(1 << 30))
        self.wind = WindField(self.noise, base=2.5, gust=5.0, travel=10.0)
        self.fx = ParticleSystem(rng, wind=self.wind, max_particles=3500)
        self.fire = self.fx.add(Emitter(
            rate=150, shape="line", width=7.0, life=(0.6, 1.5), speed=(6.0, 13.0), angle=(75, 105),
            chars="$&%*^'.", colors=FIRE, gravity=-10.0, drag=1.0, wind=0.5))
        self.embers = self.fx.add(Emitter(
            rate=8, shape="line", width=4.0, life=(1.5, 3.0), speed=(6.0, 14.0), angle=(60, 120),
            chars="*.'", char_mode="random", colors=EMBER, gravity=-2.0, drag=0.5, wind=1.2))
        self.smoke = self.fx.add(Emitter(
            rate=14, shape="line", width=3.0, life=(3.0, 5.5), speed=(1.0, 3.0), angle=(80, 100),
            chars="@Oo*:.", colors=SMOKE, gravity=-2.5, drag=0.5, wind=1.8))
        self.rain = self.fx.add(Emitter(
            rate=0, shape="line", life=3.0, speed=0, velocity=(0.0, 30.0), chars="|", char_mode="dir",
            colors=RAIN, color_mode="random", gravity=25.0, wind=0.8, collide="die",
            on_death=self._splash, active=False))
        self.splash = self.fx.attach(Emitter(
            life=(0.15, 0.3), speed=(3.0, 6.0), angle=(30, 150), chars=".,", colors=[75, 68]))
        self.snow = self.fx.add(Emitter(
            rate=0, shape="line", life=20.0, speed=0, velocity=(0.0, 3.0), chars="*.+'",
            char_mode="random", colors=SNOW, color_mode="random", gravity=0.6, drag=0.4, wind=0.9,
            collide="die", on_death=self._land, active=False))
        self.stoke = 0.0
        self.flash = 0.0
        self.bolt = []
        self.bolt_t = 0.0
        self.next_bolt = 8.0
        self.resize(self.width, self.height)

    def resize(self, width: int, height: int) -> None:
        self.ground_y = max(5, height - 3)
        self.fire_x = int(width * 0.42)
        self.tree_x = int(width * 0.8)
        self.fx.floor = self.ground_y + 0.5
        self.fx.bounds = (width, height)
        for e in (self.fire, self.embers):
            e.x, e.y = self.fire_x, self.ground_y - 1.0
        self.smoke.x, self.smoke.y = self.fire_x, self.ground_y - 6.0
        for e in (self.rain, self.snow):
            e.x, e.y, e.width = width / 2, -1.0, width * 1.4
        self.grass = GrassField(self.rng, width, self.ground_y, heights=(1, 3))
        self.grass.clear_range(self.fire_x - 4, self.fire_x + 4)
        self.snow_depth = [0.0] * width
        rng = self.rng
        self.stars = [(rng.randrange(width), rng.randrange(max(1, self.ground_y - 4)),
                       rng.uniform(0, math.tau)) for _ in range(width * height // 60)]

    def _splash(self, p) -> None:
        if self.rng.random() < 0.3:
            self.splash.emit(2, p.x, p.y - 0.5)

    def _land(self, p) -> None:
        i = int(p.x)
        if 0 <= i < len(self.snow_depth) and abs(i - self.fire_x) > 5:
            self.snow_depth[i] = min(1.0, self.snow_depth[i] + 0.12)

    def lightning(self) -> None:
        rng = self.rng
        x = rng.uniform(self.width * 0.1, self.width * 0.9)
        self.bolt = []
        for y in range(self.ground_y + 1):
            step = rng.choice((-1, 0, 0, 1))
            ch = "/" if step < 0 else ("\\" if step > 0 else "|")
            self.bolt.append((x, y, ch))
            x += step
        self.flash = 0.15
        self.bolt_t = 0.35
        self.wind.boost(10.0)

    def update(self, dt: float) -> None:
        inp = self.input
        if inp.pressed("space"):
            self.stoke = 1.5
            self.embers.emit(25)
        if inp.pressed("r"):
            self.rain.active = not self.rain.active
        if inp.pressed("s"):
            self.snow.active = not self.snow.active
        if inp.pressed("l"):
            self.lightning()
        if inp.pressed("left"):
            self.wind.base -= 3.0
        if inp.pressed("right"):
            self.wind.base += 3.0
        self.wind.base = max(-18.0, min(18.0, self.wind.base))

        raining = self.rain.active
        self.rain.rate = self.width * 2.2 if raining else 0.0
        self.snow.rate = self.width * 0.6 if self.snow.active else 0.0
        self.stoke = max(0.0, self.stoke - dt)
        boost = 1.0 + self.stoke * 1.5
        self.fire.rate = 150.0 * boost * (0.55 if raining else 1.0)
        self.embers.rate = 8.0 * boost
        self.smoke.rate = 14.0 * (1.8 if raining else 1.0)
        if raining:
            self.next_bolt -= dt
            if self.next_bolt <= 0:
                self.lightning()
                self.next_bolt = self.rng.uniform(5.0, 11.0)
        if not self.snow.active:
            self.snow_depth = [max(0.0, d - dt * 0.03) for d in self.snow_depth]
        self.flash = max(0.0, self.flash - dt)
        self.bolt_t = max(0.0, self.bolt_t - dt)
        self.wind.update(dt, self.width)
        self.grass.update(dt, self.wind)
        self.fx.update(dt)

    def draw(self, c) -> None:
        w = self.width
        gy = self.ground_y
        t = self.time
        if self.flash > 0:
            for y in range(gy + 1):
                for x in range(w):
                    c.set_bg(x, y, 250 if self.flash > 0.08 else 240)
        elif not (self.rain.active or self.snow.active):
            for x, y, phase in self.stars:
                if math.sin(t * 1.7 + phase) > -0.3:
                    c.put(x, y, ".", 250)
        flicker = 0.85 + 0.15 * math.sin(t * 13.0) * math.sin(t * 7.3)
        r = 10.0 * flicker
        for dy in range(-1, 3):
            for dx in range(-int(r), int(r) + 1):
                d = (dx / r) ** 2 + (dy / (r * 0.4)) ** 2
                if d < 1.0:
                    c.set_bg(self.fire_x + dx, gy + dy, 52 if d < 0.3 and dy > 0 else 234)
        self.grass.draw_ground(c, self.height)
        for x, depth in enumerate(self.snow_depth):
            if depth > 0.15:
                c.put(x, gy, "." if depth < 0.45 else ("_" if depth < 0.8 else "="), 255)
        art.TREE.draw(c, self.tree_x, gy)
        self.grass.draw(c)
        art.LOGS.draw(c, self.fire_x, gy)
        self.fx.draw(c)
        if self.bolt_t > 0:
            col = BOLT[min(len(BOLT) - 1, int((0.35 - self.bolt_t) * 9))]
            for x, y, ch in self.bolt:
                c.put(x, y, ch, col)

    def hud(self) -> str:
        weather = "rain" if self.rain.active else ("snow" if self.snow.active else "clear")
        return "weather %s  wind %+.0f  particles %d" % (weather, self.wind.base, len(self.fx))
