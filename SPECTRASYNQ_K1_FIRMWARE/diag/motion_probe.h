#pragma once
//
// motion_probe.h — apparent-motion perceptual test harness. NON-SHIPPING,
// compile-gated instrumentation ONLY (ENABLE_MOTION_PROBE).
//
// Purpose
// -------
// Drive the K1 LED strip with controlled spatio-temporal stimuli so the
// apparent-motion / phi-phenomenon thresholds of the physical lamp can be
// measured by eye (and on video) WITHOUT any audio input, WITHOUT touching the
// shipping visual roster, and WITHOUT modifying any light_mode_*.cpp effect.
// Two primitives are provided:
//   * mp_step  — a single bright point that jumps `size_px` pixels every
//                `interval_ms`, wrapping at the strip ends. Measures the
//                smallest jump/interval that still reads as smooth motion.
//   * mp_flash — the classic two-flash apparent-motion stimulus: flash pixel A,
//                go dark for the inter-stimulus interval (ISI), flash pixel B,
//                go dark, repeat. Measures the A↔B separation and ISI at which
//                two flashes fuse into one moving object (beta movement).
//
// Why this is safe (mirrors the gdft_harness.h discipline)
// --------------------------------------------------------
//   * NO shipping effect is edited. The harness draws directly into leds_16[]
//     and reuses the SAME show path the normal render loop calls (show_leds()).
//   * The harness only runs when `mp_active` is true, which is set ONLY by the
//     mp_step / mp_flash serial commands (gated behind ENABLE_MOTION_PROBE in
//     serial_menu.h). With the flag undefined, nothing references this header
//     and every inline definition below costs zero flash (same property as
//     gdft_harness.h — ungated inline, #pragma once, ODR-safe).
//   * On activation the harness SNAPSHOTS the contamination-control CONFIG
//     fields, OVERRIDES them to neutral values, and RESTORES the snapshot on
//     mp_off so normal rendering resumes byte-identically.
//
// Contamination controls (snapshot on activation, restore on mp_off):
//   * CONFIG.TEMPORAL_DITHERING = false  — no sub-frame dither smearing onsets.
//   * CONFIG.INCANDESCENT_MODE  = false  — no warm-bias colour remap.
//   * CONFIG.INCANDESCENT_FILTER = 0     — no incandescent low-pass.
//   * CONFIG.PHOTONS            = 1.0    — unity brightness curve.
//   * silent_scale pinned to 1.0 inside apply_brightness() (led_utilities.h),
//     guarded by `if (mp_active)`, so the silence AGC fade never dims the
//     stimulus. (Pinned at the use site because silent_scale is recomputed
//     elsewhere every frame; see led_utilities.h apply_brightness.)
// The harness draws UN-mirrored across the full NATIVE_RESOLUTION (160) strip
// regardless of CONFIG.MIRROR_ENABLED — it never calls mirror_image_downwards().
//
// Achieved-timing requirement
// ---------------------------
// Stimuli only change on rendered frames (uncapped render loop, ~185 FPS,
// ~5.4 ms/frame, variable). The requested interval/gap/on-time can therefore
// only be honoured to frame granularity. The harness MEASURES the ACHIEVED
// timing (millis() delta between actual onsets) and PRINTS it — that achieved
// value is the experiment's x-axis, NOT the requested value.
//
// Parseable serial output (one line per event):
//   MP step achieved_interval_ms=.. req_interval_ms=.. eff_pps=.. size_px=.. pos=..
//   MP flash achieved_gap_ms=.. on_ms=.. req_gap_ms=.. req_on_ms=.. sep_px=.. pixel=A|B
//
#include <stdint.h>
#include <math.h>
#include <FixedPoints.h>
#include <FixedPointsCommon.h>   // SQ15x16
#include "constants.h"           // NATIVE_RESOLUTION, CRGB16
#include "globals.h"             // leds_16[], CONFIG, silent_scale, USBSerial

