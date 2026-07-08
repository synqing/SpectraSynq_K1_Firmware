#pragma once

#include <stdint.h>
#include "constants.h"

enum SBEdgeMixerMode : uint8_t {
  SB_EDGE_MIXER_OFF = 0,
  SB_EDGE_MIXER_ANALOGOUS,
  SB_EDGE_MIXER_COMPLEMENTARY,
  SB_EDGE_MIXER_SPLIT_COMPLEMENTARY,
  SB_EDGE_MIXER_SATURATION_VEIL,
  SB_EDGE_MIXER_TRIADIC,
  SB_EDGE_MIXER_TETRADIC
};

// Colour rotation space for the harmony transform.
//   SUM_PRESERVING  — the proven hue-rotation-around-grey-axis matrix (EdgeMixer
//                     golden-master lineage; parity-validated to +/-1 LSB). This
//                     is the DEFAULT and is byte-identical to the frozen path.
//   LUMA_PRESERVING — the grey-axis rotation followed by a per-pixel BT.601 luma
//                     rescale at render time (see sb_edge_transform); preserves
//                     hue + saturation while re-pinning brightness to the input.
//   OKLAB           — a PERCEPTUAL hue rotation performed in the OKLab a/b plane
//                     (Ottosson 2020). Structurally different from the two grey-
//                     axis paths: it is a per-pixel, non-linear round trip
//                     (sRGB-gamma decode -> linear -> LMS -> cube-root -> OKLab
//                     -> 2D a/b rotation by the mode's theta -> inverse -> gamma
//                     encode), NOT a 3x3 matrix bake. It rotates hue while
//                     holding perceptual lightness (L) constant, so — unlike the
//                     sum-preserving path — it does not lurch brightness across a
//                     rotation. A mode's desaturation (satRetain) is applied as a
//                     direct OKLab chroma scale. Validated against a float OKLab
//                     oracle within a documented perceptual band (NOT +/-1 LSB;
//                     OKLab is a different transform). See sb_edgemixer_lite.cpp
//                     and scripts/regression-harness/edgemixer_oklab_probe.cpp.
enum SBEdgeMixerRotationSpace : uint8_t {
  SB_EDGE_ROTATION_SUM_PRESERVING = 0,
  SB_EDGE_ROTATION_LUMA_PRESERVING = 1,
  SB_EDGE_ROTATION_OKLAB = 2
};

// Symmetric dual-edge split (A lane). The EdgeMixer transform normally shifts only
// the SECONDARY strip; ONE_SIDED keeps that (the certified single-edge default).
// SPLIT and MIRROR make BOTH edges participate symmetrically about the 79/80
// centre so neither strip is the untouched one, by baking a SECOND coefficient set
// for the PRIMARY strip at a mirrored angle — the SAME frozen colour transform,
// only a different baked angle. The primary set is applied to the primary buffer
// OUTSIDE the secondary render scope (see sb_edgemixer_lite_apply_primary). The
// mode's desaturation (satRetain) is shared by both strips; only the rotation
// angle splits.
//   ONE_SIDED — secondary theta, primary untouched (DEFAULT; byte-inert: no
//               primary application, secondary baked at the unchanged angle).
//   SPLIT     — secondary +theta/2, primary -theta/2 (centred; same edge-to-edge
//               separation theta, both edges shift equally).
//   MIRROR    — secondary +theta, primary -theta (wide; full opposite rotations).
// Rotation modes split meaningfully; SATURATION_VEIL (theta 0) desaturates both
// strips identically with no hue split.
enum SBEdgeMixerDualEdge : uint8_t {
  SB_EDGE_DUAL_ONE_SIDED = 0,
  SB_EDGE_DUAL_SPLIT = 1,
  SB_EDGE_DUAL_MIRROR = 2
};

