"""lgp_real_measure.py — rigorous measurement of the REAL K1 LGP plate from the
hardware captures in /tmp/k1_real_calib/, to calibrate lgp_optics.K1_REAL_V1.

Measures from dscf_05.png (cleanest straight-on, bright warm hotspot on BOTTOM
edge blooming UP, magenta secondary on TOP edge blooming DOWN, on black):
  1. bottom-edge vertical luma ENVELOPE (smooth decay), normalized to edge peak,
     vs % depth into the plate -> compare to MEASURED TARGET.
  2. lateral bloom width of a bright cluster (FWHM in plate-width units).
  3. edge-hotspot brightness + vertical width (where luma crosses 0.5/0.9 of peak).
  4. TONAL distribution along the bottom-edge column: does it grade
     white->orange->amber (R>=G>=B, hue shifting) or clip flat white (R==G==B~1)?

Also samples 8884_*/8882_* to assess see-through (residual luma where the plate
is unlit -> base/veiling-glow term).

Pure measurement; prints numbers. Edits nothing.
"""
import sys
from pathlib import Path
import numpy as np
from PIL import Image

CALIB = Path("/tmp/k1_real_calib")
REF = CALIB / "dscf_05.png"

# Measured target (bottom edge), depth% -> normalized luma:
TARGET = {5: 0.96, 10: 0.90, 15: 0.81, 20: 0.73, 30: 0.60, 40: 0.48, 50: 0.39}


def luma(rgb):
    # Rec.709-ish luma on linearised-ish sRGB; keep simple (perceptual proxy).
    return 0.2126 * rgb[..., 0] + 0.7152 * rgb[..., 1] + 0.0722 * rgb[..., 2]


def find_lit_band(img):
    """Find the rows spanning the lit plate (the band of non-black pixels).
    Returns (top_row, bot_row, left_col, right_col) of the bright bounding box."""
    L = luma(img.astype(np.float64) / 255.0)
    col_max = L.max(axis=0)
    row_max = L.max(axis=1)
    thr = 0.04
    cols = np.where(col_max > thr)[0]
    rows = np.where(row_max > thr)[0]
    return rows[0], rows[-1], cols[0], cols[-1]


