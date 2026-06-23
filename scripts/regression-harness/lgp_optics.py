"""lgp_optics.py — faithful NumPy port of the DEPLOYED, CALIBRATED K1 edge-lit
LGP optics shader (`K1Optics_v1`, PHYSICAL mode).

WHAT THIS IS
  A pure-NumPy, deterministic reproduction of the fragment shader that ships in
  the K1 landing-page renderer. Given the two 160-LED RGB strips that drive the
  bottom and top edges of the light guide plate, it produces the plate image the
  shader would render — i.e. what the calibrated optical model says the LGP looks
  like. Matching this port to the shader (Deliverable 2) means matching the
  DEPLOYED CALIBRATED LGP MODEL. Matching the REAL physical plate is a later step
  that needs Captain's on-device captures.

SOURCE OF TRUTH (archived, read-only — ported LINE-FOR-LINE, not paraphrased):
  edgeLitShader.ts   app/k1/core/optics/edgeLitShader.ts   (fragment, PHYSICAL branch)
  common.ts          app/engine/shaders/common.ts          (sampleStrip + gaussian)
  presets.ts         app/k1/core/optics/presets.ts         (K1_PHYSICAL_V1 constants)
  K1CoreScene.tsx    app/k1/core/view/K1CoreScene.tsx       (deploy-time uniforms)
  (all under SpectraSynq.LandingPage/apps/web-main/)

THE OPTICAL MODEL (PHYSICAL mode, edgeLitShader.ts:55-81)
  Per output pixel (vUv.x in [0,1] across the strip, vUv.y in [0,1] bottom->top):
    1. Lateral Gaussian spread along the strip whose sigma WIDENS with depth into
       the plate (deeper from an edge => more scattering):
         bottomSpread = bottomSpreadNear * (0.5 + vUv.y       * 6.0)   (:57)
         topSpread    = topSpreadNear    * (0.5 + (1.0-vUv.y) * 6.0)   (:58)
    2. Vertical influence composite:
         bottomInfluence = (1-y)^bottomFalloff,  topInfluence = y^topFalloff (:60-61)
         finalColor = colorBottom*bottomInfluence + colorTop*topInfluence     (:66)
    3. Edge hotspots, baseLevel, exposure, tint, clamp (:69-80).
  The TOP strip is mounted mirror-reversed (index-reversed) relative to the
  bottom; this port reverses `top_rgb` internally before sampling so the caller
  passes both strips in render-index order.

DETERMINISM
  Grain ships OFF (uGrainStrength = 0.0, K1CoreScene.tsx:126). With grain zero the
  PHYSICAL path is a pure function of (bottom_rgb, top_rgb) -> output. We hold
  grain at 0.0 so the port is bit-deterministic. (HERO stylization is zeroed and
  not ported — see DELIBERATELY-OMITTED below.)

GAMMA / TONE CURVE
  NONE inside the PHYSICAL fragment. The shader writes gl_FragColor = linear
  colour, clamped to [0,1] by the framebuffer on write (PHYSICAL branch has no
  ACES / sRGB / pow tone curve — contrast the standalone preview which uses
  ACESFilmicToneMapping at the renderer, NOT in this shader). This port therefore
  reproduces the shader's pre-encoding linear output, clamps to [0,1], and
  quantises to 8-bit (×255, round). If a display gamma is wanted it must be added
  by the caller; it is NOT baked in here (matching the shader exactly).
"""

from __future__ import annotations

import numpy as np

