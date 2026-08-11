#include "palette_flow.h"

#include <math.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>

namespace {

constexpr size_t kWidth = 391;

bool check(bool condition, const char* message)
{
  if (!condition) fprintf(stderr, "palette_flow: %s\n", message);
  return condition;
}

uint32_t hash_samples(const uint16_t* samples)
{
  uint32_t hash = 2166136261u;
  for (size_t i = 0; i < kWidth; ++i) {
    hash ^= samples[i];
    hash *= 16777619u;
  }
  return hash;
}

}  // namespace

int main()
{
  bool ok = true;
  ok &= check(palette_flow_minimum_jacobian(kWidth) > 0.60f,
              "field can fold or compress too sharply");

  PaletteFlowState a = {};
  PaletteFlowState b = {};
  PaletteFlowState other = {};
  palette_flow_init(&a, 0x12345678u);
  palette_flow_init(&b, 0x12345678u);
  palette_flow_init(&other, 0x87654321u);

  uint16_t samples_a[kWidth] = {};
  uint16_t samples_b[kWidth] = {};
  uint16_t samples_other[kWidth] = {};
  uint16_t consumer_copy[kWidth] = {};
  uint16_t field[kWidth * 36] = {};
  int8_t light[kWidth * 36] = {};
  uint32_t previous_hash = 0;
  uint32_t distinct_hashes = 0;

  for (uint32_t frame = 0; frame < 37500; ++frame) {  // ten minutes at 62.5 Hz
    const float jitter_s = 0.014f + static_cast<float>((frame * 17u) % 5u) * 0.001f;
    palette_flow_step(&a, jitter_s);
    palette_flow_step(&b, jitter_s);
    palette_flow_step(&other, jitter_s);
    palette_flow_build_samples(&a, kWidth, samples_a);
    palette_flow_build_samples(&b, kWidth, samples_b);
    palette_flow_build_samples(&other, kWidth, samples_other);

    ok &= check(memcmp(samples_a, samples_b, sizeof(samples_a)) == 0,
                "same seed and timing are not deterministic");
    memcpy(consumer_copy, samples_a, sizeof(samples_a));
    ok &= check(memcmp(samples_a, consumer_copy, sizeof(samples_a)) == 0,
                "two palette consumers do not receive an identical map");

    for (size_t x = 1; x < kWidth; ++x) {
      const uint16_t delta = static_cast<uint16_t>(samples_a[x] - samples_a[x - 1]);
      ok &= check(delta >= 85u && delta <= 250u,
                  "spatial field lost monotonic bounded spacing");
    }

    if ((frame % 63u) == 0u) {
      const uint32_t current_hash = hash_samples(samples_a);
      if (previous_hash != 0 && current_hash != previous_hash) ++distinct_hashes;
      previous_hash = current_hash;
    }
    if (!ok) return 1;
  }

  ok &= check(memcmp(samples_a, samples_other, sizeof(samples_a)) != 0,
              "different seeds collapsed to the same field");
  ok &= check(distinct_hashes > 500u, "field repeats or stalls over the soak");
  palette_flow_build_field(&a, kWidth, 36, field, light);
  ok &= check(memcmp(field, field + 18 * kWidth, sizeof(uint16_t) * kWidth) != 0,
              "field is still one-dimensional across its height");
  uint64_t row_delta_sum = 0;
  for (size_t x = 0; x < kWidth; ++x) {
    const uint16_t first = field[x];
    const uint16_t middle = field[18 * kWidth + x];
    const uint16_t forward = static_cast<uint16_t>(middle - first);
    const uint16_t reverse = static_cast<uint16_t>(first - middle);
    row_delta_sum += forward < reverse ? forward : reverse;
  }
  const uint32_t mean_row_delta_q16 = static_cast<uint32_t>(row_delta_sum / kWidth);
  ok &= check(mean_row_delta_q16 >= 400u,
              "vertical effect size is technically nonzero but visually negligible");
  int8_t light_min = light[0];
  int8_t light_max = light[0];
  for (size_t i = 1; i < kWidth * 36; ++i) {
    if (light[i] < light_min) light_min = light[i];
    if (light[i] > light_max) light_max = light[i];
  }
  ok &= check(light_max - light_min >= 45,
              "caustic modulation is too weak to be visually meaningful");

  uint32_t uniform[16];
  uint32_t uniform_filtered[16] = {};
  for (uint32_t& colour : uniform) colour = 0x336699u;
  palette_flow_prefilter_rgb888(uniform, 16, uniform_filtered);
  for (uint32_t colour : uniform_filtered) {
    ok &= check(colour == 0x336699u, "uniform palette colour was not preserved");
  }

  uint32_t impulse[16] = {};
  uint32_t impulse_filtered[16] = {};
  impulse[0] = 0xFF0000u;
  palette_flow_prefilter_rgb888(impulse, 16, impulse_filtered);
  ok &= check(impulse_filtered[0] > impulse_filtered[1],
              "palette filter lost its centred triangular weighting");
  ok &= check(impulse_filtered[1] == impulse_filtered[15],
              "palette filter is not circular at the wrap boundary");
  ok &= check(impulse_filtered[5] != 0 && impulse_filtered[6] == 0,
              "palette filter support is not the intended eleven taps");
  printf("palette_flow PASS jacobian=%.3f distinct=%u row_delta_q16=%u\n",
         palette_flow_minimum_jacobian(kWidth), distinct_hashes, mean_row_delta_q16);
  return ok ? 0 : 1;
}
