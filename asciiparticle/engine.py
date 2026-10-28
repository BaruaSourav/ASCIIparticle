"""Game loop, scenes and entities."""
from __future__ import annotations

import random
import time
from typing import Callable, Iterable, Iterator, List, Optional, Sequence, Type, Union

from .canvas import Canvas
from .color import DEFAULT
from .input import Input, parse_keys
from .sprite import Sprite

Script = Callable[["Engine", int], Optional[Iterable[str]]]


class Scene:
    """Override ``setup``, ``resize``, ``update``, ``draw`` and optionally ``hud``.

    ``width``/``height`` are the playable area (the status bar sits below
    it). ``rng`` is the engine's seeded RNG so recordings are repeatable.
    """

    name = "scene"
    title = "Scene"
    help_lines: Sequence[str] = ()

    def __init__(self, engine: "Engine") -> None:
        self.engine = engine
        self.input = engine.input
        self.rng = engine.rng
        self.width = engine.width
        self.height = engine.view_height
        self.time = 0.0
        self._timers: List[list] = []

    def setup(self) -> None:
        pass

    def resize(self, width: int, height: int) -> None:
        pass

    def update(self, dt: float) -> None:
        pass

    def draw(self, canvas: Canvas) -> None:
        pass

    def hud(self) -> str:
        return ""

    def after(self, delay: float, fn: Callable[[], None]) -> None:
        """Call ``fn`` once, ``delay`` seconds from now."""
        self._timers.append([delay, 0.0, fn])

    def every(self, interval: float, fn: Callable[[], None]) -> None:
        """Call ``fn`` every ``interval`` seconds."""
        self._timers.append([interval, interval, fn])

    def _tick(self, dt: float) -> None:
        self.time += dt
        if not self._timers:
            return
        due = []
        keep = []
        for timer in self._timers:
            timer[0] -= dt
            if timer[0] <= 1e-9:  # tolerate float drift on exact multiples of dt
                due.append(timer)
                if timer[1] > 0.0:
                    timer[0] += timer[1]
                    keep.append(timer)
            else:
                keep.append(timer)
        self._timers = keep
        for timer in due:
            timer[2]()


class Entity:
    """Something with a position and velocity, usually drawn with a Sprite.

    (x, y) is the bottom-centre cell; ``w``/``h`` give its hit box.
    """

    def __init__(self, x: float = 0.0, y: float = 0.0, sprite: Optional[Sprite] = None,
                 w: float = 1.0, h: float = 1.0) -> None:
        self.x = x
        self.y = y
        self.vx = 0.0
        self.vy = 0.0
        self.w = w
        self.h = h
        self.sprite = sprite
        self.flip = False
        self.alive = True

    @property
    def rect(self):
        return self.x - self.w / 2, self.y - self.h + 1, self.w, self.h

    def update(self, dt: float) -> None:
        if self.sprite is not None:
            self.sprite.update(dt)

    def draw(self, canvas: Canvas) -> None:
        if self.sprite is not None:
            self.sprite.draw(canvas, self.x, self.y, flip=self.flip)


def overlaps(a: Entity, b: Entity) -> bool:
    ax, ay, aw, ah = a.rect
    bx, by, bw, bh = b.rect
    return ax < bx + bw and bx < ax + aw and ay < by + bh and by < ay + ah


