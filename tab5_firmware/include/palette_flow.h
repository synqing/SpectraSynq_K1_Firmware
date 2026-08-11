#pragma once

#include <stddef.h>
#include <stdint.h>

/** Maximum number of columns supported by the Tab5 palette field. */
static constexpr size_t PALETTE_FLOW_MAX_WIDTH = 420;
static constexpr size_t PALETTE_FLOW_WAVE_COUNT = 3;

typedef struct {
  float value;
  float start;
  float target;
  float elapsed_s;
  float duration_s;
  float minimum;
  float maximum;
  float duration_minimum_s;
  float duration_maximum_s;
} PaletteFlowChannel;

/**
 * One shared, bounded flow state. Primary and Secondary must consume the same
 * sample map produced from this state; they never integrate independent phases.
 */
typedef struct {
  uint32_t random_state;
  float travel_phase;
  float wave_phase[PALETTE_FLOW_WAVE_COUNT];
  PaletteFlowChannel velocity[PALETTE_FLOW_WAVE_COUNT + 1];
} PaletteFlowState;

void palette_flow_init(PaletteFlowState* state, uint32_t seed);
void palette_flow_step(PaletteFlowState* state, float dt_s);
void palette_flow_build_samples(const PaletteFlowState* state,
                                size_t width,
                                uint16_t* samples_q16);
void palette_flow_build_field(const PaletteFlowState* state,
                              size_t width,
                              size_t height,
                              uint16_t* samples_q16,
                              int8_t* light_delta_q8);

/** Analytic lower bound of du/dx for the configured spatial field. */
float palette_flow_minimum_jacobian(size_t width);

/** Circular 11-tap triangular palette integration in approximate linear light. */
void palette_flow_prefilter_rgb888(const uint32_t* input,
                                   size_t count,
                                   uint32_t* output);
