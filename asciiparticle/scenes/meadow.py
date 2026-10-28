"""Meadow: a small platformer in wind-blown grass. Catch the fireflies!"""
from __future__ import annotations

import math
from typing import List

from .. import art
from .. import color as C
from ..engine import Entity, Scene
from ..forces import WindField
from ..grass import GrassField
from ..noise import Noise
from ..particles import Emitter, ParticleSystem

GOLD = C.gradient(["#ffffd7", "#ffd700", "#ff8700", "#875f00"], 6)
GLOW = [230, 228, 226, 190, 148, 106, 64, 22]
LEAF = [148, 112, 106, 70, 64, 58]
PETAL = [225, 219, 213, 175, 132]
STREAK = [236, 238, 240, 242, 240, 238]
SCARF = [220, 214, 178, 136]
HILL_FAR = 234
HILL_NEAR = 235


class Player(Entity):
    SPEED = 16.0
    JUMP = 24.0
    GRAVITY = 64.0

    def __init__(self, x: float, y: float) -> None:
        super().__init__(x, y, art.hero(), w=3, h=3)
        self.on_ground = True
        self.facing = 1
        self.cast_time = 0.0

    def control(self, move: int, jump: bool, dt: float) -> None:
        target = move * self.SPEED
        self.vx += (target - self.vx) * min(1.0, 14.0 * dt)
        if move:
            self.facing = move
        if jump and self.on_ground:
            self.vy = -self.JUMP
            self.on_ground = False

    def physics(self, dt: float, ground_y: float, width: int) -> float:
        """Integrate; returns the impact speed when landing, else 0."""
        self.vy += self.GRAVITY * dt
        self.x += self.vx * dt
        self.y += self.vy * dt
        self.x = min(max(self.x, 1.5), width - 2.5)
        if self.y >= ground_y:
            impact = self.vy if not self.on_ground else 0.0
            self.y = ground_y
            self.vy = 0.0
            self.on_ground = True
            return impact
        self.on_ground = False
        return 0.0

    def update(self, dt: float) -> None:
        self.cast_time = max(0.0, self.cast_time - dt)
        self.flip = self.facing < 0
        s = self.sprite
        if self.cast_time > 0:
            s.play("cast")
        elif not self.on_ground:
            s.play("jump" if self.vy < 0 else "fall")
        elif abs(self.vx) > 1.5:
            s.play("walk")
        else:
            s.play("idle")
        s.speed = max(0.6, abs(self.vx) / self.SPEED * 1.4) if s.current == "walk" else 1.0
        super().update(dt)


class Firefly:
    __slots__ = ("x", "y", "vx", "vy", "seed", "t")

    def __init__(self, x: float, y: float, seed: float) -> None:
        self.x, self.y = x, y
        self.vx = self.vy = 0.0
        self.seed = seed
        self.t = 0.0


