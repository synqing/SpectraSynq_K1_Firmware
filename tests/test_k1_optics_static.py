"""Static host tests for scripts/regression-harness/k1_optics.py.

Pure NumPy — no g++, no device, fast (<5s). Validates the K1Optics_v1
PHYSICAL-preset port: shape/range contract, black-in→black-out, single-LED
localised glow attenuating away from its injection edge, dual-edge mixing,
and the optional palette_coverage_gate --plate hook.

Orientation contract under test (PORT-NOTES 9 in k1_optics.py): output row 0
is the TOP edge (secondary strip), row H-1 the BOTTOM edge (primary strip).
"""
import pathlib
import sys

import numpy as np
import pytest

HARNESS = pathlib.Path(__file__).resolve().parents[1] / "scripts" / "regression-harness"
sys.path.insert(0, str(HARNESS))
import k1_optics  # noqa: E402

N_LEDS = 128
W, H = 160, 60


def _black(n=N_LEDS):
    return np.zeros((n, 3), dtype=np.float64)


def _single(idx, colour, n=N_LEDS):
    s = _black(n)
    s[idx] = colour
    return s


def _brightness(img):
    """Per-pixel max-channel brightness."""
    return img.max(axis=2)


# ---- shape / range contract -------------------------------------------------

def test_output_shape_dtype_and_range():
    rng = np.random.default_rng(42)
    primary = rng.random((N_LEDS, 3))
    secondary = rng.random((N_LEDS, 3))
    img = k1_optics.render_plate(primary, secondary, width=W, height=H)
    assert img.shape == (H, W, 3)
    assert img.dtype == np.float64
    assert np.all(np.isfinite(img))
    assert img.min() >= 0.0 and img.max() <= 1.0


def test_full_white_input_clamps_to_unit_range():
    ones = np.ones((N_LEDS, 3))
    img = k1_optics.render_plate(ones, ones, width=W, height=H)
    # exposure 4.0 would push raw values >1; the port must clamp (PORT-NOTES 3)
    assert img.max() <= 1.0
    assert img.max() == pytest.approx(1.0)


def test_custom_dimensions():
    img = k1_optics.render_plate(_single(10, (1, 0, 0)), width=32, height=12)
    assert img.shape == (12, 32, 3)


def test_bad_inputs_raise():
    with pytest.raises(ValueError):
        k1_optics.render_plate(np.zeros((N_LEDS, 4)))
    with pytest.raises(ValueError):
        k1_optics.render_plate(_black(), _black(64))  # length mismatch
    with pytest.raises(ValueError):
        k1_optics.render_plate(_black(), width=0)


# ---- black in -> black out ---------------------------------------------------

def test_black_in_black_out():
    img = k1_optics.render_plate(_black(), _black(), width=W, height=H)
    assert np.all(img == 0.0)
    img1 = k1_optics.render_plate(_black(), None, width=W, height=H)
    assert np.all(img1 == 0.0)


# ---- single lit LED: localised glow, attenuating from its edge ---------------