# ============================================================================
# OPTICS PRESETS — a preset is a dict of optical knobs passed to plate_image().
# K1_PHYSICAL reproduces the deployed shader BIT-EXACTLY (1/255 validation gate).
# K1_REAL_V1 is CALIBRATED TO THE REAL PLATE from hardware captures (E4, 2026-06-04)
# and DIVERGES from the shader BY DESIGN — reality is the target now, the shader
# was the interim reference. Default plate_image() optics = K1_PHYSICAL, so every
# existing caller and the 1/255 K1_PHYSICAL validation are unchanged.
#
# New knob: `tonemap` selects the bright-region roll-off:
#   "clip"     — hard clamp to [0,1] on framebuffer write (the SHADER's behaviour).
#   "reinhard" — extended Reinhard soft roll-off c/(1+c) scaled by `white` so bright
#                regions stay GRADED (warm white->orange->amber) instead of clipping
#                flat to (1,1,1). Per-channel => preserves the measured warm grade.
#
# MEASURED (E4) from /tmp/k1_real_calib/dscf_05.png (cleanest straight-on ref):
#   * Bottom-edge vertical falloff best-fit exponent (10-50% depth) = 1.461; the
#     measured-target table {5:.96 10:.90 15:.81 20:.73 30:.60 40:.48 50:.39} is
#     reproduced within +/-0.04 by (1-depth)^1.45. => REAL_V1 falloff = 1.45.
#   * Edge clipped-white fraction = 0.0%. The real edge is GRADED WARM, never flat
#     white: center-column RGB grades (0.82,0.50,0.34)->(0.41,0.24,0.16) edge->mid.
#     A hard clamp at exposure 4.0 destroys this. => REAL_V1 uses Reinhard roll-off.
#   * Lateral FWHM @10% depth = ~94% of plate width: the plate diffuses widely.
#     => REAL_V1 spreadNear raised 0.015 -> 0.026 (wider lateral bloom).
#   * See-through floor on busy-scene crops (8884/8882) ~0.001-0.013 -> essentially
#     black on these captures; transparency is environment-dependent (model boundary).
#     A tiny baseLevel (0.012) keeps unlit plate from reading as pure void without
#     faking content behind it.
# ============================================================================

K1_PHYSICAL = {
    "bottom_spread_near": 0.015,   # presets.ts:42
    "top_spread_near":    0.015,   # presets.ts:41
    "bottom_falloff":     1.5,     # presets.ts:46
    "top_falloff":        1.5,     # presets.ts:45
    "exposure":           4.0,     # presets.ts:33
    "base_level":         0.0,     # presets.ts:34
    "tint":               (1.0, 1.0, 1.0),  # presets.ts:35
    "hotspot_gain":       4.0,     # K1CoreScene.tsx:127
    "tonemap":            "clip",  # SHADER: hard clamp on framebuffer write
    "white":              1.0,     # (unused for clip; reinhard white point)
}

K1_REAL_V1 = {
    # --- lateral spread: real FWHM ~94% => widen near-edge sigma (0.015 -> 0.026) ---
    "bottom_spread_near": 0.026,
    "top_spread_near":    0.026,
    # --- vertical falloff: measured best-fit 1.461; 1.45 reproduces target table ---
    "bottom_falloff":     1.45,
    "top_falloff":        1.45,
    # --- exposure: keep drive high so the edge reaches near-white, BUT roll off ---
    #     softly instead of clamping. Slightly under shader 4.0 so the Reinhard
    #     knee sits where the real edge sits (graded, ~0% hard-clip).
    "exposure":           2.8,
    # --- base level: tiny floor so unlit plate isn't pure void (real plate glows
    #     faintly / is see-through); environment-dependent, kept subtle.
    "base_level":         0.012,
    "tint":               (1.0, 0.97, 0.93),  # faint warm plate body tint (acrylic)
    # --- hotspot: real edge is bright but NOT a blown white spike; reduce gain so
    #     the warm grade survives into the hotspot (4.0 -> 2.0). ---
    "hotspot_gain":       2.0,
    # --- soft tone roll-off: the load-bearing change. Per-channel extended
    #     Reinhard keeps bright regions graded warm (R>G>B) instead of flat white. ---
    "tonemap":            "reinhard",
    "white":              2.4,     # Reinhard white point: maps ~2.4 linear -> 1.0
}

# ============================================================================
# CALIBRATION CONSTANTS — K1_PHYSICAL_V1 (presets.ts) + deploy uniforms (K1CoreScene.tsx)
# Each constant is annotated with its exact source line.
# ============================================================================

# --- Lateral spread (sigma base), presets.ts:42 (bottomSpreadNear / topSpreadNear) ---
BOTTOM_SPREAD_NEAR = 0.015   # presets.ts:42  optics.bottomSpreadNear
TOP_SPREAD_NEAR    = 0.015   # presets.ts:41  optics.topSpreadNear
# NOTE: PHYSICAL mode (edgeLitShader.ts:57-58) ignores *SpreadFar entirely; the
# depth term uses *SpreadNear * (0.5 + depth*6.0). spreadFar is a HERO-only knob.

# --- Vertical falloff, presets.ts:45-46 ---
BOTTOM_FALLOFF = 1.5   # presets.ts:46  optics.bottomFalloff
TOP_FALLOFF    = 1.5   # presets.ts:45  optics.topFalloff

