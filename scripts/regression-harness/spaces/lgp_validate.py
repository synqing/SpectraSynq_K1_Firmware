"""lgp_validate.py — compare lgp_optics.plate_image() against the headless WebGL
reference render of the VERBATIM deployed GLSL (lgp_shader_ref_out.json).

PATH: PREFERRED (real-GLSL headless WebGL). lgp_validate.mjs ran the shipping
vertex+fragment shader under Chromium/ANGLE/SwiftShader and read back canvas
pixels. This script renders the SAME static LED cases through the NumPy port and
reports per-case + overall max/mean absolute 8-bit pixel error.

The cases here MUST match buildCases() in lgp_validate.mjs exactly.
"""
import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))  # so `import lgp_optics` works
import lgp_optics as lo  # noqa: E402

RES = lo.LED_COUNT


def zeros():
    return np.zeros((RES, 3), dtype=np.float64)


def build_cases():
    """Mirror of lgp_validate.mjs buildCases() — identical inputs, same names/order."""
    cases = {}

    b = zeros(); b[80] = [1, 1, 1]
    cases['impulse_bottom_led80_white'] = (b.copy(), zeros())

    t = zeros(); t[40] = [1, 0, 0]
    cases['impulse_top_led40_red'] = (zeros(), t.copy())

    b = np.ones((RES, 3), dtype=np.float64)
    cases['allon_bottom_white'] = (b.copy(), zeros())

    b = zeros(); t = zeros()
    b[20] = [1, 0, 0]; b[100] = [0, 0.7, 0]
    t[60] = [0, 0, 1]; t[120] = [0.5, 0.5, 0]
    cases['dual_distinct_leds'] = (b.copy(), t.copy())

    b = zeros()
    ramp = np.linspace(0.0, 1.0, RES)
    b[:, 0] = ramp; b[:, 1] = ramp; b[:, 2] = ramp
    cases['ramp_bottom_gray'] = (b.copy(), zeros())

    return cases


def webgl_pixels_to_image(flat_rgba, W, H):
    """gl.readPixels gives a flat RGBA Uint8 array, origin BOTTOM-LEFT (row 0 =
    bottom of plate). Convert to (H, W, 3) with row 0 = TOP of plate to match
    plate_image()'s orientation."""
    arr = np.asarray(flat_rgba, dtype=np.uint8).reshape(H, W, 4)[:, :, :3]
    return arr[::-1]  # flip vertically: bottom-left origin -> top-row-0


def main():
    ref_path = HERE / 'lgp_shader_ref_out.json'
    ref = json.loads(ref_path.read_text())
    W, H = ref['width'], ref['height']
    print(f"reference: {ref_path.name}  W={W} H={H}")
    print(f"GL: {ref['glInfo'].get('renderer', '?')}")
    print()

    cases = build_cases()
    ref_by_name = {r['name']: r for r in ref['results']}

    overall_max = 0
    overall_sum = 0.0
    overall_n = 0
    rows = []
    for name, (bottom, top) in cases.items():
        port = lo.plate_image(bottom, top, height=H, width=W)  # (H,W,3) uint8
        shader = webgl_pixels_to_image(ref_by_name[name]['pixels'], W, H)

        diff = np.abs(port.astype(np.int32) - shader.astype(np.int32))
        mx = int(diff.max())
        mean = float(diff.mean())
        # 99.9th percentile to characterise the tail beyond raster/AA edge pixels
        p999 = float(np.percentile(diff, 99.9))
        overall_max = max(overall_max, mx)
        overall_sum += float(diff.sum())
        overall_n += diff.size
        rows.append((name, mx, mean, p999))

    print(f"{'case':32s} {'max':>5s} {'mean':>8s} {'p99.9':>7s}")
    print("-" * 56)
    for name, mx, mean, p999 in rows:
        print(f"{name:32s} {mx:5d} {mean:8.4f} {p999:7.2f}")
    print("-" * 56)
    print(f"{'OVERALL':32s} {overall_max:5d} {overall_sum / overall_n:8.4f}")
    print()
    print(f"OVERALL max abs pixel error  : {overall_max} / 255")
    print(f"OVERALL mean abs pixel error : {overall_sum / overall_n:.4f} / 255")

    # PASS criterion: max <= 2 LSB (8-bit rounding + SwiftShader fp + raster
    # centring differences). Tight enough to prove a faithful port.
    ok = overall_max <= 2
    print()
    print("VALIDATION:", "PASS" if ok else "FAIL", f"(max <= 2 LSB tolerance; got {overall_max})")
    return 0 if ok else 1


if __name__ == '__main__':
    raise SystemExit(main())
