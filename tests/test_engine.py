import unittest

from asciiparticle.engine import Engine, Entity, Scene, overlaps
from asciiparticle.scenes import SCENES
from asciiparticle.terminal import render_diff


class Counter(Scene):
    name = "counter"

    def setup(self):
        self.ticks = 0
        self.fired = []
        self.after(0.1, lambda: self.fired.append("once"))
        self.every(0.25, lambda: self.fired.append("tick"))

    def update(self, dt):
        self.ticks += 1

    def draw(self, canvas):
        canvas.text(0, 0, str(self.ticks))


class EngineTest(unittest.TestCase):
    def test_headless_steps_and_timers(self):
        e = Engine([Counter], fps=20)
        for c in e.run_headless(30, 10, 20):
            pass
        s = e.scene
        self.assertEqual(s.ticks, 20)
        self.assertEqual(s.fired.count("once"), 1)
        self.assertEqual(s.fired.count("tick"), 4)
        self.assertTrue(c.lines()[0].startswith("20"))
        self.assertIn("ASCIIparticle", c.lines()[-1])

    def test_global_keys(self):
        e = Engine(SCENES, fps=30, seed=1)
        keys = {1: ["tab"], 2: ["3"], 3: ["p"], 5: ["q"]}
        list(e.run_headless(80, 24, 6, lambda eng, i: keys.get(i)))
        self.assertEqual(e.scene.name, SCENES[2].name)
        self.assertTrue(e.paused)
        self.assertFalse(e.running)

    def test_overlaps(self):
        a, b = Entity(5, 5, w=3, h=3), Entity(6, 6, w=3, h=3)
        self.assertTrue(overlaps(a, b))
        b.x = 20
        self.assertFalse(overlaps(a, b))


class ScenesTest(unittest.TestCase):
    """Every bundled scene runs, takes its keys and survives resizes."""

    def test_all_scenes(self):
        keys = ["space", "left", "right", "up", "e", "g", "r", "s", "l", "c", "v", "d", "a", "enter"]
        for cls in SCENES:
            with self.subTest(scene=cls.name):
                e = Engine(SCENES, start=cls.name, seed=4)
                prev = None
                script = lambda eng, i: [keys[i % len(keys)]] if i % 7 == 0 else []
                for i, c in enumerate(e.run_headless(100, 30, 120, script)):
                    if i == 60:
                        e.set_size(45, 14)
                    if i == 90:
                        e.set_size(160, 48)
                    _, prev = render_diff(c, prev)
                self.assertEqual(e.scene.name, cls.name)
                self.assertTrue(any(ch != " " for ch in c.chars))

    def test_meadow_autopilot_catches_fireflies(self):
        e = Engine(SCENES, seed=11)
        e.set_size(100, 30)
        e.switch("meadow", autopilot=True)
        for _ in e.run_headless(100, 30, 30 * 30):
            pass
        self.assertGreater(e.scene.score, 0)


if __name__ == "__main__":
    unittest.main()