# --- Global visuals, presets.ts:33-36 ---
EXPOSURE   = 4.0   # presets.ts:33  visuals.exposure
BASE_LEVEL = 0.0   # presets.ts:34  visuals.baseLevel
TINT       = (1.0, 1.0, 1.0)  # presets.ts:35  visuals.tint '#ffffff' -> (1,1,1) identity

# --- Deploy-time toggles, K1CoreScene.tsx:126-127 (NOT in presets; set by the scene) ---
GRAIN_STRENGTH = 0.0   # K1CoreScene.tsx:126  uGrainStrength -> grain OFF at deploy
HOTSPOT_GAIN   = 4.0   # K1CoreScene.tsx:127  uHotspotGain (physical default)

# --- sampleStrip kernel, common.ts:16-39 ---
SAMPLES   = 7          # common.ts:21  `float samples = 7.0;` -> taps i in [-7..7] = 15 taps
WEIGHT_EPS = 1e-5      # common.ts:37  `max(totalWeight, 1e-5)` denominator floor

# --- Strip resolution: uResolution = ledCount, K1CoreScene.tsx:101 (K1 = 160 LEDs) ---
LED_COUNT = 160

# Default output canvas = the VALIDATED K1 LGP FACE aspect (delegation E3, 2026-06-04):
# ~329 mm long (the LED axis — both long edges are LED-lit) x ~60 mm visible width
# (the light-travel / diffusion axis) = ~5.48:1. Authority: CAD STEP LED strip
# 328.66 mm centre-origin + "32 cm / 320 WS2812B" spec. The shader is
# resolution-agnostic in vUv (diffusion sigma is normalized), so H/W only set raster
# fineness; the ASPECT is what must resemble the physical plate.
LGP_LENGTH_MM = 329.0
LGP_WIDTH_MM = 60.0
DEFAULT_W = 548                                                # LED (long ~329mm) axis
DEFAULT_H = round(DEFAULT_W * LGP_WIDTH_MM / LGP_LENGTH_MM)    # ~100 -> 5.48:1

# ----------------------------------------------------------------------------
# DELIBERATELY OMITTED (zeroed in PHYSICAL / not on the deployed path):
#   columnBoost* (presets.ts:48-49 = 0), edgeHotspotStrength/Width (HERO rails),
#   railInner/Outer/Sigma, prism*, the entire HERO/EXPERIMENTAL branch
#   (edgeLitShader.ts:84-132), and `uTime` (only feeds grain, which is 0).
# ----------------------------------------------------------------------------


def _gaussian(x: np.ndarray, sigma: float) -> np.ndarray:
    """common.ts:11-13  exp(-(x*x)/(2*sigma*sigma)). sigma assumed > 0 (it is:
    spreadNear*0.5 = 0.0075 minimum)."""
    return np.exp(-(x * x) / (2.0 * sigma * sigma))


def _sample_strip(strip_rgb: np.ndarray, uv_x: np.ndarray, spread: np.ndarray,
                  resolution: int) -> np.ndarray:
    """Port of common.ts sampleStrip (:16-38), vectorised over a row of pixels.

      strip_rgb : (N, 3) LED colours in [0,1], already in the orientation the
                  shader samples (caller reverses TOP before passing).
      uv_x      : (W,) horizontal UV of each output pixel in [0,1].
      spread    : (W,) per-pixel sigma base (== currentSigma in the GLSL; depth
                  already folded in by the caller — matches GLSL where spreadBase
                  is passed in and currentSigma = spreadBase).
      resolution: uResolution (LED count); pixelWidth = 1/resolution.

    Returns (W, 3) accumulated colour, weight-normalised exactly like the GLSL:
      for i in [-7..7]: offset = i*pixelWidth; w = gaussian(offset, sigma);
                        sampleUv.x = clamp(uv.x + offset, 0, 1);
                        acc += texture2D(strip, (sampleUv.x, 0.5)).rgb * w; tw += w
      return acc / max(tw, 1e-5)

    texture2D with NearestFilter (DataTexture min/magFilter = Nearest, see the
    landing renderer's strip textures) maps a continuous u in [0,1] to LED index
    floor(u * resolution), clamped to [0, resolution-1]. We replicate nearest
    sampling exactly.
    """
    W = uv_x.shape[0]
    pixel_width = 1.0 / resolution
    acc = np.zeros((W, 3), dtype=np.float64)
    total_w = np.zeros((W, 1), dtype=np.float64)

    for i in range(-SAMPLES, SAMPLES + 1):
        offset = i * pixel_width
        # gaussian(offset, sigma) — offset is scalar, sigma is per-pixel (W,)
        w = _gaussian(np.full(W, offset), spread)          # (W,)
        sample_u = np.clip(uv_x + offset, 0.0, 1.0)         # (W,)  GLSL clamp
        # NearestFilter index: floor(u * resolution), clamped to last LED.
        idx = np.minimum((sample_u * resolution).astype(np.int64), resolution - 1)
        idx = np.maximum(idx, 0)
        acc += strip_rgb[idx] * w[:, None]
        total_w += w[:, None]

    return acc / np.maximum(total_w, WEIGHT_EPS)


