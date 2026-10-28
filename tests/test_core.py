import io
import random
import unittest

from asciiparticle import color as C
from asciiparticle.canvas import Canvas
from asciiparticle.font import block_points, text_points
from asciiparticle.forces import HomeSpring, WindField
from asciiparticle.grass import GrassField
from asciiparticle.input import Input, parse_keys
from asciiparticle.noise import Noise
from asciiparticle.particles import Emitter, ParticleSystem, dir_char
from asciiparticle.sprite import Frame, Sprite
from asciiparticle.terminal import render_diff


class ColorTest(unittest.TestCase):
    def test_rgb_maps_to_cube_and_grays(self):
        self.assertEqual(C.rgb(255, 0, 0), 196)
        self.assertEqual(C.rgb(0, 0, 0), 16)
        self.assertEqual(C.rgb(128, 128, 128), 244)
        self.assertEqual(C.hex_color("#ffffff"), 231)

    def test_round_trip(self):
        for i in range(16, 256):
            self.assertEqual(C.rgb(*C.to_rgb(i)) in (i, C.rgb(*C.PALETTE[i])), True)

    def test_gradient(self):
        g = C.gradient(["#000000", "#ffffff"], 5)
        self.assertEqual(len(g), 5)
        self.assertEqual(g[0], 16)
        self.assertEqual(g[-1], 231)


class CanvasTest(unittest.TestCase):
    def test_put_clips_and_truncates(self):
        c = Canvas(4, 2)
        c.put(-0.5, 0, "x")
        c.put(4, 0, "x")
        c.put(1.9, 1.2, "a", 9)
        self.assertEqual(c.lines(), ["    ", " a  "])
        self.assertEqual(c.get(1, 1), ("a", 9, C.DEFAULT))

    def test_bg_kept_when_none(self):
        c = Canvas(2, 1)
        c.set_bg(0, 0, 52)
        c.put(0, 0, "#", 15)
        self.assertEqual(c.get(0, 0), ("#", 15, 52))


class TerminalTest(unittest.TestCase):
    def test_diff_writes_only_changes(self):
        c = Canvas(10, 3)
        c.text(0, 0, "hi", 15)
        first, snap = render_diff(c)
        self.assertIn("hi", first)
        c.clear()
        c.text(0, 0, "hi", 15)
        same, snap = render_diff(c, snap)
        self.assertEqual(same, "")
        c.clear()
        c.text(0, 0, "ho", 15)
        changed, _ = render_diff(c, snap)
        self.assertIn("\x1b[1;2H", changed)
        self.assertTrue(changed.endswith("o"))


class InputTest(unittest.TestCase):
    def test_parse(self):
        self.assertEqual(parse_keys("\x1b[Aa \x1b[1;2C\x1bQ\t"),
                         ["up", "a", "space", "right", "esc", "q", "tab"])

    def test_hold_window_and_repeat(self):
        inp = Input()
        inp.feed("left")
        inp.begin_frame(0.0)
        self.assertTrue(inp.pressed("left"))
        inp.begin_frame(0.3)
        self.assertTrue(inp.held("left"))
        self.assertFalse(inp.pressed("left"))
        inp.feed("left")  # key repeat
        inp.begin_frame(0.4)
        inp.begin_frame(0.6)
        self.assertFalse(inp.held("left"))


