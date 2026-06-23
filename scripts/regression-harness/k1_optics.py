#!/usr/bin/env python3
"""K1Optics_v1 PHYSICAL-preset plate renderer — NumPy port (host tooling).

K1 is a dual-channel edge-lit light-guide plate (LGP): the PRIMARY LED strip
injects light into the BOTTOM edge, the SECONDARY strip into the TOP edge,
and the eye sees diffused PLATE emission — never the raw strip pixels. Host
tooling that judges raw LED buffers therefore judges the wrong surface. This
module renders the diffused plate so host metrics can run on what the eye
actually sees.

SOURCE OF TRUTH (read-only archive — historical evidence, never edited):
  shader   : .../SpectraSynq.LandingPage.archived_2026-05-14/apps/web-main/
             app/k1/core/optics/edgeLitShader.ts   (K1_OPTICS_VERSION =
             'K1Optics_v1'; PHYSICAL branch = lines 55-82)
  partials : .../apps/web-main/app/engine/shaders/common.ts
             (gaussian lines 10-14, sampleStrip lines 16-38)
  preset   : .../apps/web-main/app/k1/core/optics/presets.ts
             (K1_PHYSICAL_V1, lines 30-68)
  uniforms : .../apps/web-main/app/k1/core/view/K1CoreScene.tsx
             (uResolution = ledCount line 101; uGrainStrength default 0.0
             line 126; uHotspotGain default 4.0 line 127; LED textures use
             THREE.NearestFilter — useK1Physics.ts lines 99-100, 108-109)

PHYSICAL MODEL (edgeLitShader.ts:55-82, faithfully ported):
  vUv.y = 0 at the BOTTOM edge, 1 at the TOP edge.
    bottomSpread    = bottomSpreadNear * (0.5 + y * 6.0)          # :57
    topSpread       = topSpreadNear    * (0.5 + (1 - y) * 6.0)    # :58
    bottomInfluence = (1 - y) ** bottomFalloff                    # :60
    topInfluence    = y ** topFalloff                             # :61
    colorBottom     = sampleStrip(primary,   y-dependent sigma)   # :63
    colorTop        = sampleStrip(secondary, y-dependent sigma)   # :64
    final           = colorBottom*bottomInfluence
                      + colorTop*topInfluence                     # :66
    bottomHotspot   = smoothstep(0.02, 0.0, y)                    # :69
    topHotspot      = smoothstep(0.98, 1.0, y)                    # :70
    totalHotspot    = bottomHotspot*|colorBottom|
                      + topHotspot*|colorTop|     (euclidean rgb) # :71
    out = (final + baseLevel + grain) * exposure
          + totalHotspot * hotspotGain                            # :75-77
    out *= tint                                                   # :78

  sampleStrip (common.ts:16-38): 15-tap (i = -7..+7) gaussian blur along x;
  tap offsets are i / ledCount in UV units (pixelWidth, common.ts:21); sigma
  is the spread value in UV units; sample u is clamped to [0,1]
  (common.ts:30); result normalised by accumulated weight (common.ts:37,
  guard max(totalWeight, 1e-5)).

PHYSICAL preset constants (presets.ts:30-58 + K1CoreScene.tsx:101,126,127):
  exposure 4.0 · baseLevel 0.0 · tint #ffffff · all spreads 0.015 ·
  both falloffs 1.5 · grainStrength 0.0 · hotspotGain 4.0
  (columnBoost / edgeHotspot / rail params exist in the preset but are only
  read by the HERO/EXPERIMENTAL branch, edgeLitShader.ts:84+ — not ported.)

PORT-NOTES — defensible simplifications, all FLAGGED (no silent guesses):
  1. GRAIN OMITTED. uGrainStrength defaults to 0.0 (K1CoreScene.tsx:126) so
     the PHYSICAL preset renders grain-free; the shader's rand(vUv, uTime)
     noise is also non-deterministic per frame, which host regression tooling
     must not be. grain == 0 exactly reproduces the preset; a grain_strength
     parameter is intentionally NOT offered.
  2. uTime UNUSED. Time only feeds the grain noise; with grain 0 the PHYSICAL
     output is time-invariant, so render_plate takes no time argument.
  3. OUTPUT CLAMPED to [0,1]. The GLSL writes unclamped values to
     gl_FragColor; the 8-bit framebuffer clamps on store. We clamp explicitly
     so downstream uint8 quantisation matches what the screen showed.
  4. presets.ts:28 comment claims the PHYSICAL spread formula is
     `uSpreadNear * (0.2 + vUv.y * 3.0)`; the SHADER CODE
     (edgeLitShader.ts:57-58) uses `(0.5 + ... * 6.0)`. Code is authoritative
     over comment — the code formula is ported.
  5. NEAREST-TEXEL strip sampling, per THREE.NearestFilter on the LED
     DataTextures (useK1Physics.ts:99-100): texel = min(floor(u*N), N-1)
     with u clamped (clamp-to-edge). No linear interpolation between LEDs.
  6. PIXEL-CENTRE UV convention: vUv = ((x+0.5)/W, (row+0.5)/H), matching GL
     fragment rasterisation of the full-screen quad.
  7. secondary_rgb=None renders a dark top edge (zero strip). Real K1
     hardware always drives both channels, but the current render_replay
     dump surface is single-channel; primary-only is the honest mapping
     until dual-channel replay adoption lands.
  8. The shader has a single uResolution for both strips
     (K1CoreScene.tsx:101); mismatched strip lengths are therefore a
     ValueError here, not silently resampled.
  9. Returned image rows follow standard image convention: row 0 = TOP edge
     (secondary), row H-1 = BOTTOM edge (primary). The shader's vUv.y axis
     points the other way; the flip happens once, at return.
"""

