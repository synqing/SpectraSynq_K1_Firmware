"""lgp_animate.py — stitch a fixture's FULL frame sequence into an animated GIF of
light_mode_bloom rendered through the K1 LGP optics (lgp_optics.plate_image), at
the validated ~5.48:1 plate-face aspect, dual-channel (warm bottom edge + cool top
edge). Ping-pong loop so any fixture loops smoothly.

Pipeline (per frame): render_replay (real firmware bloom path) -> hex LED bytes ->
(160,3) RGB -> plate_image(bottom, top) -> PIL frame -> animated GIF.

Usage: python3 lgp_animate.py [--fixture broadband-swell] [--fps 24] [--out PATH]
Output dir: results/bloom/lgp_sample/ (gitignored — regenerate locally).
"""
import argparse
import sys
from pathlib import Path

import numpy as np
from PIL import Image

HERE = Path(__file__).resolve().parent
HARNESS = HERE.parent
sys.path.insert(0, str(HARNESS))
import render_replay as rr  # noqa: E402
import lgp_optics as lo  # noqa: E402

OUT_DIR = HARNESS / "results" / "bloom" / "lgp_sample"

# Two visibly-distinct bloom looks, one per edge (the dual-channel composite).
PARAMS_BOTTOM = {"mood": 0.5, "saturation": 0.9, "square_iter": 1.0, "chroma": 1.0,
                 "chromatic_mode": True}                                   # warm
PARAMS_TOP = {"mood": 0.8, "saturation": 1.0, "square_iter": 1.0, "chroma": 1.0,
              "palette_mode": True, "palette_index": 2, "chromatic_mode": False,
              "hue_position": 0.6}                                         # cool


def hex_to_rgb(hex_str):
    b = bytes.fromhex(hex_str)
    return np.frombuffer(b, dtype=np.uint8).astype(np.float64).reshape(lo.LED_COUNT, 3) / 255.0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--fixture", default="broadband-swell")
    ap.add_argument("--fps", type=int, default=24)
    ap.add_argument("--out", default=None)
    ap.add_argument("--no-pingpong", action="store_true")
    args = ap.parse_args(argv)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out = Path(args.out) if args.out else (OUT_DIR / f"bloom_lgp_{args.fixture}.gif")

    ok, binary, comp = rr.build_binary(OUT_DIR / "_build", mode="bloom")
    if not ok:
        print("COMPILE FAILED:\n" + (comp.get("stderr") or "")[:1500], file=sys.stderr)
        return 1
    frames = rr.load_fixture(rr.FIXTURE_DIR / f"{args.fixture}.ndjson")
    ok_b, hex_b, _ = rr.replay_frames(binary, frames, PARAMS_BOTTOM)
    ok_t, hex_t, _ = rr.replay_frames(binary, frames, PARAMS_TOP)
    if not (ok_b and ok_t and len(hex_b) == len(frames) == len(hex_t)):
        print("REPLAY FAILED", ok_b, ok_t, len(hex_b), len(hex_t), file=sys.stderr)
        return 1

    imgs = [Image.fromarray(lo.plate_image(hex_to_rgb(hb), hex_to_rgb(ht)), "RGB")
            for hb, ht in zip(hex_b, hex_t)]
    if not args.no_pingpong and len(imgs) > 2:
        imgs = imgs + imgs[-2:0:-1]          # forward then back -> seamless loop

    duration_ms = max(20, round(1000 / args.fps))
    imgs[0].save(out, save_all=True, append_images=imgs[1:], duration=duration_ms,
                 loop=0, optimize=True, disposal=2)
    px = imgs[0].size
    print("wrote %d-frame GIF %dx%d (~%.1f:1) @ %dfps -> %s"
          % (len(imgs), px[0], px[1], px[0] / px[1], args.fps, out))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