class MeadowScene(Scene):
    name = "meadow"
    title = "Meadow - catch the fireflies before time runs out"
    help_lines = (
        "Left/Right or A/D   walk",
        "Up / W / Space      jump",
        "E                   wind spell (bends grass, shoos fireflies)",
        "G                   call a big gust of wind",
        "R                   restart the round",
    )
    ROUND = 60.0
    FIREFLIES = 6

    autopilot = False

    def setup(self) -> None:
        rng = self.rng
        self.noise = Noise(rng.randrange(1 << 30))
        self.wind = WindField(self.noise, base=4.0, gust=9.0)
        self.fx = ParticleSystem(rng, wind=self.wind, max_particles=2500)
        self.leaves = self.fx.attach(Emitter(
            life=(3.0, 6.0), speed=(1.0, 3.0), angle=(60, 120), chars="',`.", char_mode="random",
            colors=LEAF, gravity=1.2, wind=1.6, collide="die"))
        self.petals = self.fx.attach(Emitter(
            life=(3.0, 6.0), speed=(1.0, 3.0), angle=(60, 120), chars="*'.", char_mode="random",
            colors=PETAL, gravity=1.0, wind=1.8, collide="die"))
        self.streaks = self.fx.attach(Emitter(
            life=(1.2, 2.5), speed=0, chars=".-~~-.", colors=STREAK, wind=3.0))
        self.trail = self.fx.attach(Emitter(
            life=(0.4, 0.9), speed=(0.0, 1.0), chars="+.'", colors=GLOW[2:], wind=0.4))
        self.scarf = self.fx.attach(Emitter(
            life=(0.3, 0.6), speed=(0.0, 1.0), chars="~-", colors=SCARF, wind=2.0))
        self.sparks = self.fx.attach(Emitter(
            life=(0.5, 1.1), speed=(6.0, 16.0), angle=(20, 160), chars="*+'.", colors=GOLD,
            gravity=14.0, drag=1.5, wind=0.3))
        self.dust = self.fx.attach(Emitter(
            life=(0.3, 0.6), speed=(3.0, 7.0), angle=(0, 180), chars=".:'", colors=[180, 137, 95, 239],
            gravity=6.0, drag=2.0))
        self.gusts = self.fx.attach(Emitter(
            life=(0.4, 0.8), speed=(18.0, 30.0), chars="~-.", colors=[159, 123, 87, 66, 60]))
        self.best = 0
        self.popups: List[list] = []
        self.idle = 0.0
        self.attract = False
        self._layout()
        self.restart()

    def _layout(self) -> None:
        w, h = self.width, self.height
        self.ground_y = max(4, h - 4)
        self.fx.floor = self.ground_y + 0.5
        self.fx.bounds = (w, h)
        if hasattr(self, "grass"):
            self.grass.regenerate(w, self.ground_y)
        else:
            self.grass = GrassField(self.rng, w, self.ground_y)
        n1 = self.noise.fbm1
        self.far = [int(self.ground_y - 3 - (n1(x * 0.025) + 1.0) * h * 0.14) for x in range(w)]
        self.near = [int(self.ground_y - 1 - (n1(x * 0.05 + 40.0) + 1.0) * h * 0.07) for x in range(w)]
        rng = self.rng
        self.stars = [(rng.randrange(w), rng.randrange(max(1, self.ground_y - 6)),
                       rng.uniform(0, math.tau), rng.choice(".'*+")) for _ in range(w * h // 45)]
        self.moon_x = int(w * 0.82)

    def resize(self, width: int, height: int) -> None:
        self._layout()
        self.player.x = min(self.player.x, width - 3)
        self.player.y = self.ground_y
        for f in self.fireflies:
            f.x = min(f.x, width - 2.0)
            f.y = min(f.y, self.ground_y - 1.0)

    def restart(self) -> None:
        self.player = Player(self.width * 0.25, self.ground_y)
        self.score = 0
        self.time_left = self.ROUND
        self.state = "play"
        self.fireflies = [self._new_firefly() for _ in range(self.FIREFLIES)]

    def _new_firefly(self) -> Firefly:
        rng = self.rng
        return Firefly(rng.uniform(3, self.width - 4),
                       rng.uniform(self.ground_y - 8, self.ground_y - 2), rng.uniform(0, 200))

    # ---------------------------------------------------------------- update
    def _controls(self):
        inp = self.input
        if inp.events:
            self.idle = 0.0
            self.attract = False
        if self.autopilot or self.attract:
            return self._autopilot()
        if inp.pressed("left", "a"):
            inp.release("right", "d")
        if inp.pressed("right", "d"):
            inp.release("left", "a")
        move = (1 if inp.held("right", "d") else 0) - (1 if inp.held("left", "a") else 0)
        jump = inp.pressed("up", "w", "space")
        return move, jump, inp.pressed("e")

    def _autopilot(self):
        p = self.player
        if not self.fireflies:
            return 0, False, False
        target = min(self.fireflies, key=lambda f: abs(f.x - p.x) + abs(f.y - p.y) * 0.5)
        dx = target.x - p.x
        move = 0 if abs(dx) < 0.8 else (1 if dx > 0 else -1)
        jump = abs(dx) < 5 and target.y < p.y - 2.5
        cast = self.rng.random() < 0.006
        return move, jump, cast

    def update(self, dt: float) -> None:
        inp = self.input
        self.idle += dt
        if self.idle > 25.0 and not self.autopilot:
            self.attract = True
        move, jump, cast = self._controls()
        if inp.pressed("r") or (self.state == "over" and inp.pressed("enter", "space")):
            self.restart()
        if inp.pressed("g") or (self.attract and self.rng.random() < dt / 8.0):
            self.wind.boost(16.0)

        p = self.player
        p.control(move, jump, dt)
        impact = p.physics(dt, self.ground_y, self.width)
        if impact > 8.0:
            self.dust.emit(int(impact / 2), p.x, self.ground_y)
            self.grass.disturb(p.x, 4.0, impact * 0.12)
        if abs(p.vx) > 1.0 and p.on_ground:
            self.grass.disturb(p.x, 2.5, abs(p.vx) * 0.04)
        if abs(p.vx) > 4.0 and self.rng.random() < 0.6:
            self.scarf.emit(1, p.x - p.facing, p.y - 1.5)
        if cast:
            self._cast()
        p.update(dt)

        self.wind.update(dt, self.width)
        self.grass.update(dt, self.wind)
        self._update_fireflies(dt)
        self._ambient(dt)
        self.fx.update(dt)

        for pop in self.popups:
            pop[1] -= 3.0 * dt
            pop[3] += dt
        self.popups = [pop for pop in self.popups if pop[3] < 0.9]

        if self.state == "play":
            self.time_left -= dt
            if self.time_left <= 0.0:
                self.time_left = 0.0
                self.state = "over"
                self.best = max(self.best, self.score)
                if self.autopilot or self.attract:
                    self.after(3.0, self.restart)

    def _cast(self) -> None:
        p = self.player
        d = p.facing
        p.cast_time = 0.35
        self.grass.disturb(p.x + d * 7, 12.0, 6.0, direction=d)
        g = self.gusts
        g.angle = (-15, 15) if d > 0 else (165, 195)
        g.emit(25, p.x + d * 2, p.y - 1.5)
        for f in self.fireflies:
            dx = f.x - p.x
            if 0 < dx * d < 16 and abs(f.y - p.y) < 6:
                f.vx += d * 30.0

    def _update_fireflies(self, dt: float) -> None:
        n1 = self.noise.noise1
        p = self.player
        top = max(1.0, self.ground_y - 9.0)
        bottom = self.ground_y - 1.0
        caught = []
        for f in self.fireflies:
            f.t += dt
            tx = n1(f.seed + f.t * 0.45) * 11.0 + self.wind.strength_at(f.x) * 0.15
            ty = n1(f.seed + 77.0 + f.t * 0.55) * 4.0
            f.vx += (tx - f.vx) * min(1.0, 2.0 * dt)
            f.vy += (ty - f.vy) * min(1.0, 2.0 * dt)
            if f.y < top:
                f.vy += 10.0 * dt
            if f.y > bottom:
                f.vy -= 10.0 * dt
            f.x += f.vx * dt
            f.y += f.vy * dt
            if f.x < 1:
                f.x, f.vx = 1.0, abs(f.vx)
            elif f.x > self.width - 2:
                f.x, f.vx = self.width - 2.0, -abs(f.vx)
            f.y = min(max(f.y, 0.0), bottom + 0.5)
            if self.rng.random() < 0.25:
                self.trail.emit(1, f.x, f.y)
            if self.state == "play" and abs(f.x - p.x) < 1.8 and p.y - 3.0 <= f.y <= p.y + 0.5:
                caught.append(f)
        for f in caught:
            self.fireflies.remove(f)
            self.score += 1
            self.sparks.emit(30, f.x, f.y)
            self.popups.append([f.x, f.y - 1.0, "+1", 0.0])
            self.after(0.8, self._respawn)

    def _respawn(self) -> None:
        if len(self.fireflies) < self.FIREFLIES:
            self.fireflies.append(self._new_firefly())

    def _ambient(self, dt: float) -> None:
        rng = self.rng
        strength = abs(self.wind.mean())
        blades = self.grass.blades
        if blades:
            n = (2.0 + max(0.0, strength - 5.0) * 2.5) * dt
            while n > 0:
                if rng.random() < n:
                    b = rng.choice(blades)
                    x, y = self.grass.tip(b)
                    (self.petals if b.tip else self.leaves).emit(1, x, y - 0.5)
                n -= 1.0
        n = (1.0 + strength * 0.6) * dt * self.width / 40.0
        while n > 0:
            if rng.random() < n:
                self.streaks.emit(1, rng.uniform(0, self.width), rng.uniform(1, self.ground_y - 2))
            n -= 1.0

    # ------------------------------------------------------------------ draw
    def draw(self, c) -> None:
        t = self.time
        for x, y, phase, ch in self.stars:
            tw = math.sin(t * 2.0 + phase)
            if tw > -0.6:
                c.put(x, y, ch if tw > 0.2 else ".", 255 if tw > 0.6 else 245)
        art.MOON.draw(c, self.moon_x, 6)
        gy = self.ground_y
        far, near = self.far, self.near
        last = self.width - 1
        for x in range(self.width):
            for y in range(max(0, far[x]), gy + 1):
                c.set_bg(x, y, HILL_FAR)
            for y in range(max(0, near[x]), gy + 1):
                c.set_bg(x, y, HILL_NEAR)
            for ridge, col in ((far, 238), (near, 22)):
                y = ridge[x]
                left, right = ridge[max(0, x - 1)], ridge[min(last, x + 1)]
                ch = "/" if right < y or left > y else ("\\" if left < y or right > y else "_")
                c.put(x, y - (1 if ch == "_" else 0), ch, col)
        self.grass.draw_ground(c, self.height)
        self.grass.draw(c)
        self.fx.draw(c)
        for f in self.fireflies:
            glow = 0.5 + 0.5 * math.sin(t * 7.0 + f.seed)
            ch = "*" if glow > 0.6 else ("+" if glow > 0.25 else ".")
            c.put(f.x, f.y, ch, GLOW[int((1.0 - glow) * 4)])
        self.player.draw(c)
        for x, y, text, age in self.popups:
            c.text(x, y, text, 229 if age < 0.5 else 136)
        if self.state == "over":
            msg = ["TIME!", "", "You caught %d fireflies" % self.score, "best: %d" % self.best,
                   "", "press R or Space to play again"]
            top = max(0, self.height // 2 - 6)
            for i, line in enumerate(msg):
                c.text((self.width - len(line)) // 2, top + i, line, 229 if i == 0 else 252)
        if self.attract and not self.autopilot:
            c.text(2, 0, "DEMO - press any key to play", 244)

    def hud(self) -> str:
        w = self.wind.mean()
        arrows = (">" if w >= 0 else "<") * max(1, min(5, int(abs(w) / 4) + 1))
        return "fireflies %d  best %d  time %2d  wind %s" % (
            self.score, max(self.best, self.score), math.ceil(self.time_left), arrows)