from __future__ import annotations

import numpy as np

try:  # scipy is optional; the fixed 15-tap kernel needs only NumPy.
    import scipy  # noqa: F401
    HAVE_SCIPY = True
except ImportError:  # pragma: no cover
    HAVE_SCIPY = False

K1_OPTICS_VERSION = "K1Optics_v1"          # edgeLitShader.ts:3

# --- K1_PHYSICAL_V1 preset (presets.ts:30-58) -------------------------------
PHYSICAL_EXPOSURE = 4.0                    # presets.ts:33
PHYSICAL_BASE_LEVEL = 0.0                  # presets.ts:34
PHYSICAL_TINT = (1.0, 1.0, 1.0)            # presets.ts:35 ('#ffffff')
PHYSICAL_SPREAD_NEAR = 0.015               # presets.ts:41-44 (top == bottom)
PHYSICAL_FALLOFF = 1.5                     # presets.ts:45-46 (top == bottom)
# Uniform defaults not in the preset object (K1CoreScene.tsx):
PHYSICAL_HOTSPOT_GAIN = 4.0                # K1CoreScene.tsx:127
PHYSICAL_GRAIN_STRENGTH = 0.0              # K1CoreScene.tsx:126 (see note 1)

# --- sampleStrip kernel (common.ts:16-38) ------------------------------------
SAMPLE_TAPS = 7                            # common.ts:20 (samples = 7.0)
WEIGHT_FLOOR = 1e-5                        # common.ts:37 max(totalWeight,1e-5)

# Hotspot bands (edgeLitShader.ts:69-70)
BOTTOM_HOTSPOT_EDGE = 0.02
TOP_HOTSPOT_EDGE = 0.98


def _smoothstep(edge0: float, edge1: float, x: np.ndarray) -> np.ndarray:
    """GLSL smoothstep (works for edge0 > edge1, as the shader relies on)."""
    t = np.clip((x - edge0) / (edge1 - edge0), 0.0, 1.0)
    return t * t * (3.0 - 2.0 * t)


def _sample_strip(strip: np.ndarray, u_x: np.ndarray,
                  sigmas: np.ndarray) -> np.ndarray:
    """Port of sampleStrip (common.ts:16-38), vectorised over rows/columns.

    strip : (N, 3) float LED colours.
    u_x   : (W,) plate-pixel uv.x at column centres.
    sigmas: (H,) per-row gaussian sigma in UV units (spread).
    Returns (H, W, 3): the laterally blurred strip colour per plate pixel.
    """
    n = strip.shape[0]
    pixel_width = 1.0 / n                                   # common.ts:21
    taps = np.arange(-SAMPLE_TAPS, SAMPLE_TAPS + 1, dtype=np.float64)
    offsets = taps * pixel_width                            # common.ts:25
    # Sample positions, clamped to [0,1] (common.ts:30), nearest texel
    # (useK1Physics.ts NearestFilter — PORT-NOTES 5).
    u = np.clip(u_x[None, :] + offsets[:, None], 0.0, 1.0)  # (T, W)
    idx = np.minimum((u * n).astype(np.int64), n - 1)
    sampled = strip[idx]                                    # (T, W, 3)
    # Per-row gaussian weights over tap offsets (common.ts:11-13, :26).
    sig = np.maximum(np.asarray(sigmas, dtype=np.float64), 1e-9)[:, None]
    w = np.exp(-(offsets[None, :] ** 2) / (2.0 * sig * sig))  # (H, T)
    w_sum = np.maximum(w.sum(axis=1), WEIGHT_FLOOR)           # common.ts:37
    return np.einsum("ht,twc->hwc", w, sampled) / w_sum[:, None, None]


