#include "palette_flow.h"

#include <math.h>

namespace {

constexpr float kTau = 6.28318530718f;
constexpr float kWaveAmplitudePx[PALETTE_FLOW_WAVE_COUNT] = {8.0f, 3.0f, 1.0f};
constexpr float kWaveSpatialFrequency[PALETTE_FLOW_WAVE_COUNT] = {1.0f, 3.0f, 7.0f};
constexpr float kWaveVerticalFrequency[PALETTE_FLOW_WAVE_COUNT] = {0.38f, 0.85f, 1.35f};

uint32_t next_random(uint32_t* state)
{
  uint32_t x = *state;
  x ^= x << 13;
  x ^= x >> 17;
  x ^= x << 5;
  *state = x;
  return x;
}

float random_unit(uint32_t* state)
{
  return static_cast<float>(next_random(state) >> 8) * (1.0f / 16777216.0f);
}

float random_range(uint32_t* state, float minimum, float maximum)
{
  return minimum + (maximum - minimum) * random_unit(state);
}

float smootherstep(float t)
{
  if (t <= 0.0f) return 0.0f;
  if (t >= 1.0f) return 1.0f;
  return t * t * t * (t * (t * 6.0f - 15.0f) + 10.0f);
}

void start_channel(PaletteFlowChannel* channel,
                   uint32_t* random_state,
                   float minimum,
                   float maximum,
                   float duration_minimum_s,
                   float duration_maximum_s)
{
  channel->minimum = minimum;
  channel->maximum = maximum;
  channel->duration_minimum_s = duration_minimum_s;
  channel->duration_maximum_s = duration_maximum_s;
  channel->value = random_range(random_state, minimum, maximum);
  channel->start = channel->value;
  channel->target = random_range(random_state, minimum, maximum);
  channel->elapsed_s = 0.0f;
  channel->duration_s = random_range(random_state, duration_minimum_s, duration_maximum_s);
}

void step_channel(PaletteFlowChannel* channel, uint32_t* random_state, float dt_s)
{
  channel->elapsed_s += dt_s;
  while (channel->elapsed_s >= channel->duration_s) {
    channel->elapsed_s -= channel->duration_s;
    channel->value = channel->target;
    channel->start = channel->value;
    channel->target = random_range(random_state, channel->minimum, channel->maximum);
    channel->duration_s = random_range(
        random_state, channel->duration_minimum_s, channel->duration_maximum_s);
  }
  const float t = channel->elapsed_s / channel->duration_s;
  channel->value = channel->start +
                   (channel->target - channel->start) * smootherstep(t);
}

float wrap_unit(float phase)
{
  phase -= floorf(phase);
  return phase < 0.0f ? phase + 1.0f : phase;
}

}  // namespace

void palette_flow_init(PaletteFlowState* state, uint32_t seed)
{
  if (!state) return;
  state->random_state = seed ? seed : 0x6D2B79F5u;
  state->travel_phase = random_unit(&state->random_state);
  for (size_t i = 0; i < PALETTE_FLOW_WAVE_COUNT; ++i) {
    state->wave_phase[i] = random_unit(&state->random_state);
  }

  /* The current always advances. Spatial waves may move against it. */
  start_channel(&state->velocity[0], &state->random_state, 0.080f, 0.260f, 1.4f, 4.8f);
  start_channel(&state->velocity[1], &state->random_state, 0.025f, 0.065f, 2.0f, 6.0f);
  start_channel(&state->velocity[2], &state->random_state, -0.085f, -0.035f, 2.4f, 7.0f);
  start_channel(&state->velocity[3], &state->random_state, 0.090f, 0.160f, 1.8f, 5.5f);
}

void palette_flow_step(PaletteFlowState* state, float dt_s)
{
  if (!state || dt_s <= 0.0f) return;
  if (dt_s > 0.050f) dt_s = 0.050f;
  for (PaletteFlowChannel& channel : state->velocity) {
    step_channel(&channel, &state->random_state, dt_s);
  }

  state->travel_phase = wrap_unit(state->travel_phase + state->velocity[0].value * dt_s);
  for (size_t i = 0; i < PALETTE_FLOW_WAVE_COUNT; ++i) {
    state->wave_phase[i] = wrap_unit(
        state->wave_phase[i] + state->velocity[i + 1].value * dt_s);
  }
}

void palette_flow_build_samples(const PaletteFlowState* state,
                                size_t width,
                                uint16_t* samples_q16)
{
  palette_flow_build_field(state, width, 1, samples_q16, nullptr);
}

