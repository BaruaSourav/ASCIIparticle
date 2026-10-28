"""xterm-256 colour helpers.

Every cell stores its colours as xterm-256 palette indices. ``DEFAULT`` (-1)
means "use the terminal's own default colour". The 256-colour palette is
supported by macOS Terminal.app, iTerm2 and practically every modern
terminal, which is why the engine sticks to it instead of 24-bit colour.
"""
from __future__ import annotations

from typing import Dict, List, Sequence, Tuple, Union

DEFAULT = -1

RGB = Tuple[int, int, int]
ColorSpec = Union[str, Sequence[int]]

_CUBE = (0, 95, 135, 175, 215, 255)
_BASE16: List[RGB] = [
    (0, 0, 0), (205, 0, 0), (0, 205, 0), (205, 205, 0),
    (0, 0, 238), (205, 0, 205), (0, 205, 205), (229, 229, 229),
    (127, 127, 127), (255, 0, 0), (0, 255, 0), (255, 255, 0),
    (92, 92, 255), (255, 0, 255), (0, 255, 255), (255, 255, 255),
]


def _build_palette() -> List[RGB]:
    pal = list(_BASE16)
    for r in _CUBE:
        for g in _CUBE:
            for b in _CUBE:
                pal.append((r, g, b))
    for i in range(24):
        v = 8 + 10 * i
        pal.append((v, v, v))
    return pal


PALETTE: List[RGB] = _build_palette()
_cache: Dict[RGB, int] = {}


def _cube_level(v: int) -> int:
    if v < 48:
        return 0
    if v < 115:
        return 1
    return min(5, (v - 35) // 40)


def _dist(a: RGB, b: RGB) -> int:
    return (a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2 + (a[2] - b[2]) ** 2


def rgb(r: int, g: int, b: int) -> int:
    """Return the xterm-256 index closest to an RGB colour."""
    key = (int(r), int(g), int(b))
    hit = _cache.get(key)
    if hit is not None:
        return hit
    cube = 16 + 36 * _cube_level(key[0]) + 6 * _cube_level(key[1]) + _cube_level(key[2])
    avg = sum(key) // 3
    gray_index = 232 + min(23, max(0, (avg - 3) // 10))
    best = cube if _dist(PALETTE[cube], key) <= _dist(PALETTE[gray_index], key) else gray_index
    _cache[key] = best
    return best


def parse(spec: ColorSpec) -> RGB:
    """Parse ``"#rrggbb"`` or an ``(r, g, b)`` sequence."""
    if isinstance(spec, str):
        s = spec.lstrip("#")
        if len(s) == 3:
            s = "".join(c * 2 for c in s)
        return int(s[0:2], 16), int(s[2:4], 16), int(s[4:6], 16)
    return int(spec[0]), int(spec[1]), int(spec[2])


def hex_color(spec: str) -> int:
    return rgb(*parse(spec))


def to_rgb(index: int, default: RGB = (204, 204, 204)) -> RGB:
    """Convert a palette index back to RGB (used by the video exporter)."""
    if index < 0 or index > 255:
        return default
    return PALETTE[index]


def gradient(stops: Sequence[ColorSpec], steps: int) -> List[int]:
    """Evenly interpolate ``steps`` palette indices through colour ``stops``."""
    pts = [parse(s) for s in stops]
    if steps <= 1 or len(pts) == 1:
        return [rgb(*pts[0])] * max(1, steps)
    out = []
    for i in range(steps):
        t = i / (steps - 1) * (len(pts) - 1)
        j = min(int(t), len(pts) - 2)
        f = t - j
        a, b = pts[j], pts[j + 1]
        out.append(rgb(*(round(a[k] + (b[k] - a[k]) * f) for k in range(3))))
    return out


def gray(level: float) -> int:
    """Grayscale ramp index for ``level`` in [0, 1]."""
    level = min(1.0, max(0.0, level))
    return 232 + int(round(level * 23))
