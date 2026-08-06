#include "battery_gate.h"

#include <Arduino.h>
#include "knob.h"
#include "pincfg.h"

// Battery candidate-sweep logging floods the serial line (6 lines / 5 s) and
// buries perf telemetry. OFF by default; flip to 1 for divider/ADC debugging.
#define BAT_VERBOSE 0

static constexpr float BATTERY_DIVIDER_SELECTED = 2.0f;
static constexpr float BATTERY_DIVIDER_EST = 3.0f;
static constexpr float BATTERY_DIVIDER_ALT_1 = 1.5f;
static constexpr float BATTERY_DIVIDER_ALT_2 = 2.0f;
static constexpr uint32_t USB_BIASED_THRESHOLD_MV = 4200;
static constexpr uint32_t SAMPLE_INTERVAL_MS = 5000;
static constexpr uint8_t AVG_WINDOW = 4;

static uint32_t next_sample_ms = 0;
static uint32_t raw_sum = 0;
static uint32_t mv_sum = 0;
static uint8_t sample_count = 0;

static uint8_t interpolate_percent(uint32_t battery_mv,
                                   uint32_t lower_mv,
                                   uint32_t upper_mv,
                                   uint8_t lower_pct,
                                   uint8_t upper_pct)
{
  uint32_t span_mv = upper_mv - lower_mv;
  uint32_t delta_mv = battery_mv - lower_mv;
  uint32_t span_pct = upper_pct - lower_pct;
  return lower_pct + (delta_mv * span_pct) / span_mv;
}

static uint8_t percent_from_lipo_mv(uint32_t battery_mv)
{
  if (battery_mv <= 3300) {
    return 0;
  }
  if (battery_mv < 3520) {
    return interpolate_percent(battery_mv, 3300, 3520, 0, 20);
  }
  if (battery_mv < 3640) {
    return interpolate_percent(battery_mv, 3520, 3640, 20, 40);
  }
  if (battery_mv < 3760) {
    return interpolate_percent(battery_mv, 3640, 3760, 40, 60);
  }
  if (battery_mv < 3880) {
    return interpolate_percent(battery_mv, 3760, 3880, 60, 80);
  }
  if (battery_mv < 4000) {
    return interpolate_percent(battery_mv, 3880, 4000, 80, 100);
  }
  return 100;
}

static bool plausible_lipo_mv(uint32_t battery_mv)
{
  return battery_mv >= 3000 && battery_mv <= USB_BIASED_THRESHOLD_MV;
}

static bool usb_biased_mv(uint32_t battery_mv)
{
  return battery_mv > USB_BIASED_THRESHOLD_MV;
}

static void print_candidate(const char *label, float divider, uint32_t sensed_mv)
{
  uint32_t battery_mv = (uint32_t)(sensed_mv * divider);
  Serial.printf("BAT_CAND divider=%s vbat_mv=%lu pct=%u plausible=%s usb_bias=%s\n",
                label,
                (unsigned long)battery_mv,
                percent_from_lipo_mv(battery_mv),
                plausible_lipo_mv(battery_mv) ? "yes" : "no",
                usb_biased_mv(battery_mv) ? "yes" : "no");
}

static void print_attenuation_sweep(void)
{
  struct AttenCase {
    adc_attenuation_t atten;
    const char *name;
  };
  static const AttenCase cases[] = {
      {ADC_0db, "0db"},
      {ADC_2_5db, "2_5db"},
      {ADC_6db, "6db"},
      {ADC_11db, "11db"},
  };

  for (const AttenCase &c : cases) {
    analogSetAttenuation(c.atten);
    analogSetPinAttenuation(BATTERY_ADC_PIN, c.atten);
    delay(5);
    uint32_t raw = analogRead(BATTERY_ADC_PIN);
    uint32_t mv = analogReadMilliVolts(BATTERY_ADC_PIN);
#if BAT_VERBOSE
    Serial.printf("BAT_ATTEN name=%s raw=%lu mv=%lu x1_5_mv=%lu x2_0_mv=%lu x3_0_mv=%lu\n",
                  c.name,
                  (unsigned long)raw,
                  (unsigned long)mv,
                  (unsigned long)(mv * BATTERY_DIVIDER_ALT_1),
                  (unsigned long)(mv * BATTERY_DIVIDER_ALT_2),
                  (unsigned long)(mv * BATTERY_DIVIDER_EST));
#else
    (void)raw; (void)mv;
#endif
  }

  analogSetAttenuation(ADC_11db);
  analogSetPinAttenuation(BATTERY_ADC_PIN, ADC_11db);
}