// show_leds() is defined in led_utilities.h (included before this header in the
// .ino). Forward-declare so the harness reuses the unmodified canonical show
// path (apply_brightness → incandescent → base-coat → UI → clip → quantise →
// reverse → FastLED.show). Mirrors serial_menu.h's forward-decl pattern.
void show_leds();

// ===========================================================================
// Probe state — file-scope inline globals (ODR-safe under #pragma once).
// ===========================================================================
enum MotionProbeMode : uint8_t {
  MP_MODE_NONE  = 0,
  MP_MODE_STEP  = 1,
  MP_MODE_FLASH = 2,
};

inline bool          mp_active = false;          // led_thread branch checks this
inline MotionProbeMode mp_mode = MP_MODE_NONE;

// --- mp_step parameters / state ---
inline float    mp_step_interval_ms = 100.0f;    // requested jump interval
inline int      mp_step_size_px     = 1;         // requested jump size (>=1)
inline float    mp_step_lum         = 1.0f;      // point luminance (0..1)
inline int      mp_step_pos         = 0;         // current point position
inline uint32_t mp_step_last_onset_ms = 0;       // millis() of last actual jump
inline uint32_t mp_step_achieved_interval_ms = 0;// last MEASURED jump interval (ms)
inline bool     mp_step_seeded = false;          // step params ever configured?

// --- mp_flash parameters / state ---
inline int      mp_flash_a_px   = 0;             // pixel A position
inline int      mp_flash_b_px   = 0;             // pixel B position
inline float    mp_flash_gap_ms = 100.0f;        // requested ISI (dark gap)
inline float    mp_flash_lum    = 1.0f;          // flash luminance (0..1)
inline float    mp_flash_on_ms  = 60.0f;         // requested on-time per flash
// flash phase machine: 0=A on, 1=gap after A, 2=B on, 3=gap after B
inline uint8_t  mp_flash_phase  = 0;
inline uint32_t mp_flash_phase_start_ms = 0;     // millis() phase began
inline uint32_t mp_flash_last_onset_ms  = 0;     // millis() of last A or B onset
inline uint32_t mp_flash_achieved_gap_ms = 0;    // last MEASURED dark gap / ISI (ms)
inline bool     mp_flash_seeded = false;         // flash params ever configured?

// --- contamination-control snapshot (restored on mp_off) ---
inline bool  mp_saved_temporal_dithering  = false;
inline bool  mp_saved_incandescent_mode   = false;
inline float mp_saved_incandescent_filter = 0.0f;
inline float mp_saved_photons             = 1.0f;
inline bool  mp_saved_valid               = false;

// ===========================================================================
// Helpers
// ===========================================================================

// Snapshot + override the contamination-control CONFIG fields. Idempotent: a
// re-arm while already active does NOT re-snapshot (so an mp_off after several
// re-issues still restores the genuine pre-probe values).
inline void motion_probe_snapshot_and_override() {
  if (!mp_saved_valid) {
    mp_saved_temporal_dithering  = CONFIG.TEMPORAL_DITHERING;
    mp_saved_incandescent_mode   = CONFIG.INCANDESCENT_MODE;
    mp_saved_incandescent_filter = CONFIG.INCANDESCENT_FILTER;
    mp_saved_photons             = CONFIG.PHOTONS;
    mp_saved_valid               = true;
  }
  CONFIG.TEMPORAL_DITHERING  = false;
  CONFIG.INCANDESCENT_MODE   = false;
  CONFIG.INCANDESCENT_FILTER = 0.0f;
  CONFIG.PHOTONS             = 1.0f;
  // silent_scale is pinned to 1.0 inside apply_brightness() (led_utilities.h),
  // guarded by `if (mp_active)`, because it is recomputed every frame upstream.
}

