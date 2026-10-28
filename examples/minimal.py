"""The smallest useful ASCIIparticle game: a sprite in windy grass.

Run from the repository root:  python3 examples/minimal.py
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from asciiparticle import (Emitter, Engine, Frame, GrassField, Noise,  # noqa: E402
                           ParticleSystem, Scene, Sprite, WindField)

CAT = Frame.from_art(r"""
 /\_/\
( o.o )
 > ^ <
""", colors="""
 yyyyy
yyggyyy
 yyyyy
""", palette={"y": 215, "g": 46}, solid=True)


class Garden(Scene):
    name = "garden"
    title = "Garden"
    help_lines = ("Left/Right  move the cat", "Space       sparkles")

    def setup(self):
        self.wind = WindField(Noise(1), base=5.0, gust=8.0)
        self.grass = GrassField(self.rng, self.width, self.height - 2)
        self.fx = ParticleSystem(self.rng, wind=self.wind)
        self.leaves = self.fx.add(Emitter(
            x=self.width / 2, y=0, rate=6, shape="line", width=self.width,
            life=(4, 7), speed=0, chars="',.", colors=[148, 112, 70], wind=1.5, gravity=1.0))
        self.sparkles = self.fx.attach(Emitter(
            life=(0.4, 1.0), speed=(5, 14), chars="*+.", colors=[231, 229, 220, 214], gravity=10))
        self.cat = Sprite(CAT)
        self.x = self.width / 2

    def resize(self, width, height):
        self.grass.regenerate(width, height - 2)

    def update(self, dt):
        if self.input.held("left"):
            self.x -= 15 * dt
        if self.input.held("right"):
            self.x += 15 * dt
        if self.input.pressed("space"):
            self.sparkles.emit(40, self.x, self.height - 4)
        self.grass.disturb(self.x, 3, 0.4)
        self.wind.update(dt, self.width)
        self.grass.update(dt, self.wind)
        self.fx.update(dt)

    def draw(self, canvas):
        self.grass.draw(canvas)
        self.cat.draw(canvas, self.x, self.height - 2)
        self.fx.draw(canvas)


if __name__ == "__main__":
    Engine([Garden]).run()
