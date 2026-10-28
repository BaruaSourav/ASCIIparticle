"""Command line: play in the terminal, or record scenes to GIF/MP4."""
from __future__ import annotations

import argparse
import sys

from .engine import Engine
from .scenes import SCENES


def _size(text: str):
    try:
        w, h = text.lower().split("x")
        return int(w), int(h)
    except ValueError:
        raise argparse.ArgumentTypeError("size must look like 100x32")


def main(argv=None) -> int:
    names = [s.name for s in SCENES]
    ap = argparse.ArgumentParser(
        prog="asciiparticle",
        description="ASCII particle & sprite engine for the terminal.")
    ap.add_argument("--scene", "-s", default=names[0],
                    help="scene to start in: %s (or 1-%d)" % (", ".join(names), len(names)))
    ap.add_argument("--list", action="store_true", help="list scenes and exit")
    ap.add_argument("--fps", type=int, default=30, help="simulation/render rate (default 30)")
    ap.add_argument("--seed", type=int, default=None, help="random seed")
    ap.add_argument("--demo", action="store_true", help="meadow plays itself")
    rec = ap.add_argument_group("recording (needs Pillow; MP4 also needs ffmpeg)")
    rec.add_argument("--record", metavar="FILE",
                     help="record --scene headless to FILE (.gif or .mp4)")
    rec.add_argument("--reel", metavar="FILE", nargs="+",
                     help="record the scripted demo reel of every scene to FILE(s)")
    rec.add_argument("--seconds", type=float, default=6.0, help="length of --record")
    rec.add_argument("--size", type=_size, default=(110, 34), help="cells, e.g. 110x34")
    rec.add_argument("--video-fps", type=int, default=15, help="frames per second of video")
    rec.add_argument("--font-size", type=int, default=14, help="font size of video")
    args = ap.parse_args(argv)

    if args.list:
        for i, s in enumerate(SCENES, 1):
            print("%d  %-10s %s" % (i, s.name, s.title))
        return 0

    start = int(args.scene) - 1 if args.scene.isdigit() else args.scene
    engine = Engine(SCENES, start=start, fps=args.fps, seed=args.seed)
    try:
        engine.index_of(start)
    except KeyError as exc:
        ap.error(str(exc.args[0]))

    if args.record or args.reel:
        from .export import record
        from .reel import capture, reel

        outputs = args.reel or [args.record]
        gif = next((p for p in outputs if p.lower().endswith(".gif")), None)
        mp4 = next((p for p in outputs if p.lower().endswith(".mp4")), None)
        if not (gif or mp4):
            ap.error("output must end in .gif or .mp4")
        w, h = args.size
        if args.reel:
            frames = reel(w, h, args.video_fps, seed=7 if args.seed is None else args.seed)
        else:
            engine.set_size(w, h)
            engine.switch(start, **({"autopilot": True} if args.demo else {}))
            frames = capture(engine, w, h, args.seconds, args.video_fps)
        n = record(frames, args.video_fps, gif=gif, mp4=mp4, font_size=args.font_size)
        print("wrote %d frames to %s" % (n, ", ".join(p for p in (gif, mp4) if p)))
        return 0

    if not (sys.stdin.isatty() and sys.stdout.isatty()):
        print("asciiparticle needs an interactive terminal (try --record to make a video).",
              file=sys.stderr)
        return 1
    if args.demo:
        engine.set_size(80, 24)
        engine.switch("meadow", autopilot=True)
    try:
        engine.run()
    except KeyboardInterrupt:
        pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