// Clear the whole canvas, then light a single pixel at `pos` with luminance
// `lum` (0..1) as a neutral white point. Drawn UN-mirrored (no mirror call).
inline void motion_probe_draw_point(int pos, float lum) {
  for (uint16_t i = 0; i < NATIVE_RESOLUTION; i++) {
    leds_16[i].r = SQ15x16(0.0);
    leds_16[i].g = SQ15x16(0.0);
    leds_16[i].b = SQ15x16(0.0);
  }
  if (pos < 0) pos = 0;
  if (pos >= NATIVE_RESOLUTION) pos = NATIVE_RESOLUTION - 1;
  SQ15x16 v = SQ15x16(lum);
  leds_16[pos] = CRGB16{ v, v, v };
}

// Clear the whole canvas to black (the dark / ISI phase).
inline void motion_probe_draw_dark() {
  for (uint16_t i = 0; i < NATIVE_RESOLUTION; i++) {
    leds_16[i].r = SQ15x16(0.0);
    leds_16[i].g = SQ15x16(0.0);
    leds_16[i].b = SQ15x16(0.0);
  }
}

// ===========================================================================
// Command arming (called from serial_menu.h, gated by ENABLE_MOTION_PROBE)
// ===========================================================================

// Arm / re-arm the single-point step probe. Live-adjustable: re-issuing while
// active updates the parameters without resetting the contamination snapshot.
inline void motion_probe_arm_step(float interval_ms, int size_px, float lum) {
  if (interval_ms < 1.0f) interval_ms = 1.0f;
  if (size_px < 1)        size_px = 1;
  if (lum < 0.0f) lum = 0.0f;
  if (lum > 1.0f) lum = 1.0f;

  bool was_step = (mp_active && mp_mode == MP_MODE_STEP);
  mp_step_interval_ms = interval_ms;
  mp_step_size_px     = size_px;
  mp_step_lum         = lum;
  mp_step_seeded      = true;
  if (!was_step) {
    mp_step_pos = 0;            // fresh run starts at the left end
  }
  mp_step_last_onset_ms = millis();

  motion_probe_snapshot_and_override();
  mp_mode   = MP_MODE_STEP;
  mp_active = true;

  // Effective rate computed from the REQUESTED interval (the achieved rate is
  // reported per-frame from the measured onset delta in the render branch).
  float eff_pps = (float)size_px / (interval_ms / 1000.0f);
  USBSerial.print("MP step armed req_interval_ms=");
  USBSerial.print(interval_ms, 2);
  USBSerial.print(" size_px=");
  USBSerial.print(size_px);
  USBSerial.print(" lum=");
  USBSerial.print(lum, 3);
  USBSerial.print(" eff_pps=");
  USBSerial.println(eff_pps, 2);
}

// Arm / re-arm the two-flash apparent-motion probe.
inline void motion_probe_arm_flash(int a_px, int b_px, float gap_ms,
                                   float lum, float on_ms) {
  if (a_px < 0) a_px = 0;
  if (a_px >= NATIVE_RESOLUTION) a_px = NATIVE_RESOLUTION - 1;
  if (b_px < 0) b_px = 0;
  if (b_px >= NATIVE_RESOLUTION) b_px = NATIVE_RESOLUTION - 1;
  if (gap_ms < 0.0f) gap_ms = 0.0f;
  if (on_ms  < 1.0f) on_ms  = 1.0f;
  if (lum < 0.0f) lum = 0.0f;
  if (lum > 1.0f) lum = 1.0f;

  mp_flash_a_px   = a_px;
  mp_flash_b_px   = b_px;
  mp_flash_gap_ms = gap_ms;
  mp_flash_lum    = lum;
  mp_flash_on_ms  = on_ms;
  mp_flash_seeded = true;
  mp_flash_phase  = 0;                 // start with A on
  uint32_t now = millis();
  mp_flash_phase_start_ms = now;
  mp_flash_last_onset_ms  = now;

  motion_probe_snapshot_and_override();
  mp_mode   = MP_MODE_FLASH;
  mp_active = true;

  int sep = abs(b_px - a_px);
  USBSerial.print("MP flash armed sep_px=");
  USBSerial.print(sep);
  USBSerial.print(" req_gap_ms=");
  USBSerial.print(gap_ms, 2);
  USBSerial.print(" req_on_ms=");
  USBSerial.print(on_ms, 2);
  USBSerial.print(" lum=");
  USBSerial.println(lum, 3);
}