static void sample_battery(void)
{
  uint32_t raw = analogRead(BATTERY_ADC_PIN);
  uint32_t mv = analogReadMilliVolts(BATTERY_ADC_PIN);

  raw_sum += raw;
  mv_sum += mv;
  if (sample_count < AVG_WINDOW) {
    sample_count++;
  } else {
    raw_sum = raw * AVG_WINDOW;
    mv_sum = mv * AVG_WINDOW;
  }

  uint32_t avg_raw = raw_sum / sample_count;
  uint32_t avg_mv = mv_sum / sample_count;
  uint32_t vbat_est_mv = (uint32_t)(avg_mv * BATTERY_DIVIDER_EST);
  uint32_t vbat_selected_mv = (uint32_t)(avg_mv * BATTERY_DIVIDER_SELECTED);
  uint8_t pct_selected = percent_from_lipo_mv(vbat_selected_mv);
  bool usb_biased = usb_biased_mv(vbat_selected_mv);

#if BAT_VERBOSE
  Serial.printf("BAT raw=%lu mv=%lu vbat_est_mv=%lu usb_bias=%s usable_for_soc=%s soc_pct_est=%u provisional=yes\n",
                (unsigned long)avg_raw,
                (unsigned long)avg_mv,
                (unsigned long)vbat_selected_mv,
                usb_biased ? "yes" : "no",
                usb_biased ? "no" : "yes",
                pct_selected);
  Serial.printf("BAT_ALT vbat_x3_mv=%lu\n", (unsigned long)vbat_est_mv);
  print_candidate("1.5", BATTERY_DIVIDER_ALT_1, avg_mv);
  print_candidate("2.0", BATTERY_DIVIDER_ALT_2, avg_mv);
  print_candidate("3.0", BATTERY_DIVIDER_EST, avg_mv);
  Serial.printf("BAT_SELECTED divider=2.0 provisional=yes vbat_mv=%lu pct=%u usb_bias=%s usable_for_soc=%s\n",
                (unsigned long)vbat_selected_mv,
                pct_selected,
                usb_biased ? "yes" : "no",
                usb_biased ? "no" : "yes");
#else
  (void)avg_raw; (void)vbat_est_mv;
#endif

  char status[48];
  if (usb_biased) {
    snprintf(status, sizeof(status), "BAT: %lumV USB bias",
             (unsigned long)vbat_selected_mv);
  } else {
    snprintf(status, sizeof(status), "BAT: %lumV %u%% est",
             (unsigned long)vbat_selected_mv,
             pct_selected);
  }
  battery_status_set(status);
}

void battery_gate_init(void)
{
  analogReadResolution(12);
  analogSetAttenuation(ADC_11db);
  analogSetPinAttenuation(BATTERY_ADC_PIN, ADC_11db);
  Serial.printf("BAT_INIT_OK pin=%d divider_candidates=1.5,2.0,3.0 selected=2.0 usb_bias_threshold_mv=%lu percent_model=provisional\n",
                BATTERY_ADC_PIN,
                (unsigned long)USB_BIASED_THRESHOLD_MV);
  Serial.println("BAT_CONTEXT operator_reported_battery_attached=yes");
  print_attenuation_sweep();
  battery_status_set("BAT: sampling");
  sample_battery();
  next_sample_ms = millis() + SAMPLE_INTERVAL_MS;
}

void battery_gate_tick(void)
{
  if (millis() < next_sample_ms) {
    return;
  }

  next_sample_ms = millis() + SAMPLE_INTERVAL_MS;
  sample_battery();
}
