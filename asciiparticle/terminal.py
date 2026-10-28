"""Raw-mode terminal I/O with a diffing ANSI renderer."""
from __future__ import annotations

import os
import select
import shutil
import sys
from typing import List, Optional, Tuple

from .canvas import Canvas

Snapshot = Tuple[int, int, List[str], List[int], List[int]]

_ENTER = "\x1b[?1049h\x1b[?25l\x1b[?7l\x1b[0m\x1b[2J"
_LEAVE = "\x1b[0m\x1b[?7h\x1b[?25h\x1b[?1049l"


def _sgr(fg: int, bg: int) -> str:
    f = "39" if fg < 0 else "38;5;%d" % fg
    b = "49" if bg < 0 else "48;5;%d" % bg
    return "\x1b[%s;%sm" % (f, b)


def render_diff(canvas: Canvas, prev: Optional[Snapshot] = None) -> Tuple[str, Snapshot]:
    """Return the escape sequence that turns ``prev`` into ``canvas``.

    Only changed cells are written, which keeps output small enough for a
    smooth 30 fps even in Terminal.app.
    """
    w, h = canvas.width, canvas.height
    chars, fgs, bgs = canvas.chars, canvas.fg, canvas.bg
    full = prev is None or prev[0] != w or prev[1] != h
    out: List[str] = []
    if full:
        out.append("\x1b[0m\x1b[2J")
        pc: List[str] = []
        pf: List[int] = []
        pb: List[int] = []
    else:
        pc, pf, pb = prev[2], prev[3], prev[4]
    cur_f: Optional[int] = None
    cur_b: Optional[int] = None
    cx = cy = -1
    for y in range(h):
        base = y * w
        for x in range(w):
            i = base + x
            ch = chars[i]
            f = fgs[i]
            b = bgs[i]
            if full:
                if ch == " " and b < 0:
                    continue
            elif ch == pc[i] and b == pb[i] and (f == pf[i] or ch == " "):
                continue
            if cy != y or cx != x:
                out.append("\x1b[%d;%dH" % (y + 1, x + 1))
            if b != cur_b or (ch != " " and f != cur_f):
                nf = f if (ch != " " or cur_f is None) else cur_f
                out.append(_sgr(nf, b))
                cur_f, cur_b = nf, b
            out.append(ch)
            cx, cy = x + 1, y
    return "".join(out), (w, h, list(chars), list(fgs), list(bgs))


class Terminal:
    """Context manager: alternate screen, hidden cursor, unbuffered keys."""

    def __init__(self, out=None, inp=None) -> None:
        self.out = out or sys.stdout
        self.inp = inp or sys.stdin
        self.fd = self.inp.fileno()
        self._saved = None
        self._prev: Optional[Snapshot] = None

    def __enter__(self) -> "Terminal":
        if os.isatty(self.fd):
            import termios
            import tty
            self._saved = termios.tcgetattr(self.fd)
            tty.setcbreak(self.fd)
        self._write(_ENTER)
        return self

    def __exit__(self, *exc) -> None:
        self._write(_LEAVE)
        if self._saved is not None:
            import termios
            termios.tcsetattr(self.fd, termios.TCSADRAIN, self._saved)

    def size(self) -> Tuple[int, int]:
        s = shutil.get_terminal_size((80, 24))
        return s.columns, s.lines

    def read(self) -> str:
        """Everything typed since the last call, without blocking."""
        chunks = []
        while True:
            ready, _, _ = select.select([self.fd], [], [], 0)
            if not ready:
                break
            data = os.read(self.fd, 1024)
            if not data:
                break
            chunks.append(data)
        return b"".join(chunks).decode("utf-8", "ignore")

    def invalidate(self) -> None:
        self._prev = None

    def present(self, canvas: Canvas) -> None:
        text, self._prev = render_diff(canvas, self._prev)
        if text:
            self._write(text)

    def _write(self, s: str) -> None:
        self.out.write(s)
        self.out.flush()