def _as_strip(arr, name: str) -> np.ndarray:
    a = np.asarray(arr, dtype=np.float64)
    if a.ndim != 2 or a.shape[1] != 3 or a.shape[0] < 1:
        raise ValueError("%s must be an (N, 3) RGB array, got shape %s"
                         % (name, a.shape))
    return a


def render_plate(primary_rgb, secondary_rgb=None, width: int = 160,
                 height: int = 60, *,
                 exposure: float = PHYSICAL_EXPOSURE,
                 base_level: float = PHYSICAL_BASE_LEVEL,
                 tint=PHYSICAL_TINT,
                 spread_near: float = PHYSICAL_SPREAD_NEAR,
                 falloff: float = PHYSICAL_FALLOFF,
                 hotspot_gain: float = PHYSICAL_HOTSPOT_GAIN) -> np.ndarray:
    """Render diffused K1 plate emission from per-LED strip colours.

    primary_rgb   : (N, 3) float RGB in [0,1] — BOTTOM edge injection.
    secondary_rgb : (N, 3) float RGB in [0,1] — TOP edge injection, or None
                    for a dark top edge (PORT-NOTES 7).
    width, height : output plate raster size.
    Keyword overrides default to the K1_PHYSICAL_V1 preset (provenance in
    module docstring); leave them alone for canonical PHYSICAL output.

    Returns (height, width, 3) float64 in [0,1]; row 0 = TOP edge,
    row height-1 = BOTTOM edge (PORT-NOTES 9).
    """
    primary = _as_strip(primary_rgb, "primary_rgb")
    if secondary_rgb is None:
        secondary = np.zeros_like(primary)
    else:
        secondary = _as_strip(secondary_rgb, "secondary_rgb")
        if secondary.shape[0] != primary.shape[0]:
            raise ValueError(
                "primary (%d) and secondary (%d) strip lengths differ; the "
                "shader has a single uResolution (K1CoreScene.tsx:101) — "
                "PORT-NOTES 8" % (primary.shape[0], secondary.shape[0]))
    if width < 1 or height < 1:
        raise ValueError("width and height must be >= 1")

    # Pixel-centre UVs (PORT-NOTES 6). uy: 0 = bottom edge, 1 = top edge.
    u_x = (np.arange(width, dtype=np.float64) + 0.5) / width
    u_y = (np.arange(height, dtype=np.float64) + 0.5) / height

    # PHYSICAL spreads — edgeLitShader.ts:57-58 (code over comment, note 4).
    bottom_spread = spread_near * (0.5 + u_y * 6.0)
    top_spread = spread_near * (0.5 + (1.0 - u_y) * 6.0)

    # Vertical attenuation — edgeLitShader.ts:60-61.
    bottom_influence = np.power(1.0 - u_y, falloff)[:, None, None]
    top_influence = np.power(u_y, falloff)[:, None, None]

    # Lateral diffusion — edgeLitShader.ts:63-64.
    color_bottom = _sample_strip(primary, u_x, bottom_spread)
    color_top = _sample_strip(secondary, u_x, top_spread)

    # Dual-edge combination — edgeLitShader.ts:66.
    final = color_bottom * bottom_influence + color_top * top_influence

    # Edge hotspots — edgeLitShader.ts:69-71.
    bottom_hotspot = _smoothstep(BOTTOM_HOTSPOT_EDGE, 0.0, u_y)[:, None]
    top_hotspot = _smoothstep(TOP_HOTSPOT_EDGE, 1.0, u_y)[:, None]
    total_hotspot = (bottom_hotspot * np.linalg.norm(color_bottom, axis=2)
                     + top_hotspot * np.linalg.norm(color_top, axis=2))

    # Composition + exposure + tint — edgeLitShader.ts:75-78
    # (grain omitted, PORT-NOTES 1).
    out = final + base_level
    out = out * exposure + total_hotspot[:, :, None] * hotspot_gain
    out = out * np.asarray(tint, dtype=np.float64).reshape(1, 1, 3)

    # Clamp (PORT-NOTES 3) and flip to image convention (PORT-NOTES 9).
    return np.clip(out, 0.0, 1.0)[::-1].copy()
