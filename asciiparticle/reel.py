"""Scripted, deterministic demo reel used to make the README video."""
from __future__ import annotations

from typing import Callable, Dict, Iterator, List, Optional, Sequence

from .canvas import Canvas
from .engine import Engine

KeyScript = Optional[Callable[[Engine, int], Optional[Sequence[str]]]]


def keys_at(fps: int, schedule: Dict[float, Sequence[str]]) -> Callable[[Engine, int], List[str]]:
    """Press keys at given times (seconds) within a segment."""
    frames = {int(round(t * fps)): list(keys) for t, keys in schedule.items()}
    return lambda engine, i: frames.get(i, [])


def capture(engine: Engine, width: int, height: int, seconds: float, fps: int,
            script: KeyScript = None, warmup: float = 0.0) -> Iterator[Canvas]:
    """Run the current scene headless, yielding one canvas per output frame.

    Physics always runs at the engine's own rate; frames are sampled down to
    ``fps`` for the recording. ``warmup`` seconds are simulated unrecorded
    first, so effects are already going when the clip starts.
    """
    for _ in engine.run_headless(width, height, int(warmup * engine.fps)):
        pass
    steps = max(1, round(engine.fps / fps))
    total = int(seconds * fps) * steps
    for i, canvas in enumerate(engine.run_headless(width, height, total, script)):
        if i % steps == steps - 1:
            yield canvas


def reel(width: int, height: int, fps: int = 15, seed: int = 7) -> Iterator[Canvas]:
    from .scenes import SCENES

    engine = Engine(SCENES, fps=30, seed=seed)
    engine.set_size(width, height)
    k = engine.fps
    # (scene, seconds, options, key script, warm-up seconds)
    segments = [
        ("banner", 5.0, {}, keys_at(k, {2.6: ["space"]}), 0.0),
        ("meadow", 7.0, {"autopilot": True}, keys_at(k, {3.0: ["g"]}), 0.5),
        ("flow", 5.0, {}, keys_at(k, {3.0: ["g"]}), 2.0),
        ("fireworks", 5.0, {}, keys_at(k, {0.2: ["space"], 0.9: ["space"], 2.2: ["space"]}), 1.5),
        ("campfire", 6.0, {}, keys_at(k, {1.5: ["r"], 3.0: ["l"], 4.6: ["right", "right"]}), 2.0),
    ]
    for name, seconds, options, script, warmup in segments:
        engine.switch(name, **options)
        yield from capture(engine, width, height, seconds, fps, script, warmup)
