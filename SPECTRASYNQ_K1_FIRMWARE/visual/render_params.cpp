// render_params.cpp
// ============================================================================
// RenderParams core implementation (secondary-renderparams, 2026-05-26).
//
// Real TU (ODR-safe): the params stack lives in static .bss here, no heap.
// ============================================================================

#include "render_params.h"
#include "globals.h"

RenderParams build_primary_render_params() {
  RenderParams p;

  // Mutated-for-secondary fields (live CONFIG).
  p.LIGHTSHOW_MODE      = CONFIG.LIGHTSHOW_MODE;
  p.PHOTONS             = CONFIG.PHOTONS;
  p.CHROMA              = CONFIG.CHROMA;
  p.MOOD                = CONFIG.MOOD;
  p.SATURATION          = CONFIG.SATURATION;
  p.MIRROR_ENABLED      = CONFIG.MIRROR_ENABLED;
  p.AUTO_COLOR_SHIFT    = CONFIG.AUTO_COLOR_SHIFT;
  p.INCANDESCENT_FILTER = CONFIG.INCANDESCENT_FILTER;
  p.INCANDESCENT_MODE   = CONFIG.INCANDESCENT_MODE;

  // Fields NOT mutated for secondary (secondary reads primary CONFIG today).
  p.SQUARE_ITER          = CONFIG.SQUARE_ITER;
  p.PALETTE_MODE_ENABLED = CONFIG.PALETTE_MODE_ENABLED;
  p.PALETTE_INDEX        = CONFIG.PALETTE_INDEX;
  p.SWEET_SPOT_MIN_LEVEL = CONFIG.SWEET_SPOT_MIN_LEVEL;
  p.SENSITIVITY          = CONFIG.SENSITIVITY;
  p.SAMPLES_PER_CHUNK    = CONFIG.SAMPLES_PER_CHUNK;

  // Still-global colour state (channel-invariant — same value both channels).
  p.hue_position    = hue_position;
  p.chroma_val      = chroma_val;
  p.chromatic_mode  = chromatic_mode;
  p.hue_shifting_mix = hue_shifting_mix;

  return p;
}

RenderParams build_secondary_render_params() {
  RenderParams p = build_primary_render_params();

  // Overwrite ONLY the 9 fields that apply_secondary_render_config() used to
  // mutate in global CONFIG. Everything else stays at primary values.
  p.LIGHTSHOW_MODE      = SECONDARY_LIGHTSHOW_MODE;
  p.PHOTONS             = SECONDARY_PHOTONS;
  p.CHROMA              = SECONDARY_CHROMA;
  p.MOOD                = SECONDARY_MOOD;
  p.MIRROR_ENABLED      = SECONDARY_MIRROR_ENABLED;
  p.SATURATION          = SECONDARY_SATURATION;
  p.AUTO_COLOR_SHIFT    = SECONDARY_AUTO_COLOR_SHIFT;
  p.INCANDESCENT_FILTER = SECONDARY_INCANDESCENT_FILTER;
  p.INCANDESCENT_MODE   = SECONDARY_INCANDESCENT_MODE;

  return p;
}

// Fixed-depth params stack (max depth 2): index 0 = primary, index 1 = secondary.
static RenderParams stack[2];
static int top = -1;

void push_render_params(const RenderParams* params) {
  if (params == nullptr) {
    return;
  }
  if (top < 1) {
    top++;
  }
  stack[top] = *params;
}

void pop_render_params() {
  if (top >= 0) {
    top--;
  }
}

const RenderParams* active_render_params() {
  if (top >= 0) {
    return &stack[top];
  }
  // Empty stack (e.g. the VP probe path, which never pushes): mirror live
  // CONFIG so reads are bit-identical to direct CONFIG reads.
  static RenderParams fallback;
  fallback = build_primary_render_params();
  return &fallback;
}

int active_render_params_depth() {
  return top;
}
