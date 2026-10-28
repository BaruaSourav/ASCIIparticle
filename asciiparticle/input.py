"""Keyboard decoding and "held key" emulation.

Terminals only report key presses, never releases. A key therefore counts as
held for a short window after each press; macOS key-repeat keeps refreshing
that window while the key stays down.
"""
from __future__ import annotations

from typing import Dict, List

_SIMPLE = {
    " ": "space", "\r": "enter", "\n": "enter", "\t": "tab",
    "\x7f": "backspace", "\x08": "backspace",
}
_FINAL = {"A": "up", "B": "down", "C": "right", "D": "left", "H": "home", "F": "end"}


def parse_keys(data: str) -> List[str]:
    """Turn raw terminal input into key names (``"left"``, ``"a"``, ``"space"``...)."""
    keys: List[str] = []
    i = 0
    n = len(data)
    while i < n:
        c = data[i]
        if c == "\x1b":
            if i + 1 < n and data[i + 1] in "[O":
                j = i + 2
                while j < n and not ("@" <= data[j] <= "~"):
                    j += 1
                if j < n and data[j] in _FINAL:
                    keys.append(_FINAL[data[j]])
                i = j + 1
                continue
            keys.append("esc")
            i += 1
            continue
        name = _SIMPLE.get(c)
        if name is None:
            name = c.lower() if c.isalpha() else c
        keys.append(name)
        i += 1
    return keys


class Input:
    """Per-frame key state: ``pressed`` this frame, or ``held`` recently."""

    first_hold = 0.42   # longer than macOS' default initial repeat delay
    repeat_hold = 0.14  # longer than macOS' default repeat interval

    def __init__(self) -> None:
        self.now = 0.0
        self._until: Dict[str, float] = {}
        self._queue: List[str] = []
        self.events: List[str] = []

    def feed(self, key: str) -> None:
        self._queue.append(key)

    def begin_frame(self, now: float) -> None:
        self.now = now
        self.events = []
        for key in self._queue:
            until = self._until.get(key)
            repeating = until is not None and now <= until + 0.05
            self._until[key] = now + (self.repeat_hold if repeating else self.first_hold)
            self.events.append(key)
        self._queue = []

    def pressed(self, *keys: str) -> bool:
        return any(k in self.events for k in keys)

    def held(self, *keys: str) -> bool:
        now = self.now
        return any(now <= self._until.get(k, -1.0) for k in keys)

    def release(self, *keys: str) -> None:
        for k in keys:
            self._until.pop(k, None)

    def reset(self) -> None:
        self._until.clear()
        self._queue = []
        self.events = []
