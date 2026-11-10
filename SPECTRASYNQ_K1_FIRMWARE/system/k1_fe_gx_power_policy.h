#pragma once

#include <stdint.h>

// K1-FE-Gx: TPS259474LRPWR, R_ILM=2.21k; GPIO39 adds 2.61k in
// parallel. These select nominal 1.51 / 2.79 A *trip thresholds*, not a
// regulated load current. The LED ceilings below are initial estimates with
// a 400 mA allowance for the rest of the board. Bench calibration is required.
// CC voltages are calibrated ADC readings at the actual sense pins. The
// fitted 100k series resistors still need a measured ADC-settling check.
enum class K1FeGxSource : uint8_t { Invalid, DefaultUsb, Amp1_5, Amp3 };

static constexpr uint16_t K1_FE_GX_LED_LOW_MA = 800;
static constexpr uint16_t K1_FE_GX_LED_HIGH_MA = 1900;
static constexpr uint32_t K1_FE_GX_SOURCE_STABLE_MS = 250;
static constexpr uint32_t K1_FE_GX_DROP_MAX_MS = 40;
static constexpr uint32_t K1_FE_GX_FRAME_SETTLE_MS = 10;

static inline K1FeGxSource k1_fe_gx_classify_cc(uint32_t cc1_mv,
                                              uint32_t cc2_mv) {
  // Exactly one active CC pin. Unsupported/debug/accessory and out-of-range
  // readings never authorize more current. Gaps between the USB-C voltage
  // bands deliberately select Invalid rather than guessing upward.
  const bool cc1_active = cc1_mv >= 250 && cc1_mv <= 2040;
  const bool cc2_active = cc2_mv >= 250 && cc2_mv <= 2040;
  if (cc1_active == cc2_active) return K1FeGxSource::Invalid;
  if ((cc1_active ? cc2_mv : cc1_mv) > 200) return K1FeGxSource::Invalid;
  const uint32_t active = cc1_active ? cc1_mv : cc2_mv;
  if (active <= 610) return K1FeGxSource::DefaultUsb;
  if (active >= 700 && active <= 1160) return K1FeGxSource::Amp1_5;
  if (active >= 1310) return K1FeGxSource::Amp3;
  return K1FeGxSource::Invalid;
}

static inline uint16_t k1_fe_gx_source_led_ma(K1FeGxSource source) {
  return source == K1FeGxSource::Amp3 ? K1_FE_GX_LED_HIGH_MA :
         source == K1FeGxSource::Amp1_5 ? K1_FE_GX_LED_LOW_MA : 0;
}

// Called on the housekeeping core. A higher allowance needs a stable source;
// a lower allowance is published immediately. Before lowering the hardware
// trip threshold, allow a limited LED frame to arrive. If rendering stalls,
// lower it after 40 ms anyway; the hardware breaker remains the final guard.
struct K1FeGxPowerPolicy {
  K1FeGxSource observed = K1FeGxSource::Invalid;
  uint16_t led_budget_ma = 0;
  bool permit = false;
  bool initialized = false;
  bool dropping = false;
  bool frame_seen = false;
  uint32_t source_since = 0;
  uint32_t drop_since = 0;
  uint32_t frame_since = 0;

  void update(uint32_t now, bool pg, uint32_t cc1_mv, uint32_t cc2_mv,
              bool reduced_frame_submitted) {
    const K1FeGxSource raw = pg ? k1_fe_gx_classify_cc(cc1_mv, cc2_mv)
                              : K1FeGxSource::Invalid;
    if (!initialized || raw != observed) {
      observed = raw;
      source_since = now;
      initialized = true;
    }
    const uint16_t available = k1_fe_gx_source_led_ma(raw);
    if (available < led_budget_ma) led_budget_ma = available;
    if (uint32_t(now - source_since) >= K1_FE_GX_SOURCE_STABLE_MS)
      led_budget_ma = available;

    if (!pg) {
      permit = false;
      dropping = frame_seen = false;
      return;
    }
    if (led_budget_ma == K1_FE_GX_LED_HIGH_MA && raw == K1FeGxSource::Amp3) {
      permit = true;
      dropping = frame_seen = false;
      return;
    }
    if (!permit) return;
    if (!dropping) {
      dropping = true;
      frame_seen = false;
      drop_since = now;
    }
    if (reduced_frame_submitted && !frame_seen) {
      frame_seen = true;
      frame_since = now;
    }
    if ((frame_seen && uint32_t(now - frame_since) >= K1_FE_GX_FRAME_SETTLE_MS) ||
        uint32_t(now - drop_since) >= K1_FE_GX_DROP_MAX_MS) {
      permit = false;
      dropping = frame_seen = false;
    }
  }
};

static inline uint16_t k1_fe_gx_effective_led_ma(uint32_t requested_ma,
                                                uint16_t source_budget_ma) {
  return requested_ma < source_budget_ma ? uint16_t(requested_ma)
                                         : source_budget_ma;
}