// Stop the probe and restore the snapshotted CONFIG fields. silent_scale
// un-pins automatically because the apply_brightness guard tests mp_active.
inline void motion_probe_off() {
  if (mp_saved_valid) {
    CONFIG.TEMPORAL_DITHERING  = mp_saved_temporal_dithering;
    CONFIG.INCANDESCENT_MODE   = mp_saved_incandescent_mode;
    CONFIG.INCANDESCENT_FILTER = mp_saved_incandescent_filter;
    CONFIG.PHOTONS             = mp_saved_photons;
    mp_saved_valid = false;
  }
  mp_active = false;
  mp_mode   = MP_MODE_NONE;
  USBSerial.println("MP off — probe stopped, CONFIG restored");
}

// ===========================================================================
// Hotkey support — single-key live control (serial_handle_hotkey, gated)
// ---------------------------------------------------------------------------
// These wrap the arm/adjust maths so the immediate-hotkey path stays a thin
// dispatcher. Re-arming through here reuses the existing arm functions, whose
// contamination snapshot is idempotent (taken once on first arm, restored on
// mp_off), so a hotkey re-arm NEVER re-snapshots stale CONFIG.
// ===========================================================================

// First-use defaults (used only when the relevant mode has never been seeded).
#ifndef MP_HOTKEY_STEP_INTERVAL_MS
#define MP_HOTKEY_STEP_INTERVAL_MS 16.0f
#endif
#ifndef MP_HOTKEY_STEP_SIZE_PX
#define MP_HOTKEY_STEP_SIZE_PX 1
#endif
#ifndef MP_HOTKEY_STEP_LUM
#define MP_HOTKEY_STEP_LUM (160.0f / 255.0f)
#endif
#ifndef MP_HOTKEY_FLASH_A
#define MP_HOTKEY_FLASH_A 80
#endif
#ifndef MP_HOTKEY_FLASH_B
#define MP_HOTKEY_FLASH_B 88
#endif
#ifndef MP_HOTKEY_FLASH_GAP_MS
#define MP_HOTKEY_FLASH_GAP_MS 50.0f
#endif
#ifndef MP_HOTKEY_FLASH_ON_MS
#define MP_HOTKEY_FLASH_ON_MS 30.0f
#endif
#ifndef MP_HOTKEY_FLASH_LUM
#define MP_HOTKEY_FLASH_LUM (160.0f / 255.0f)
#endif

// One parser-friendly state line, including the MEASURED/achieved timing.
inline void motion_probe_hotkey_print_state() {
  if (mp_mode == MP_MODE_STEP) {
    float eff_pps = (mp_step_interval_ms > 0.0f)
                      ? ((float)mp_step_size_px / (mp_step_interval_ms / 1000.0f)) : 0.0f;
    USBSerial.print("MP STEP interval_req_ms=");
    USBSerial.print(mp_step_interval_ms, 1);
    USBSerial.print(" size_px=");
    USBSerial.print(mp_step_size_px);
    USBSerial.print(" eff_pps=");
    USBSerial.print(eff_pps, 1);
    USBSerial.print(" ach_interval_ms=");
    USBSerial.println((float)mp_step_achieved_interval_ms, 1);
  } else if (mp_mode == MP_MODE_FLASH) {
    int sep = abs(mp_flash_b_px - mp_flash_a_px);
    USBSerial.print("MP FLASH a=");
    USBSerial.print(mp_flash_a_px);
    USBSerial.print(" b=");
    USBSerial.print(mp_flash_b_px);
    USBSerial.print(" sep_px=");
    USBSerial.print(sep);
    USBSerial.print(" gap_req_ms=");
    USBSerial.print(mp_flash_gap_ms, 1);
    USBSerial.print(" on_ms=");
    USBSerial.print(mp_flash_on_ms, 1);
    USBSerial.print(" ach_gap_ms=");
    USBSerial.println((float)mp_flash_achieved_gap_ms, 1);
  }
}