struct SBEdgeMixerConfig {
  bool enabled;
  SBEdgeMixerMode mode;
  float strength;
  // Spread in degrees (0-60). Drives ANALOGOUS/TRIADIC/TETRADIC rotation angle
  // and SATURATION_VEIL / TRIADIC / TETRADIC desaturation retention, mirroring
  // the LightwaveOS EdgeMixer source. Clamped to [0, 60] on set.
  uint8_t spreadDegrees;
  // Rotation space (default SUM_PRESERVING). LUMA_PRESERVING (ref C) rescales each
  // rotated pixel to the input's BT.601 luma at render time (see sb_edge_transform);
  // the 'u' hotkey selects it. OKLAB performs a perceptual hue rotation in the
  // OKLab a/b plane at render time (see sb_edge_transform_oklab), holding
  // perceptual lightness constant; it is a structural per-pixel round trip, not a
  // matrix bake. Any value outside the enum is sanitised to SUM_PRESERVING on set.
  SBEdgeMixerRotationSpace rotationSpace;
  // Spatial weighting (ref E). false (default) = centre-mask: the colour shift
  // fades from 0 at the strip centre (LED 79/80) to full at the strip ends. true =
  // uniform: the shift is applied evenly across the strip. Edge-to-edge LGP
  // differentiation comes from the per-strip colour difference by physics; the mask
  // only adds along-strip end-emphasis. A bench A/B decides the default.
  bool spatialUniform;
  // Symmetric dual-edge split (A lane). DEFAULT ONE_SIDED = byte-inert: the primary
  // strip is untouched and the secondary is baked at the unchanged angle, so the
  // certified single-edge behaviour is preserved bit-for-bit. SPLIT / MIRROR bake a
  // second primary-angle coefficient set applied via sb_edgemixer_lite_apply_primary().
  // The default member initialiser guarantees every construction path defaults to
  // ONE_SIDED even where fields are set individually; sanitised again on set.
  SBEdgeMixerDualEdge dualEdge = SB_EDGE_DUAL_ONE_SIDED;
};

SBEdgeMixerConfig sb_edgemixer_lite_config();
void sb_edgemixer_lite_set_config(const SBEdgeMixerConfig& config);
void sb_edgemixer_lite_apply(CRGB16* secondary, uint16_t count, const SBEdgeMixerConfig& config);
// Apply the PRIMARY-edge transform (dual-edge SPLIT / MIRROR only) to the primary
// strip buffer, using the second config-time-baked coefficient set at the mirrored
// angle. No-op when config.dualEdge == ONE_SIDED. MUST be called OUTSIDE the
// secondary render scope, on the primary strip's own buffer. Same frozen per-pixel
// transform as sb_edgemixer_lite_apply — only the baked angle differs.
void sb_edgemixer_lite_apply_primary(CRGB16* primary, uint16_t count, const SBEdgeMixerConfig& config);

#ifdef SB_EDGEMIXER_HOST_TEST
// Host-only parity-test hooks (compiled out of every production/device build;
// SB_EDGEMIXER_HOST_TEST is defined ONLY by the native parity probe). They
// expose the config-time colour matrix so the golden-master oracle can read it
// and inject a perturbed coefficient for the fault-evidence case. Not shippable.
void sb_edgemixer_lite_test_get_matrix(SQ15x16* out9);
void sb_edgemixer_lite_test_set_matrix(const SQ15x16* in9);
#endif

#ifdef SB_EDGEMIXER_AB_DEMO
// BENCH-ONLY A/B demo scaffold (TEMPORARY). Compiled out of production: the
// k1_hardware build does NOT define SB_EDGEMIXER_AB_DEMO, so the shipping binary
// is byte-unaffected. When defined, sb_edgemixer_ab_demo_tick() force-enables the
// EdgeMixer and cycles its mode (ANALOGOUS -> COMPLEMENTARY -> TRIADIC) on a ~4 s
// timer at full strength / spread 30 / SUM_PRESERVING, so the Captain can eyeball
// the Strip 2 edge-colour transform against an untouched baseline unit. Call once
// per render frame BEFORE the frame reads sb_edgemixer_lite_config(). Not shippable.
void sb_edgemixer_ab_demo_tick();
#endif