class ParticleTest(unittest.TestCase):
    def setUp(self):
        self.fx = ParticleSystem(random.Random(1))

    def test_rate_and_life(self):
        deaths = []
        self.fx.add(Emitter(rate=10, life=0.5, on_death=deaths.append))
        for _ in range(30):
            self.fx.update(0.1)
        self.assertGreater(len(deaths), 0)
        self.assertLessEqual(len(self.fx), 6)

    def test_gravity_and_floor(self):
        self.fx.floor = 5.0
        hits = []
        em = self.fx.attach(Emitter(gravity=20.0, collide="die", on_death=hits.append, life=10))
        self.fx.spawn(em, 0, 0, 0, 0, 10)
        for _ in range(30):
            self.fx.update(0.05)
        self.assertEqual(len(hits), 1)
        self.assertEqual(hits[0].y, 5.0)

    def test_draw_uses_ramps(self):
        c = Canvas(5, 5)
        em = self.fx.attach(Emitter(chars="AB", colors=[1, 2]))
        self.fx.spawn(em, 2, 2, 0, 0, 1.0)
        self.fx.draw(c)
        self.assertEqual(c.get(2, 2), ("A", 1, C.DEFAULT))

    def test_dir_char(self):
        self.assertEqual(dir_char(5, 0), "-")
        self.assertEqual(dir_char(0, 5), "|")
        self.assertEqual(dir_char(3, 3), "\\")
        self.assertEqual(dir_char(-3, 3), "/")

    def test_home_spring_converges(self):
        em = self.fx.attach(Emitter())
        self.fx.forces.append(HomeSpring())
        p = self.fx.spawn(em, 0, 0, 0, 0, 100, data=(10.5, 4.5))
        for _ in range(120):
            self.fx.update(1 / 30)
        self.assertAlmostEqual(p.x, 10.5, delta=0.1)
        self.assertAlmostEqual(p.y, 4.5, delta=0.1)


class WindAndGrassTest(unittest.TestCase):
    def test_grass_leans_with_wind(self):
        noise = Noise(3)
        for base, sign in ((10.0, 1), (-10.0, -1)):
            wind = WindField(noise, base=base, gust=0.0)
            grass = GrassField(random.Random(2), 40, 10)
            for _ in range(60):
                wind.update(1 / 30, 40)
                grass.update(1 / 30, wind)
            mean = sum(b.angle for b in grass.blades) / len(grass.blades)
            self.assertGreater(mean * sign, 0.4)

    def test_noise_range(self):
        n = Noise(5)
        vals = [n.noise2(x * 0.37, x * 0.11) for x in range(500)]
        self.assertTrue(all(-1.0 <= v <= 1.0 for v in vals))


class SpriteTest(unittest.TestCase):
    def test_art_colours_and_flip(self):
        f = Frame.from_art(" o \n/|\\", " h \nccc", {"h": 1, "c": 2})
        self.assertEqual((f.width, f.height), (3, 2))
        self.assertIn((1, 0, "o", 1), f.cells)
        self.assertIn((0, 1, "/", 2), f.cells)
        flipped = f.flipped()
        self.assertIn((2, 1, "\\", 2), flipped.cells)
        c = Canvas(5, 5)
        f.draw(c, 2, 4)  # anchor is bottom centre
        self.assertEqual(c.lines()[3:5], ["  o  ", " /|\\ "])

    def test_solid_fills_inner_gaps_only(self):
        f = Frame.from_art("( o )", solid=True)
        c = Canvas(7, 1)
        c.text(0, 0, "#######")
        f.draw(c, 3, 0)
        self.assertEqual(c.lines(), ["#( o )#"])

    def test_animation(self):
        a = Frame.from_art("a")
        b = Frame.from_art("b")
        from asciiparticle.sprite import Animation
        s = Sprite({"run": Animation([a, b], fps=2)})
        self.assertIs(s.frame(), a)
        s.update(0.6)
        self.assertIs(s.frame(), b)
        s.update(0.5)
        self.assertIs(s.frame(), a)


class FontTest(unittest.TestCase):
    def test_points(self):
        pts = text_points("I")
        self.assertEqual(len(pts), 13)
        self.assertIn((0.5, 0.5), pts)

    def test_block_fits(self):
        for w, h in ((110, 33), (80, 23), (40, 12)):
            pts = block_points(("ASCII", "PARTICLE"), w, h)
            self.assertTrue(pts)
            if w >= 80:
                self.assertTrue(all(0 <= x < w and 0 <= y < h for x, y in pts))


if __name__ == "__main__":
    unittest.main()
