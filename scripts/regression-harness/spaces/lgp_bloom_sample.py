"""lgp_bloom_sample.py — render light_mode_bloom's ACTUAL LED output through the
K1 LGP optics port (lgp_optics.plate_image) and write representative plate PNGs.

DELIVERABLE 3. Pipeline:
  render_replay.build_binary(mode='bloom')  ->  compile firmware bloom render path
  render_replay.replay_frames(binary, broadband-swell fixture, params)  ->  hex bytes
  decode hex -> (160,3) RGB float in [0,1]  (harness emits RGB, linear, 0..255)
  feed bloom -> BOTTOM edge; a second bloom (different params) -> TOP edge
  lgp_optics.plate_image(bottom, top) -> uint8 plate image -> PNG

Output dir: scripts/regression-harness/results/bloom/lgp_sample/ (gitignored).
"""
import sys
from pathlib import Path

import numpy as np
from PIL import Image

HERE = Path(__file__).resolve().parent
HARNESS = HERE.parent
sys.path.insert(0, str(HARNESS))
import render_replay as rr  # noqa: E402
import lgp_optics as lo  # noqa: E402

OUT = HARNESS / "results" / "bloom" / "lgp_sample"
OUT.mkdir(parents=True, exist_ok=True)

H, W = 256, 512


def hex_to_rgb(hex_str):
    """Harness 'R' line: hex of 160*3 bytes, RGB per LED, linear 0..255."""
    b = bytes.fromhex(hex_str)
    arr = np.frombuffer(b, dtype=np.uint8).astype(np.float64).reshape(lo.LED_COUNT, 3)
    return arr / 255.0


def main():
    workdir = OUT / "_build"
    print("compiling bloom render path ...")
    ok, binary, comp = rr.build_binary(workdir, mode="bloom")
    if not ok:
        print("COMPILE FAILED:\n", comp["stderr"][:2000])
        return 1
    print("compiled:", comp["compiler"])

    frames = rr.load_fixture(rr.FIXTURE_DIR / "broadband-swell.ndjson")
    print("fixture frames:", len(frames))

    # Bottom channel: bloom, default-ish warm params.
    params_b = {"mood": 0.5, "saturation": 0.9, "square_iter": 1.0, "chroma": 1.0,
                "chromatic_mode": True}
    ok_b, hex_b, _ = rr.replay_frames(binary, frames, params_b)
    # Top channel: a SECOND bloom with different params (cooler / palette mode) so
    # the two edges are visibly distinct, exercising the dual-channel composite.
    params_t = {"mood": 0.8, "saturation": 1.0, "square_iter": 1.0, "chroma": 1.0,
                "palette_mode": True, "palette_index": 2, "chromatic_mode": False,
                "hue_position": 0.6}
    ok_t, hex_t, _ = rr.replay_frames(binary, frames, params_t)
    if not (ok_b and ok_t and len(hex_b) == len(frames)):
        print("REPLAY FAILED", ok_b, ok_t, len(hex_b))
        return 1

    # Representative frames: pick the frames with the most lit LEDs (swell peaks)
    # plus a couple of fixed indices, so the PNGs actually show something.
    energy = [int(bytes.fromhex(h).count(0) * -1) for h in hex_b]  # fewer zeros = brighter
    order = sorted(range(len(hex_b)), key=lambda i: energy[i])
    picks = sorted(set([order[0], order[len(order) // 4], len(hex_b) // 2,
                        order[-1], min(len(hex_b) - 1, 5)]))

    written = []
    for fi in picks:
        bottom = hex_to_rgb(hex_b[fi])
        top = hex_to_rgb(hex_t[fi])

        # (a) bloom on bottom only (zeros top) — the task's minimum requirement
        img_b = lo.plate_image(bottom, np.zeros_like(top), height=H, width=W)
        p = OUT / f"bloom_bottom_frame{fi:04d}.png"
        Image.fromarray(img_b, "RGB").save(p)
        written.append(p)

        # (b) dual: bloom bottom + second bloom top
        img_d = lo.plate_image(bottom, top, height=H, width=W)
        p = OUT / f"bloom_dual_frame{fi:04d}.png"
        Image.fromarray(img_d, "RGB").save(p)
        written.append(p)

    # Also dump the raw 160-px LED strips (1px tall, nearest) for reference.
    peak = order[0]
    strip_b = (hex_to_rgb(hex_b[peak]) * 255).astype(np.uint8).reshape(1, lo.LED_COUNT, 3)
    strip_b = np.repeat(strip_b, 16, axis=0)
    p = OUT / f"strip_bottom_frame{peak:04d}.png"
    Image.fromarray(strip_b, "RGB").save(p)
    written.append(p)

    print("\nWROTE", len(written), "PNGs to", OUT)
    for p in written:
        print("  ", p)
    print("\npeak (brightest) bloom frame index:", peak)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
