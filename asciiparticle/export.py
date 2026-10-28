"""Render canvases to images and record GIF / MP4 videos.

Needs Pillow (``pip install pillow``). MP4 output also needs ``ffmpeg`` on
PATH (``brew install ffmpeg`` on a Mac). Playing in the terminal needs
neither.
"""
from __future__ import annotations

import os
import shutil
import subprocess
from typing import Dict, Iterable, Iterator, List, Optional, Tuple

from .canvas import Canvas
from .color import PALETTE

FONT_CANDIDATES = [
    "/System/Library/Fonts/Menlo.ttc",
    "/System/Library/Fonts/SFNSMono.ttf",
    "/Library/Fonts/Menlo.ttc",
    "/usr/share/fonts/truetype/jetbrains-mono/JetBrainsMono-Regular.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationMono-Regular.ttf",
    "C:/Windows/Fonts/consola.ttf",
]

BACKGROUND = (12, 12, 14)
FOREGROUND = (210, 210, 210)


def _require_pillow():
    try:
        from PIL import Image, ImageDraw, ImageFont  # noqa: F401
    except ImportError as exc:  # pragma: no cover - depends on environment
        raise SystemExit("Recording needs Pillow: python3 -m pip install pillow") from exc
    return Image, ImageDraw, ImageFont


class FrameRenderer:
    """Rasterises a Canvas the way a terminal would draw it."""

    def __init__(self, font_path: Optional[str] = None, font_size: int = 14) -> None:
        Image, ImageDraw, ImageFont = _require_pillow()
        self._Image = Image
        self._ImageDraw = ImageDraw
        path = font_path or next((p for p in FONT_CANDIDATES if os.path.exists(p)), None)
        self.font = ImageFont.truetype(path, font_size) if path else ImageFont.load_default()
        ascent, descent = self.font.getmetrics()
        self.cell_w = max(1, int(round(self.font.getlength("M"))))
        self.cell_h = ascent + descent
        self._masks: Dict[str, object] = {}

    def _mask(self, ch: str):
        m = self._masks.get(ch)
        if m is None:
            m = self._Image.new("L", (self.cell_w, self.cell_h), 0)
            self._ImageDraw.Draw(m).text((0, 0), ch, fill=255, font=self.font)
            self._masks[ch] = m
        return m

    def size(self, canvas: Canvas) -> Tuple[int, int]:
        return canvas.width * self.cell_w, canvas.height * self.cell_h

    def render(self, canvas: Canvas):
        cw, chh = self.cell_w, self.cell_h
        img = self._Image.new("RGB", self.size(canvas), BACKGROUND)
        draw = self._ImageDraw.Draw(img)
        w = canvas.width
        chars, fgs, bgs = canvas.chars, canvas.fg, canvas.bg
        for i, b in enumerate(bgs):
            if b >= 0:
                x, y = (i % w) * cw, (i // w) * chh
                draw.rectangle((x, y, x + cw - 1, y + chh - 1), fill=PALETTE[b])
        for i, ch in enumerate(chars):
            if ch != " ":
                f = fgs[i]
                img.paste(PALETTE[f] if f >= 0 else FOREGROUND,
                          ((i % w) * cw, (i // w) * chh), self._mask(ch))
        return img


def _xterm_palette_image():
    Image, _, _ = _require_pillow()
    pal = Image.new("P", (1, 1))
    flat: List[int] = []
    for r, g, b in PALETTE:
        flat += [r, g, b]
    pal.putpalette(flat)
    return pal


def to_palette(img, pal=None):
    """Map an RGB frame onto the xterm palette (GIFs hold 256 colours)."""
    Image, _, _ = _require_pillow()
    return img.quantize(palette=pal or _xterm_palette_image(), dither=Image.Dither.NONE)


def save_gif(images: Iterable, path: str, fps: float) -> int:
    """Write frames as a looping GIF using the xterm palette; returns frame count."""
    pal = _xterm_palette_image()
    frames = [im if im.mode == "P" else to_palette(im, pal) for im in images]
    if not frames:
        raise ValueError("no frames to save")
    frames[0].save(path, save_all=True, append_images=frames[1:], loop=0,
                   duration=int(round(1000 / fps)), optimize=True, disposal=1)
    return len(frames)


class Mp4Writer:
    """Streams RGB frames into ffmpeg's H.264 encoder."""

    def __init__(self, path: str, size: Tuple[int, int], fps: float) -> None:
        exe = shutil.which("ffmpeg")
        if exe is None:
            raise SystemExit("MP4 output needs ffmpeg on PATH (macOS: brew install ffmpeg)")
        self.w, self.h = size[0] - size[0] % 2, size[1] - size[1] % 2
        self.proc = subprocess.Popen(
            [exe, "-loglevel", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24",
             "-s", "%dx%d" % (self.w, self.h), "-r", str(fps), "-i", "-",
             "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "20", "-preset", "slow",
             "-movflags", "+faststart", path],
            stdin=subprocess.PIPE)

    def write(self, img) -> None:
        if img.size != (self.w, self.h):
            img = img.crop((0, 0, self.w, self.h))
        self.proc.stdin.write(img.tobytes())

    def close(self) -> None:
        self.proc.stdin.close()
        if self.proc.wait() != 0:
            raise RuntimeError("ffmpeg failed")


def record(canvases: Iterator[Canvas], fps: float, gif: Optional[str] = None,
           mp4: Optional[str] = None, font_size: int = 14) -> int:
    """Render a stream of canvases to a GIF and/or MP4. Returns the frame count."""
    renderer = FrameRenderer(font_size=font_size)
    pal = _xterm_palette_image() if gif else None
    gif_frames = []
    writer: Optional[Mp4Writer] = None
    n = 0
    for canvas in canvases:
        img = renderer.render(canvas)
        if mp4:
            if writer is None:
                writer = Mp4Writer(mp4, img.size, fps)
            writer.write(img)
        if gif:
            gif_frames.append(to_palette(img, pal))
        n += 1
    if writer is not None:
        writer.close()
    if gif:
        save_gif(gif_frames, gif, fps)
    return n
