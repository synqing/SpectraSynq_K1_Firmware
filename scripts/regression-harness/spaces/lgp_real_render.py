"""lgp_real_render.py — REGENERATE light_mode_bloom through the REAL-PLATE-calibrated
optics (lgp_optics.K1_REAL_V1), mimicking dscf_05: warm chromatic bloom on the BOTTOM
edge + a magenta/purple palette bloom on the TOP edge, over broadband-swell.

Writes to results/bloom/lgp_sample/ (gitignored):
  * recalibrated still PNGs (real_v1_*.png)
  * recalibrated GIF (bloom_lgp_REAL_V1_broadband-swell.gif)
  * a SIDE-BY-SIDE comparison PNG: real dscf_05 (cropped to the lit band) ABOVE the
    recalibrated render at the same aspect (real_vs_model_comparison.png)

Pipeline: render_replay (real firmware bloom path) -> hex LED bytes -> (160,3) RGB
-> plate_image(bottom, top, optics=K1_REAL_V1) -> PIL.
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
CALIB = Path("/tmp/k1_real_calib")
H, W = 256, 1402  # ~5.48:1 plate face (matches LGP_LENGTH/WIDTH); long axis horizontal? no:
# plate face is 329mm(long, LED axis) x 60mm(width). We render with the LED axis ACROSS
# the image width and depth vertical -> W=long, H=short. 1402/256 ~= 5.48.

# Bottom: warm chromatic bloom — the DOMINANT bright near-white hotspot edge, like
# dscf_05. High brightness/saturation so it reads as the primary feature.
PARAMS_BOTTOM = {"mood": 0.5, "saturation": 0.85, "square_iter": 1.0, "chroma": 1.0,
                 "chromatic_mode": True}
# Top: magenta/purple palette bloom — the SECONDARY edge (dimmer than the warm edge
# in dscf_05). Palettes.h gGradientPalettes order: ...Colorfull=25,
# Magenta_Evening=26, Pink_Purple=27, Sunset_Real=0... Use Magenta_Evening (26).
PARAMS_TOP = {"mood": 0.7, "saturation": 1.0, "square_iter": 1.0, "chroma": 1.0,
              "palette_mode": True, "palette_index": 26, "chromatic_mode": False,
              "hue_position": 0.85}
# dscf_05 has the warm edge brighter than the magenta edge. The bloom firmware path
# drives both channels comparably, so scale the TOP channel down post-decode to make
# the warm bottom dominant (matches the real plate's brightness hierarchy).
TOP_SCALE = 0.62


def hex_to_rgb(h):
    return np.frombuffer(bytes.fromhex(h), dtype=np.uint8).astype(np.float64).reshape(lo.LED_COUNT, 3) / 255.0


def crop_real_band(path):
    """Crop dscf_05 to its lit plate band (measured rows 378..629, cols 140..1760)."""
    im = np.asarray(Image.open(path).convert("RGB"))
    return Image.fromarray(im[378:630, 140:1761])


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    print("compiling bloom render path ...")
    ok, binary, comp = rr.build_binary(OUT / "_build", mode="bloom")
    if not ok:
        print("COMPILE FAILED:\n", (comp.get("stderr") or "")[:1500]); return 1
    frames = rr.load_fixture(rr.FIXTURE_DIR / "broadband-swell.ndjson")
    print("frames:", len(frames))
    ok_b, hex_b, _ = rr.replay_frames(binary, frames, PARAMS_BOTTOM)
    ok_t, hex_t, _ = rr.replay_frames(binary, frames, PARAMS_TOP)
    if not (ok_b and ok_t and len(hex_b) == len(frames) == len(hex_t)):
        print("REPLAY FAILED", ok_b, ok_t, len(hex_b), len(hex_t)); return 1

    # pick representative bright frames
    energy = [bytes.fromhex(h).count(0) for h in hex_b]
    order = sorted(range(len(hex_b)), key=lambda i: energy[i])  # fewest zeros first
    picks = sorted(set([order[0], order[len(order)//4], len(hex_b)//2, order[-1]]))

    written = []
    peak = order[0]
    for fi in picks:
        bottom = hex_to_rgb(hex_b[fi]); top = hex_to_rgb(hex_t[fi]) * TOP_SCALE
        img = lo.plate_image(bottom, top, height=H, width=W, optics=lo.K1_REAL_V1)
        p = OUT / f"real_v1_frame{fi:04d}.png"
        Image.fromarray(img, "RGB").save(p); written.append(p)

    # --- recalibrated GIF (full sequence, ping-pong) ---
    imgs = [Image.fromarray(lo.plate_image(hex_to_rgb(hb), hex_to_rgb(ht) * TOP_SCALE,
            height=H, width=W, optics=lo.K1_REAL_V1), "RGB")
            for hb, ht in zip(hex_b, hex_t)]
    if len(imgs) > 2:
        imgs = imgs + imgs[-2:0:-1]
    gif = OUT / "bloom_lgp_REAL_V1_broadband-swell.gif"
    imgs[0].save(gif, save_all=True, append_images=imgs[1:], duration=42, loop=0,
                 optimize=True, disposal=2)
    written.append(gif)

    # --- SIDE-BY-SIDE comparison: real (top) above recalibrated render (bottom) ---
    real = crop_real_band(CALIB / "dscf_05.png")
    cmp_w = 1402
    real_r = real.resize((cmp_w, round(cmp_w * real.height / real.width)))
    model_img = Image.fromarray(lo.plate_image(hex_to_rgb(hex_b[peak]),
                hex_to_rgb(hex_t[peak]) * TOP_SCALE, height=256, width=cmp_w,
                optics=lo.K1_REAL_V1))
    gap = 16
    canvas = Image.new("RGB", (cmp_w, real_r.height + gap + model_img.height), (20, 20, 20))
    canvas.paste(real_r, (0, 0))
    canvas.paste(model_img, (0, real_r.height + gap))
    cmp_path = OUT / "real_vs_model_comparison.png"
    canvas.save(cmp_path); written.append(cmp_path)

    print("\nWROTE:")
    for p in written:
        print("  ", p)
    print("peak frame:", peak)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