def plate_image(bottom_rgb, top_rgb, height: int = DEFAULT_H, width: int = DEFAULT_W,
                resolution: int = LED_COUNT, optics=None) -> np.ndarray:
    """Render the K1 edge-lit LGP for one frame.

    Parameters
    ----------
    bottom_rgb : (resolution, 3) float in [0,1]  — bottom-edge strip, render-index order.
    top_rgb    : (resolution, 3) float in [0,1]  — top-edge strip, render-index order.
                 Reversed INTERNALLY (mirror-mounted top edge). Single-channel
                 callers pass np.zeros((resolution, 3)) for the unused edge.
    height, width : output image dimensions (pixels). Default ~5.48:1 plate face.
    resolution : uResolution / LED count (default 160).
    optics     : optional optics-preset dict (see K1_PHYSICAL / K1_REAL_V1).
                 None => K1_PHYSICAL, i.e. the BIT-EXACT deployed shader (the
                 1/255 validation against the shader holds for this default).
                 Pass K1_REAL_V1 for the real-plate-calibrated render.

    Returns
    -------
    np.ndarray, shape (height, width, 3), dtype uint8 — the plate image, with
    row 0 = TOP of the plate (vUv.y = 1) and row height-1 = BOTTOM (vUv.y = 0),
    i.e. conventional image orientation (y increases downward => y_uv decreases).

    Deterministic given the inputs (grain is held at 0.0).
    """
    o = K1_PHYSICAL if optics is None else optics
    b_spread = o["bottom_spread_near"]; t_spread_n = o["top_spread_near"]
    b_falloff = o["bottom_falloff"];    t_falloff = o["top_falloff"]
    exposure = o["exposure"];           base_level = o["base_level"]
    hotspot_gain = o["hotspot_gain"];   tonemap = o.get("tonemap", "clip")
    white = o.get("white", 1.0)
    tint = np.asarray(o["tint"], dtype=np.float64)

    bottom_rgb = np.asarray(bottom_rgb, dtype=np.float64).reshape(resolution, 3)
    top_rgb = np.asarray(top_rgb, dtype=np.float64).reshape(resolution, 3)

    # TOP edge is mirror-mounted -> index-reversed before sampling (task spec;
    # the deployed renderer uploads the top strip reversed so its physical left
    # matches the bottom strip's left). Reverse here so callers pass render order.
    top_sampled = top_rgb[::-1]

    # vUv.x for each output column: pixel-centre sampling across [0,1].
    uv_x = (np.arange(width, dtype=np.float64) + 0.5) / width          # (W,)

    # vUv.y for each output row. Image row 0 = top of plate (y_uv = 1), so y_uv
    # decreases as the row index increases. Pixel-centre sampling.
    y_uv = 1.0 - (np.arange(height, dtype=np.float64) + 0.5) / height  # (H,)

    out = np.zeros((height, width, 3), dtype=np.float64)

    for r in range(height):
        y = y_uv[r]

        # --- PHYSICAL spread (edgeLitShader.ts:57-58): sigma widens with depth ---
        bottom_spread = b_spread * (0.5 + y * 6.0)                     # scalar
        top_spread = t_spread_n * (0.5 + (1.0 - y) * 6.0)             # scalar
        bottom_spread_row = np.full(width, bottom_spread)
        top_spread_row = np.full(width, top_spread)

        # --- vertical influence (edgeLitShader.ts:60-61) ---
        bottom_influence = (1.0 - y) ** b_falloff
        top_influence = y ** t_falloff

        # --- sample both strips (edgeLitShader.ts:63-64) ---
        color_bottom = _sample_strip(bottom_rgb, uv_x, bottom_spread_row, resolution)
        color_top = _sample_strip(top_sampled, uv_x, top_spread_row, resolution)

        # --- composite (edgeLitShader.ts:66) ---
        final_color = color_bottom * bottom_influence + color_top * top_influence

        # --- edge hotspots (edgeLitShader.ts:69-71) ---
        bottom_hotspot = _smoothstep(0.02, 0.0, y)                      # scalar
        top_hotspot = _smoothstep(0.98, 1.0, y)                        # scalar
        len_bottom = np.linalg.norm(color_bottom, axis=1)              # (W,)
        len_top = np.linalg.norm(color_top, axis=1)                    # (W,)
        total_hotspot = bottom_hotspot * len_bottom + top_hotspot * len_top  # (W,)

        # --- grain (edgeLitShader.ts:74) — GRAIN_STRENGTH = 0 at deploy => 0 ---
        grain = 0.0

        # --- tonemap/output (edgeLitShader.ts:75-78) ---
        out_color = final_color + base_level                            # +baseLevel
        out_color = out_color + grain                                   # + vec3(grain)
        out_color = out_color * exposure + (total_hotspot[:, None] * hotspot_gain)
        out_color = out_color * tint                                    # *= uTint

        out[r] = out_color

    # --- bright-region roll-off ---
    if tonemap == "reinhard":
        # Extended per-channel Reinhard: c*(1 + c/white^2) / (1 + c). Maps a finite
        # linear `white` to 1.0, monotone, and PRESERVES channel ratios in the knee
        # so a warm (R>G>B) edge stays graded warm instead of clamping flat to white.
        c = np.maximum(out, 0.0)
        out = c * (1.0 + c / (white * white)) / (1.0 + c)
    out = np.clip(out, 0.0, 1.0)
    return np.round(out * 255.0).astype(np.uint8)