def main():
    img = np.asarray(Image.open(REF).convert("RGB"))
    H, W, _ = img.shape
    print(f"REF {REF.name}  {W}x{H}")
    rgbf = img.astype(np.float64) / 255.0
    L = luma(rgbf)

    t, b, l, r = find_lit_band(img)
    print(f"lit band rows [{t}..{b}] cols [{l}..{r}]  band_h={b-t} band_w={r-l}")

    # --- locate the BOTTOM edge (the bright warm near-white hotspot) ---
    # The brightest horizontal row inside the band is an edge. dscf_05: warm
    # hotspot on the bottom edge. Use a robust per-row mean over the lit columns.
    row_mean = L[t:b+1, l:r+1].mean(axis=1)
    edge_offset = int(np.argmax(row_mean))
    # bottom edge could be near top of band or bottom; report both candidates.
    print(f"brightest row within band at +{edge_offset} (of {b-t}); "
          f"row_mean peak={row_mean.max():.3f}")

    # Decide orientation: the warm (R>G>B) edge is the bottom. Compare the two ends.
    top_strip = rgbf[t:t+8, l:r+1].mean(axis=(0, 1))
    bot_strip = rgbf[b-7:b+1, l:r+1].mean(axis=(0, 1))
    warm_top = top_strip[0] - top_strip[2]
    warm_bot = bot_strip[0] - bot_strip[2]
    print(f"top-end mean RGB={top_strip.round(3)} (R-B={warm_top:+.3f})  "
          f"bot-end mean RGB={bot_strip.round(3)} (R-B={warm_bot:+.3f})")
    bottom_is_low = warm_bot >= warm_top  # warmer end = bottom (the bright warm hotspot)
    print(f"=> warm BOTTOM edge at image-{'BOTTOM (high row idx)' if bottom_is_low else 'TOP (low row idx)'}")

    # --- vertical ENVELOPE from the warm bottom edge into the plate ---
    # Build a depth axis from the bottom edge inward. Use the lit columns,
    # take a robust per-row stat (90th pct over columns) to capture the smooth
    # envelope rather than dark gaps. Normalise to the edge (depth 0) peak.
    band = L[t:b+1, l:r+1]
    if bottom_is_low:
        prof = band[::-1].copy()  # index 0 = bottom edge, increasing = into plate
    else:
        prof = band.copy()
    env = np.percentile(prof, 90, axis=1)  # smooth envelope per depth row
    # smooth a touch (5-row moving avg) to suppress content spikes
    k = 5
    kern = np.ones(k) / k
    env_s = np.convolve(env, kern, mode="same")
    peak = env_s[:3].max()  # edge peak (first few rows)
    env_n = env_s / max(peak, 1e-6)
    depth_n = np.arange(len(env_n)) / (len(env_n) - 1)  # 0..1 across full band

    print("\n--- BOTTOM-EDGE VERTICAL FALLOFF (real, normalized) vs TARGET ---")
    print(f"{'depth%':>7} {'real':>6} {'target':>7} {'delta':>7}")
    for pct, tgt in TARGET.items():
        # depth% is fraction of FULL plate height (target was depth into plate).
        di = int(round(pct / 100.0 * (len(env_n) - 1)))
        di = min(di, len(env_n) - 1)
        real = env_n[di]
        print(f"{pct:>6}% {real:>6.3f} {tgt:>7.3f} {real-tgt:>+7.3f}")

    # halfway value (target ~0.39)
    half = env_n[len(env_n)//2 if False else int(0.5*(len(env_n)-1))]
    print(f"real @50% depth = {half:.3f} (target 0.39)")

    # --- lateral bloom width: take the row at ~10% depth, find FWHM of brightest cluster ---
    row10 = prof[int(0.10*(len(prof)-1))]
    pk = row10.max()
    above = np.where(row10 >= 0.5*pk)[0]
    if len(above):
        fwhm = (above[-1]-above[0]+1) / len(row10)
        print(f"\nlateral FWHM @10% depth = {fwhm*100:.1f}% of plate width "
              f"(cluster cols {above[0]}..{above[-1]} of {len(row10)})")

    # --- edge hotspot vertical width: where envelope crosses 0.9 and 0.5 of peak ---
    def crossing(frac):
        idx = np.where(env_n < frac)[0]
        return (idx[0] / (len(env_n)-1) * 100) if len(idx) else 100.0
    print(f"\nhotspot vertical extent: 0.90 at {crossing(0.90):.1f}% depth, "
          f"0.50 at {crossing(0.50):.1f}% depth")

    # --- TONAL distribution along the bottom-edge inward column (center column) ---
    cc = (l + r)//2
    col = rgbf[t:b+1, cc-3:cc+4].mean(axis=1)  # (band_h,3)
    if bottom_is_low:
        col = col[::-1]
    print("\n--- TONAL trace from bottom edge inward (center col) ---")
    print(f"{'depth%':>7} {'R':>5} {'G':>5} {'B':>5}  note")
    for pct in [0, 5, 10, 20, 30, 50]:
        di = min(int(round(pct/100.0*(len(col)-1))), len(col)-1)
        rr_, gg, bb = col[di]
        if rr_ > 0.95 and gg > 0.95 and bb > 0.95:
            note = "CLIPPED WHITE"
        elif rr_ >= gg >= bb and (rr_-bb) > 0.06:
            note = "warm (R>G>B)"
        else:
            note = ""
        print(f"{pct:>6}% {rr_:>5.2f} {gg:>5.2f} {bb:>5.2f}  {note}")
    # fraction of bottom-edge pixels that are clipped white (all chans >0.96)
    edge_px = rgbf[(b-3 if bottom_is_low else t):(b+1 if bottom_is_low else t+4),
                   l:r+1].reshape(-1, 3)
    clip_frac = np.mean(np.all(edge_px > 0.96, axis=1))
    print(f"edge clipped-white fraction = {clip_frac*100:.1f}%")

    # --- see-through assessment from busy-scene frames ---
    print("\n--- SEE-THROUGH / VEILING assessment ---")
    for name in ["8884_03.png", "8882_03.png"]:
        p = CALIB / name
        if not p.exists():
            continue
        im2 = np.asarray(Image.open(p).convert("RGB")).astype(np.float64)/255.0
        L2 = luma(im2)
        # median luma of the darkest 30% of pixels = residual floor (plate not pure black)
        floor = np.percentile(L2, 30)
        med = np.median(L2)
        print(f"{name}: dark-floor(p30)={floor:.3f}  median={med:.3f}  "
              f"(>0 floor on unlit regions => plate is see-through / not pure black)")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