// `z` — arm STEP mode using current step params (seeding first-use defaults).
inline void motion_probe_hotkey_arm_step() {
  if (!mp_step_seeded) {
    mp_step_interval_ms = MP_HOTKEY_STEP_INTERVAL_MS;
    mp_step_size_px     = MP_HOTKEY_STEP_SIZE_PX;
    mp_step_lum         = MP_HOTKEY_STEP_LUM;
  }
  motion_probe_arm_step(mp_step_interval_ms, mp_step_size_px, mp_step_lum);
  motion_probe_hotkey_print_state();
}

// `x` — arm FLASH mode using current flash params (seeding first-use defaults).
inline void motion_probe_hotkey_arm_flash() {
  if (!mp_flash_seeded) {
    mp_flash_a_px   = MP_HOTKEY_FLASH_A;
    mp_flash_b_px   = MP_HOTKEY_FLASH_B;
    mp_flash_gap_ms = MP_HOTKEY_FLASH_GAP_MS;
    mp_flash_on_ms  = MP_HOTKEY_FLASH_ON_MS;
    mp_flash_lum    = MP_HOTKEY_FLASH_LUM;
  }
  motion_probe_arm_flash(mp_flash_a_px, mp_flash_b_px, mp_flash_gap_ms,
                         mp_flash_lum, mp_flash_on_ms);
  motion_probe_hotkey_print_state();
}

// Step-size cycle through the fixed ladder {1,2,4,8}. dir<0 = next-smaller,
// dir>0 = next-larger (clamped at the ends).
inline int motion_probe_step_size_cycle(int cur, int dir) {
  static const int ladder[4] = { 1, 2, 4, 8 };
  int idx = 0;
  for (int i = 0; i < 4; i++) {
    if (cur >= ladder[i]) idx = i;   // pick the highest ladder entry <= cur
  }
  idx += (dir > 0) ? 1 : -1;
  if (idx < 0) idx = 0;
  if (idx > 3) idx = 3;
  return ladder[idx];
}

// `v`/`b` — "A knob" −/+ (dir = -1 / +1).
//   STEP  → interval ±4 ms, clamp [4,200], re-arm.
//   FLASH → separation ±4 px (b = 80 + sep, a stays 80), clamp sep [2,78], re-arm.
inline void motion_probe_hotkey_knob_a(int dir) {
  if (!mp_active || mp_mode == MP_MODE_NONE) {
    USBSerial.println("MP: press z (step) or x (flash) first");
    return;
  }
  if (mp_mode == MP_MODE_STEP) {
    float iv = mp_step_interval_ms + (float)(dir * 4);
    if (iv < 4.0f)   iv = 4.0f;
    if (iv > 200.0f) iv = 200.0f;
    motion_probe_arm_step(iv, mp_step_size_px, mp_step_lum);
  } else {  // FLASH
    int sep = abs(mp_flash_b_px - mp_flash_a_px) + (dir * 4);
    if (sep < 2)  sep = 2;
    if (sep > 78) sep = 78;
    motion_probe_arm_flash(80, 80 + sep, mp_flash_gap_ms, mp_flash_lum, mp_flash_on_ms);
  }
  motion_probe_hotkey_print_state();
}

// `n`/`m` — "B knob" −/+ (dir = -1 / +1).
//   STEP  → step size cycle {1,2,4,8} (m=next-larger, n=next-smaller), re-arm.
//   FLASH → gap ±10 ms, clamp [5,400], re-arm.
inline void motion_probe_hotkey_knob_b(int dir) {
  if (!mp_active || mp_mode == MP_MODE_NONE) {
    USBSerial.println("MP: press z (step) or x (flash) first");
    return;
  }
  if (mp_mode == MP_MODE_STEP) {
    int sz = motion_probe_step_size_cycle(mp_step_size_px, dir);
    motion_probe_arm_step(mp_step_interval_ms, sz, mp_step_lum);
  } else {  // FLASH
    float gap = mp_flash_gap_ms + (float)(dir * 10);
    if (gap < 5.0f)   gap = 5.0f;
    if (gap > 400.0f) gap = 400.0f;
    motion_probe_arm_flash(mp_flash_a_px, mp_flash_b_px, gap, mp_flash_lum, mp_flash_on_ms);
  }
  motion_probe_hotkey_print_state();
}