def _smoothstep(edge0: float, edge1: float, x: float) -> float:
    """GLSL smoothstep (works for edge0 > edge1, as the hotspot calls use)."""
    if edge0 == edge1:
        return 0.0 if x < edge0 else 1.0
    t = (x - edge0) / (edge1 - edge0)
    t = min(max(t, 0.0), 1.0)
    return t * t * (3.0 - 2.0 * t)


# ----------------------------------------------------------------------------
# Continuous single-pixel evaluator — used by the analytic validation to compare
# the port against closed-form shader values at exact (vUv.x, vUv.y) points,
# independent of the raster grid.
# ----------------------------------------------------------------------------
def eval_fragment(bottom_rgb, top_rgb, uv_x: float, uv_y: float,
                  resolution: int = LED_COUNT) -> np.ndarray:
    """Evaluate the PHYSICAL fragment at one (uv_x, uv_y), returning the linear
    (pre-clamp) RGB the shader computes. Mirrors plate_image's per-pixel math but
    for a single continuous point (no raster centring)."""
    bottom_rgb = np.asarray(bottom_rgb, dtype=np.float64).reshape(resolution, 3)
    top_rgb = np.asarray(top_rgb, dtype=np.float64).reshape(resolution, 3)
    top_sampled = top_rgb[::-1]

    y = uv_y
    bottom_spread = BOTTOM_SPREAD_NEAR * (0.5 + y * 6.0)
    top_spread = TOP_SPREAD_NEAR * (0.5 + (1.0 - y) * 6.0)
    cb = _sample_strip(bottom_rgb, np.array([uv_x]), np.array([bottom_spread]), resolution)[0]
    ct = _sample_strip(top_sampled, np.array([uv_x]), np.array([top_spread]), resolution)[0]

    bottom_influence = (1.0 - y) ** BOTTOM_FALLOFF
    top_influence = y ** TOP_FALLOFF
    final_color = cb * bottom_influence + ct * top_influence

    bottom_hotspot = _smoothstep(0.02, 0.0, y)
    top_hotspot = _smoothstep(0.98, 1.0, y)
    total_hotspot = bottom_hotspot * np.linalg.norm(cb) + top_hotspot * np.linalg.norm(ct)

    out_color = (final_color + BASE_LEVEL) * EXPOSURE + total_hotspot * HOTSPOT_GAIN
    out_color = out_color * np.asarray(TINT, dtype=np.float64)
    return out_color