class Engine:
    """Runs scenes at a fixed timestep, in a terminal or headless."""

    def __init__(self, scenes: Sequence[Type[Scene]], start: Union[int, str] = 0, fps: int = 30,
                 seed: Optional[int] = None, status_bar: bool = True) -> None:
        self.scene_classes = list(scenes)
        self.start = start
        self.fps = fps
        self.dt = 1.0 / fps
        self.rng = random.Random(seed)
        self.input = Input()
        self.status_bar = status_bar
        self.width = 80
        self.height = 24
        self.canvas = Canvas(self.width, self.height)
        self.scene: Optional[Scene] = None
        self.scene_index = 0
        self.running = False
        self.paused = False
        self.show_help = False
        self.clock = 0.0
        self.frame = 0
        self.measured_fps: Optional[float] = None

    @property
    def view_height(self) -> int:
        return max(1, self.height - (1 if self.status_bar else 0))

    def index_of(self, which: Union[int, str]) -> int:
        if isinstance(which, int):
            return which % len(self.scene_classes)
        for i, cls in enumerate(self.scene_classes):
            if cls.name == which:
                return i
        raise KeyError("unknown scene %r (have: %s)" % (
            which, ", ".join(c.name for c in self.scene_classes)))

    def switch(self, which: Union[int, str], **options) -> Scene:
        self.scene_index = self.index_of(which)
        self.input.reset()
        self.paused = False
        scene = self.scene_classes[self.scene_index](self)
        for key, value in options.items():
            setattr(scene, key, value)
        self.scene = scene
        scene.setup()
        return scene

    def set_size(self, width: int, height: int) -> None:
        width, height = max(20, width), max(8, height)
        if (width, height) == (self.width, self.height):
            return
        self.width, self.height = width, height
        self.canvas.resize(width, height)
        if self.scene is not None:
            self.scene.width, self.scene.height = width, self.view_height
            self.scene.resize(width, self.view_height)

    def quit(self) -> None:
        self.running = False

    def _global_key(self, key: str) -> None:
        if key in ("q", "esc"):
            self.quit()
        elif key == "tab":
            self.switch(self.scene_index + 1)
        elif key.isdigit() and 1 <= int(key) <= len(self.scene_classes):
            self.switch(int(key) - 1)
        elif key == "p":
            self.paused = not self.paused
        elif key in ("h", "?"):
            self.show_help = not self.show_help

    def step(self) -> None:
        """Advance one fixed timestep."""
        self.input.begin_frame(self.clock)
        for key in list(self.input.events):
            before = self.scene
            self._global_key(key)
            if self.scene is not before:
                self.input.begin_frame(self.clock)
                break
        scene = self.scene
        if scene is not None and not self.paused:
            scene.update(self.dt)
            scene._tick(self.dt)
        self.clock += self.dt
        self.frame += 1

    def render(self) -> Canvas:
        c = self.canvas
        c.clear()
        if self.scene is not None:
            self.scene.draw(c)
        if self.status_bar:
            self._draw_status(c)
        if self.paused:
            self._center_box(c, ["PAUSED", "", "press P to resume"])
        elif self.show_help and self.scene is not None:
            lines = list(self.scene.help_lines) + [
                "",
                "1-%d     switch scene" % len(self.scene_classes),
                "Tab     next scene",
                "P       pause",
                "H       toggle this help",
                "Q/Esc   quit",
            ]
            self._center_box(c, [self.scene.title, ""] + lines)
        return c

    def _draw_status(self, c: Canvas) -> None:
        y = self.height - 1
        c.fill(0, y, self.width, 1, " ", DEFAULT, 236)
        scene = self.scene
        left = " ASCIIparticle | %d:%s " % (self.scene_index + 1, scene.name if scene else "-")
        hud = scene.hud() if scene else ""
        right = " H help  Tab next  Q quit "
        if self.measured_fps is not None:
            right = " %2.0ffps |%s" % (self.measured_fps, right)
        c.text(0, y, left, 213, 236)
        x = len(left)
        if hud and x + len(hud) + 2 < self.width - len(right):
            c.text(x + 1, y, hud, 252, 236)
        if len(left) + len(right) < self.width:
            c.text(self.width - len(right), y, right, 245, 236)

    def _center_box(self, c: Canvas, lines: List[str]) -> None:
        w = min(self.width - 2, max(len(s) for s in lines) + 6)
        h = min(self.view_height, len(lines) + 2)
        x0 = (self.width - w) // 2
        y0 = max(0, (self.view_height - h) // 2)
        c.fill(x0, y0, w, h, " ", DEFAULT, 235)
        c.text(x0, y0, "+" + "-" * (w - 2) + "+", 244, 235)
        c.text(x0, y0 + h - 1, "+" + "-" * (w - 2) + "+", 244, 235)
        for i in range(1, h - 1):
            c.put(x0, y0 + i, "|", 244, 235)
            c.put(x0 + w - 1, y0 + i, "|", 244, 235)
        for i, line in enumerate(lines[:h - 2]):
            col = 229 if i == 0 else 252
            c.text(x0 + 3, y0 + 1 + i, line[:w - 6], col, 235)

    def run(self) -> None:
        """Play in the current terminal until the user quits."""
        from .terminal import Terminal

        self.running = True
        with Terminal() as term:
            self.set_size(*term.size())
            if self.scene is None:
                self.switch(self.start)
            next_tick = time.perf_counter()
            fps_t = next_tick
            fps_n = 0
            while self.running:
                size = term.size()
                if size != (self.width, self.height):
                    self.set_size(*size)
                    term.invalidate()
                for key in parse_keys(term.read()):
                    self.input.feed(key)
                self.step()
                if not self.running:
                    break
                term.present(self.render())
                fps_n += 1
                now = time.perf_counter()
                if now - fps_t >= 1.0:
                    self.measured_fps = fps_n / (now - fps_t)
                    fps_t, fps_n = now, 0
                next_tick += self.dt
                if next_tick > now:
                    time.sleep(next_tick - now)
                elif now - next_tick > 0.25:
                    next_tick = now

    def run_headless(self, width: int, height: int, frames: int,
                     script: Optional[Script] = None) -> Iterator[Canvas]:
        """Step without a terminal, yielding the canvas after every frame.

        ``script(engine, i)`` may return key names to "press" on frame ``i``.
        """
        self.set_size(width, height)
        if self.scene is None:
            self.switch(self.start)
        for i in range(frames):
            if script is not None:
                for key in script(self, i) or ():
                    self.input.feed(key)
            self.step()
            yield self.render()