// ===========================================================================
// Per-frame render (called from led_thread, gated by ENABLE_MOTION_PROBE)
// ===========================================================================

// Render ONE probe frame into leds_16[]. Caller (led_thread) then runs the
// normal show path and vTaskDelay(1). Each call updates the stimulus only when
// the requested interval/phase boundary has actually been crossed (measured by
// millis()), and reports the ACHIEVED timing when an onset fires. dt clamps
// mirror the light_mode_waveform_fast idiom but are unused for stimulus timing
// here — onset decisions are made directly on the millis() delta so the
// reported achieved value is the true wall-clock onset interval.
inline void motion_probe_render_frame() {
  uint32_t now = millis();

  if (mp_mode == MP_MODE_STEP) {
    uint32_t since_onset = now - mp_step_last_onset_ms;
    if ((float)since_onset >= mp_step_interval_ms) {
      // ---- ONSET: advance the point and report the ACHIEVED interval ----
      uint32_t achieved = now - mp_step_last_onset_ms;   // measured, not requested
      mp_step_achieved_interval_ms = achieved;           // latch for the hotkey state line
      mp_step_last_onset_ms = now;
      mp_step_pos += mp_step_size_px;
      while (mp_step_pos >= NATIVE_RESOLUTION) mp_step_pos -= NATIVE_RESOLUTION;  // wrap

      float ai = (float)achieved;
      float eff_pps = (ai > 0.0f) ? ((float)mp_step_size_px / (ai / 1000.0f)) : 0.0f;
      USBSerial.print("MP step achieved_interval_ms=");
      USBSerial.print(ai, 1);
      USBSerial.print(" req_interval_ms=");
      USBSerial.print(mp_step_interval_ms, 1);
      USBSerial.print(" eff_pps=");
      USBSerial.print(eff_pps, 1);
      USBSerial.print(" size_px=");
      USBSerial.print(mp_step_size_px);
      USBSerial.print(" pos=");
      USBSerial.println(mp_step_pos);
    }
    // Re-draw the point every frame (cheap, keeps it lit between onsets).
    motion_probe_draw_point(mp_step_pos, mp_step_lum);
    return;
  }

  if (mp_mode == MP_MODE_FLASH) {
    uint32_t in_phase = now - mp_flash_phase_start_ms;
    // Phase machine: 0=A on (on_ms), 1=gap (gap_ms), 2=B on (on_ms), 3=gap.
    switch (mp_flash_phase) {
      case 0: {  // A on
        motion_probe_draw_point(mp_flash_a_px, mp_flash_lum);
        if ((float)in_phase >= mp_flash_on_ms) {
          mp_flash_phase = 1;
          mp_flash_phase_start_ms = now;
        }
        break;
      }
      case 1: {  // gap after A (ISI)
        motion_probe_draw_dark();
        if ((float)in_phase >= mp_flash_gap_ms) {
          // ---- onset of B: report achieved A-side on_ms + gap (ISI) ----
          uint32_t achieved_gap = in_phase;                 // measured dark gap
          mp_flash_achieved_gap_ms = achieved_gap;          // latch for the hotkey state line
          uint32_t achieved_onset = now - mp_flash_last_onset_ms;
          mp_flash_last_onset_ms = now;
          int sep = abs(mp_flash_b_px - mp_flash_a_px);
          USBSerial.print("MP flash achieved_gap_ms=");
          USBSerial.print((float)achieved_gap, 1);
          USBSerial.print(" achieved_cycle_ms=");
          USBSerial.print((float)achieved_onset, 1);
          USBSerial.print(" req_gap_ms=");
          USBSerial.print(mp_flash_gap_ms, 1);
          USBSerial.print(" req_on_ms=");
          USBSerial.print(mp_flash_on_ms, 1);
          USBSerial.print(" sep_px=");
          USBSerial.print(sep);
          USBSerial.println(" pixel=B");
          mp_flash_phase = 2;
          mp_flash_phase_start_ms = now;
        }
        break;
      }
      case 2: {  // B on
        motion_probe_draw_point(mp_flash_b_px, mp_flash_lum);
        if ((float)in_phase >= mp_flash_on_ms) {
          mp_flash_phase = 3;
          mp_flash_phase_start_ms = now;
        }
        break;
      }
      case 3: {  // gap after B (ISI), then loop back to A
        motion_probe_draw_dark();
        if ((float)in_phase >= mp_flash_gap_ms) {
          // ---- onset of next A: report achieved B-side on_ms + gap (ISI) ----
          uint32_t achieved_gap = in_phase;
          mp_flash_achieved_gap_ms = achieved_gap;          // latch for the hotkey state line
          uint32_t achieved_onset = now - mp_flash_last_onset_ms;
          mp_flash_last_onset_ms = now;
          int sep = abs(mp_flash_b_px - mp_flash_a_px);
          USBSerial.print("MP flash achieved_gap_ms=");
          USBSerial.print((float)achieved_gap, 1);
          USBSerial.print(" achieved_cycle_ms=");
          USBSerial.print((float)achieved_onset, 1);
          USBSerial.print(" req_gap_ms=");
          USBSerial.print(mp_flash_gap_ms, 1);
          USBSerial.print(" req_on_ms=");
          USBSerial.print(mp_flash_on_ms, 1);
          USBSerial.print(" sep_px=");
          USBSerial.print(sep);
          USBSerial.println(" pixel=A");
          mp_flash_phase = 0;
          mp_flash_phase_start_ms = now;
        }
        break;
      }
    }
    return;
  }

  // MP_MODE_NONE while mp_active (should not normally happen): hold dark.
  motion_probe_draw_dark();
}

