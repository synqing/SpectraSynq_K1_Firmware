#pragma once

// render_params.h
// ============================================================================
// RenderParams core (secondary-renderparams, 2026-05-26)
//
// Immutable per-channel render parameter snapshot. Modes read render params
// through active_render_params() instead of reading global CONFIG directly, so
// the SECONDARY render pass no longer has to MUTATE global CONFIG in place.
//
// Behaviour-preserving: when the params stack is empty (e.g. the VP probe path,
// which never pushes), active_render_params() returns a snapshot freshly built
// from live CONFIG + colour-state globals, so reads are bit-identical to the
// pre-RenderParams direct CONFIG reads.
//
// Field types mirror struct conf (config_types.h) plus the still-global colour
// state (hue_position, chroma_val, chromatic_mode, hue_shifting_mix).
// ============================================================================

#include <FixedPointsCommon.h>
#include "config_types.h"

struct RenderParams {
  // --- Mutated-for-secondary CONFIG fields (the 9 SECONDARY_* overrides) ---
  uint8_t  LIGHTSHOW_MODE;
  float    PHOTONS;
  float    CHROMA;
  float    MOOD;
  float    SATURATION;
  bool     MIRROR_ENABLED;
  bool     AUTO_COLOR_SHIFT;
  float    INCANDESCENT_FILTER;
  bool     INCANDESCENT_MODE;

  // --- CONFIG fields that secondary reads from PRIMARY today (NOT mutated) ---
  float    SQUARE_ITER;
  bool     PALETTE_MODE_ENABLED;
  uint8_t  PALETTE_INDEX;
  uint32_t SWEET_SPOT_MIN_LEVEL;
  float    SENSITIVITY;
  uint16_t SAMPLES_PER_CHUNK;

  // --- Still-global colour state, surfaced through rp for completeness ---
  SQ15x16  hue_position;
  SQ15x16  chroma_val;
  bool     chromatic_mode;
  SQ15x16  hue_shifting_mix;
};

// Build a snapshot of the live PRIMARY render params (global CONFIG + colour state).
RenderParams build_primary_render_params();

// Build the SECONDARY render params: primary snapshot with the 9 SECONDARY_*
// overrides applied; all other fields stay at their primary values.
RenderParams build_secondary_render_params();

// Fixed-depth, heap-free params stack (max depth 2). push() caps at the top
// slot; pop() unwinds; active() returns the current top, or a freshly-built
// primary snapshot when the stack is empty.
void push_render_params(const RenderParams* params);
void pop_render_params();
const RenderParams* active_render_params();

// Current params-stack top index: -1 = empty (active() falls back to live CONFIG),
// 0 = primary slot, 1 = secondary slot. Harness instrumentation only (VPS status).
int active_render_params_depth();