void palette_flow_build_field(const PaletteFlowState* state,
                              size_t width,
                              size_t height,
                              uint16_t* samples_q16,
                              int8_t* light_delta_q8)
{
  if (!state || !samples_q16 || width == 0 || height == 0 ||
      width > PALETTE_FLOW_MAX_WIDTH) return;

  float step_sin[PALETTE_FLOW_WAVE_COUNT];
  float step_cos[PALETTE_FLOW_WAVE_COUNT];
  for (size_t i = 0; i < PALETTE_FLOW_WAVE_COUNT; ++i) {
    const float step = kTau * kWaveSpatialFrequency[i] / static_cast<float>(width);
    step_sin[i] = sinf(step);
    step_cos[i] = cosf(step);
  }

  const float travel_px = state->travel_phase * static_cast<float>(width);
  const float height_scale = height > 1 ? 1.0f / static_cast<float>(height - 1) : 0.0f;
  for (size_t y = 0; y < height; ++y) {
    float wave_sin[PALETTE_FLOW_WAVE_COUNT];
    float wave_cos[PALETTE_FLOW_WAVE_COUNT];
    for (size_t i = 0; i < PALETTE_FLOW_WAVE_COUNT; ++i) {
      const float vertical_phase = kWaveVerticalFrequency[i] *
                                   static_cast<float>(y) * height_scale;
      const float phase = kTau * (state->wave_phase[i] + vertical_phase);
      wave_sin[i] = sinf(phase);
      wave_cos[i] = cosf(phase);
    }

    for (size_t x = 0; x < width; ++x) {
      float source_px = static_cast<float>(x) + travel_px;
      float shimmer = 0.0f;
      for (size_t i = 0; i < PALETTE_FLOW_WAVE_COUNT; ++i) {
        source_px += kWaveAmplitudePx[i] * wave_sin[i];
        const float weight = i == 0 ? 0.55f : (i == 1 ? 0.30f : 0.15f);
        shimmer += weight * wave_cos[i];
      }
      float unit = source_px / static_cast<float>(width);
      unit -= floorf(unit);
      if (unit < 0.0f) unit += 1.0f;
      const size_t pixel = y * width + x;
      samples_q16[pixel] = static_cast<uint16_t>(unit * 65536.0f);
      if (light_delta_q8) {
        float delta = -8.0f + 34.0f * shimmer;
        if (delta < -40.0f) delta = -40.0f;
        if (delta > 24.0f) delta = 24.0f;
        light_delta_q8[pixel] = static_cast<int8_t>(delta);
      }

      for (size_t i = 0; i < PALETTE_FLOW_WAVE_COUNT; ++i) {
        const float next_sin = wave_sin[i] * step_cos[i] + wave_cos[i] * step_sin[i];
        const float next_cos = wave_cos[i] * step_cos[i] - wave_sin[i] * step_sin[i];
        wave_sin[i] = next_sin;
        wave_cos[i] = next_cos;
      }
    }
  }
}

float palette_flow_minimum_jacobian(size_t width)
{
  if (width == 0) return 0.0f;
  float deformation = 0.0f;
  for (size_t i = 0; i < PALETTE_FLOW_WAVE_COUNT; ++i) {
    deformation += kWaveAmplitudePx[i] * kTau * kWaveSpatialFrequency[i] /
                   static_cast<float>(width);
  }
  return 1.0f - deformation;
}

void palette_flow_prefilter_rgb888(const uint32_t* input,
                                   size_t count,
                                   uint32_t* output)
{
  if (!input || !output || count == 0) return;
  static constexpr uint8_t kWeights[11] = {1, 2, 3, 4, 5, 6, 5, 4, 3, 2, 1};
  static constexpr uint32_t kWeightSum = 36;
  for (size_t i = 0; i < count; ++i) {
    uint32_t r_linear = 0;
    uint32_t g_linear = 0;
    uint32_t b_linear = 0;
    for (int offset = -5; offset <= 5; ++offset) {
      const size_t source = static_cast<size_t>(
          (static_cast<long>(i) + offset + static_cast<long>(count)) %
          static_cast<long>(count));
      const uint32_t rgb = input[source];
      const uint32_t r = (rgb >> 16) & 0xFFu;
      const uint32_t g = (rgb >> 8) & 0xFFu;
      const uint32_t b = rgb & 0xFFu;
      const uint32_t weight = kWeights[offset + 5];
      r_linear += r * r * weight;
      g_linear += g * g * weight;
      b_linear += b * b * weight;
    }
    const uint8_t r = static_cast<uint8_t>(sqrtf(static_cast<float>(r_linear) /
                                                 static_cast<float>(kWeightSum)));
    const uint8_t g = static_cast<uint8_t>(sqrtf(static_cast<float>(g_linear) /
                                                 static_cast<float>(kWeightSum)));
    const uint8_t b = static_cast<uint8_t>(sqrtf(static_cast<float>(b_linear) /
                                                 static_cast<float>(kWeightSum)));
    output[i] = (static_cast<uint32_t>(r) << 16) |
                (static_cast<uint32_t>(g) << 8) | b;
  }
}