// ===========================================================================
// Status report
// ===========================================================================
inline void motion_probe_status() {
  USBSerial.print("MP status active=");
  USBSerial.print(mp_active ? 1 : 0);
  USBSerial.print(" mode=");
  USBSerial.print(mp_mode == MP_MODE_STEP ? "step"
                : mp_mode == MP_MODE_FLASH ? "flash" : "none");
  // Measured render cadence (the achievable timing floor of the experiment).
  float fps = (float)LED_FPS;
  float frame_ms = (fps > 0.0f) ? (1000.0f / fps) : 0.0f;
  USBSerial.print(" led_fps=");
  USBSerial.print(fps, 1);
  USBSerial.print(" frame_ms=");
  USBSerial.print(frame_ms, 3);

  if (mp_mode == MP_MODE_STEP) {
    USBSerial.print(" req_interval_ms=");
    USBSerial.print(mp_step_interval_ms, 1);
    USBSerial.print(" size_px=");
    USBSerial.print(mp_step_size_px);
    USBSerial.print(" pos=");
    USBSerial.print(mp_step_pos);
    USBSerial.print(" last_achieved_onset_age_ms=");
    USBSerial.print((float)(millis() - mp_step_last_onset_ms), 1);
  } else if (mp_mode == MP_MODE_FLASH) {
    int sep = abs(mp_flash_b_px - mp_flash_a_px);
    USBSerial.print(" sep_px=");
    USBSerial.print(sep);
    USBSerial.print(" req_gap_ms=");
    USBSerial.print(mp_flash_gap_ms, 1);
    USBSerial.print(" req_on_ms=");
    USBSerial.print(mp_flash_on_ms, 1);
    USBSerial.print(" phase=");
    USBSerial.print(mp_flash_phase);
  }
  USBSerial.println("");
}
