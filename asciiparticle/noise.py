"""Seeded value noise: smooth, cheap randomness for wind and flow."""
from __future__ import annotations

import math
import random


class Noise:
    def __init__(self, seed: int = 0) -> None:
        rng = random.Random(seed)
        perm = list(range(256))
        rng.shuffle(perm)
        self.perm = perm + perm
        self.values = [rng.uniform(-1.0, 1.0) for _ in range(256)]

    def noise1(self, x: float) -> float:
        """1-D noise in [-1, 1]."""
        xi = math.floor(x)
        xf = x - xi
        xi &= 255
        u = xf * xf * (3.0 - 2.0 * xf)
        a = self.values[self.perm[xi]]
        b = self.values[self.perm[xi + 1]]
        return a + (b - a) * u

    def noise2(self, x: float, y: float) -> float:
        """2-D noise in [-1, 1]."""
        xi = math.floor(x)
        yi = math.floor(y)
        xf = x - xi
        yf = y - yi
        xi &= 255
        yi &= 255
        p = self.perm
        v = self.values
        u = xf * xf * (3.0 - 2.0 * xf)
        w = yf * yf * (3.0 - 2.0 * yf)
        aa = v[p[p[xi] + yi]]
        ba = v[p[p[xi + 1] + yi]]
        ab = v[p[p[xi] + yi + 1]]
        bb = v[p[p[xi + 1] + yi + 1]]
        x1 = aa + (ba - aa) * u
        x2 = ab + (bb - ab) * u
        return x1 + (x2 - x1) * w

    def fbm1(self, x: float, octaves: int = 3) -> float:
        total = 0.0
        amp = 1.0
        norm = 0.0
        for _ in range(octaves):
            total += self.noise1(x) * amp
            norm += amp
            amp *= 0.5
            x = x * 2.03 + 17.0
        return total / norm