def test_single_primary_led_glow_is_localised_and_attenuates():
    led = 30
    img = k1_optics.render_plate(_single(led, (1.0, 0.0, 0.0)),
                                 width=W, height=H)
    bright = _brightness(img)
    # Column under the LED (uv.x of LED centre -> plate column).
    col = int((led + 0.5) / N_LEDS * W)
    far_col = int(0.9 * W)

    # Localised: glow column massively brighter than a far column.
    assert bright[:, col].max() > 0.5
    assert bright[:, far_col].max() < 1e-6

    # Attenuates with distance from the BOTTOM edge (primary injects bottom;
    # bottom = last rows, PORT-NOTES 9). Compare horizontal-band means.
    column = bright[:, col]
    top_band = column[: H // 3].mean()
    mid_band = column[H // 3: 2 * H // 3].mean()
    bottom_band = column[2 * H // 3:].mean()
    assert bottom_band > mid_band > top_band
    assert top_band < 0.05 * bottom_band

    # Red LED stays red away from the edge: the hotspot term is WHITE
    # (vec3(1.0) * totalHotspot, edgeLitShader.ts:77), so green/blue may
    # only appear inside the bottom hotspot band (y < 0.02 -> last rows).
    hotspot_rows = int(np.ceil(0.02 * H)) + 1
    assert img[:-hotspot_rows, :, 1].max() < 1e-9
    assert img[:-hotspot_rows, :, 2].max() < 1e-9
    assert img[-1, col, 1] > 0.0   # white hotspot present at the edge


def test_single_secondary_led_glows_from_top_edge():
    led = 100
    img = k1_optics.render_plate(_black(),
                                 _single(led, (0.0, 0.0, 1.0)),
                                 width=W, height=H)
    bright = _brightness(img)
    col = int((led + 0.5) / N_LEDS * W)
    column = bright[:, col]
    top_band = column[: H // 3].mean()
    bottom_band = column[2 * H // 3:].mean()
    assert top_band > bottom_band  # secondary injects the TOP edge
    assert column.max() > 0.5


def test_lateral_spread_widens_away_from_injection_edge():
    """PHYSICAL spread grows with distance from the strip
    (edgeLitShader.ts:57): glow row near the far edge is wider than near."""
    led = 64
    img = k1_optics.render_plate(_single(led, (1.0, 1.0, 1.0)),
                                 width=W, height=H,
                                 exposure=1.0, hotspot_gain=0.0)
    bright = _brightness(img)

    def lit_width(row):
        r = bright[row]
        return int((r > 0.02 * r.max()).sum()) if r.max() > 0 else 0

    near_bottom = lit_width(H - 2)   # close to primary edge
    mid = lit_width(H // 2)
    assert mid >= near_bottom


# ---- dual-edge mixing ---------------------------------------------------------

def test_dual_edge_inputs_mix():
    red = np.tile([0.2, 0.0, 0.0], (N_LEDS, 1))
    blue = np.tile([0.0, 0.0, 0.2], (N_LEDS, 1))
    img = k1_optics.render_plate(red, blue, width=W, height=H)

    top_rows = img[: H // 4]          # near secondary (blue) edge
    bottom_rows = img[3 * H // 4:]    # near primary (red) edge
    mid_rows = img[H // 2 - 2: H // 2 + 2]

    assert bottom_rows[:, :, 0].mean() > bottom_rows[:, :, 2].mean()
    assert top_rows[:, :, 2].mean() > top_rows[:, :, 0].mean()
    # Mid-plate carries BOTH contributions (the mix, edgeLitShader.ts:66).
    assert mid_rows[:, :, 0].mean() > 0.0
    assert mid_rows[:, :, 2].mean() > 0.0

    # Superposition: dual-edge render == primary-only + secondary-only
    # (PHYSICAL branch is linear pre-clamp; keep values below clamp).
    a = k1_optics.render_plate(red, None, width=W, height=H)
    b = k1_optics.render_plate(_black(), blue, width=W, height=H)
    np.testing.assert_allclose(img, np.clip(a + b, 0.0, 1.0), atol=1e-12)


# ---- preset provenance guard ---------------------------------------------------

def test_physical_preset_constants():
    # presets.ts:33-46 + K1CoreScene.tsx:126-127 — drift here means the port
    # no longer renders K1_PHYSICAL_V1.
    assert k1_optics.PHYSICAL_EXPOSURE == 4.0
    assert k1_optics.PHYSICAL_BASE_LEVEL == 0.0
    assert k1_optics.PHYSICAL_TINT == (1.0, 1.0, 1.0)
    assert k1_optics.PHYSICAL_SPREAD_NEAR == 0.015
    assert k1_optics.PHYSICAL_FALLOFF == 1.5
    assert k1_optics.PHYSICAL_HOTSPOT_GAIN == 4.0
    assert k1_optics.PHYSICAL_GRAIN_STRENGTH == 0.0
    assert k1_optics.K1_OPTICS_VERSION == "K1Optics_v1"


# ---- palette_coverage_gate --plate hook ----------------------------------------

def test_palette_gate_plate_hook_renders_plate_pixels():
    import palette_coverage_gate as pg
    frame = [(0, 0, 0)] * N_LEDS
    frame[30] = (255, 0, 0)
    hexes = [bytes(c for px in frame for c in px).hex()]
    plate_hexes = pg._plate_hexes(hexes, width=W, height=H)
    assert len(plate_hexes) == 1
    raw = bytes.fromhex(plate_hexes[0])
    assert len(raw) == W * H * 3        # plate pixels, not raw LEDs
    assert max(raw) > 0                  # lit LED produced plate emission
    # Existing metric functions run unchanged on the plate pixels.
    m = pg.compute_colour_metrics(plate_hexes)
    assert m["led_count"] == W * H
    assert 0.0 < m["lit_fraction"] < 1.0
