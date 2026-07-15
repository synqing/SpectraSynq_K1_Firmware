/*----------------------------------------
  K1 `[K1EV]` BUFFERED telemetry capture — implementation
  ----------------------------------------
  Mode-A read-only analysis tap, buffered edition. Supersedes the live per-frame
  emit in serial/k1ev_stream.h (see that header + k1ev_capture.h for the WHY: the
  live USBSerial write per frame perturbed the pipeline it measures).

  The whole unit is gated on ENABLE_K1EV_STREAM, defined ONLY in the non-shippable
  [env:k1_bench_ap_frontend_probe]. As with k1_ap_capture_telemetry.cpp, the gate
  is applied FIRST — BEFORE any #include — so that in production (k1_hardware /
  k1_prod_im73d) this TU preprocesses to NOTHING: no header pull-in, no globals,
  no static-initialiser ctor, hence zero bytes added to the release link (the
  binary stays byte-identical).
*/

#ifdef ENABLE_K1EV_STREAM

#include "k1ev_capture.h"
#include "globals.h"             // USBSerial, millis, vTaskDelay (Arduino/FreeRTOS)
#include "k1_tempo.h"            // K1TempoEvent, k1_tempo_read()
#include "k1_mode_selection.h"   // k1_mode_selection_read_state()
#include "k1_smart_director.h"   // k1_smart_director_read_output()
#include <esp_heap_caps.h>       // heap_caps_malloc / MALLOC_CAP_SPIRAM
#include <math.h>                // lroundf, isfinite

// One record is exactly 64 B; assert it so the PSRAM budget claim can't silently
// drift, and pin the chroma width to the pitch-class bin count.
static_assert(sizeof(K1EVCaptureSample) == 64, "K1EVCaptureSample must stay 64 B");
static_assert(K1_CHROMA_PC_BINS == 12, "dump chroma loop assumes 12 pitch-class bins");

// ---- State (external linkage) ----------------------------------------------
K1EVCaptureSample* K1EV_CAPTURE_BUFFER = nullptr;
uint32_t K1EV_CAPTURE_COUNT = 0;
uint32_t K1EV_CAPTURE_DROPPED = 0;
uint32_t K1EV_CAPTURE_FRAME_N = 0;
uint32_t K1EV_CAPTURE_START_MS = 0;
uint32_t K1EV_CAPTURE_END_MS = 0;
bool     K1EV_CAPTURE_ACTIVE = false;
bool     K1EV_CAPTURE_ALLOC_FAILED = false;

// Saturating fixed-point quantiser (semantics of ap_capture_i16_sat, kept local so
// this TU stays independent of the ENABLE_AP_FRONTEND_DEBUG gate). round(v*scale)
// then clamp to int16 — re-expanded /scale it reproduces the exact %.Nf the live
// emit printed for the bounded fields (phase01/confidence 0..1, bpm to 0.1).
static inline int16_t k1ev_i16_scale(float v, float scale) {
  if (!isfinite(v)) {
    return 0;
  }
  long q = lroundf(v * scale);
  if (q > 32767L) return 32767;
  if (q < -32768L) return -32768;
  return (int16_t)q;
}

bool k1ev_capture_ensure_buffer() {
  K1EV_CAPTURE_ALLOC_FAILED = false;
  if (K1EV_CAPTURE_BUFFER != nullptr) {
    return true;
  }
  K1EV_CAPTURE_BUFFER = (K1EVCaptureSample*)heap_caps_malloc(
    sizeof(K1EVCaptureSample) * (size_t)K1EV_CAPTURE_CAPACITY,
    MALLOC_CAP_SPIRAM | MALLOC_CAP_8BIT);
  if (K1EV_CAPTURE_BUFFER == nullptr) {
    // Internal fallback (2 MiB will not fit internal RAM; this just yields a clean
    // null -> alloc_failed -> arm returns false, never a crash). Mirrors ap_cad.
    K1EV_CAPTURE_BUFFER = (K1EVCaptureSample*)heap_caps_malloc(
      sizeof(K1EVCaptureSample) * (size_t)K1EV_CAPTURE_CAPACITY,
      MALLOC_CAP_8BIT);
  }
  K1EV_CAPTURE_ALLOC_FAILED = (K1EV_CAPTURE_BUFFER == nullptr);
  return !K1EV_CAPTURE_ALLOC_FAILED;
}

bool k1ev_capture_arm(uint32_t duration_ms) {
  if (duration_ms == 0 || duration_ms > K1EV_CAPTURE_MAX_MS) {
    return false;
  }
  if (!k1ev_capture_ensure_buffer()) {
    return false;
  }
  K1EV_CAPTURE_COUNT = 0;
  K1EV_CAPTURE_DROPPED = 0;
  K1EV_CAPTURE_FRAME_N = 0;
  K1EV_CAPTURE_START_MS = millis();
  K1EV_CAPTURE_END_MS = K1EV_CAPTURE_START_MS + duration_ms;
  K1EV_CAPTURE_ACTIVE = true;
  return true;
}

// Hot path. Runs once per audio frame from loop() (post k1_tempo_update). MUST be
// minimal: append a struct, no printf, no USB. Append rule mirrors the retired
// k1ev_stream.h::k1ev_emit — append on any onset/beat frame OR every K1EV_STREAM_DECIMATE
// sample frame; heavy chroma/chord/mode/photons only on sample frames (has_chroma).
void k1ev_capture_tick(const K1AudioSnapshot& snap, const K1OnsetBeatEvent& ev) {
  if (!K1EV_CAPTURE_ACTIVE) {
    return;
  }
  // snap.frame_ms is the same millis()-domain clock ap_cad compares against.
  if ((int32_t)(snap.frame_ms - K1EV_CAPTURE_END_MS) >= 0) {
    K1EV_CAPTURE_ACTIVE = false;
    return;
  }

  const bool onset_frame  = ev.onset || ev.bass_onset || ev.kick || ev.snare || ev.hihat || ev.beat;
  const bool sample_frame = ((K1EV_CAPTURE_FRAME_N++) % (uint32_t)K1EV_STREAM_DECIMATE) == 0;
  if (!onset_frame && !sample_frame) {
    return;
  }
  if (K1EV_CAPTURE_BUFFER == nullptr || K1EV_CAPTURE_COUNT >= (uint32_t)K1EV_CAPTURE_CAPACITY) {
    K1EV_CAPTURE_DROPPED++;
    return;
  }

  const K1TempoEvent tev = k1_tempo_read();   // fresh: post k1_tempo_update
  K1EVCaptureSample& s = K1EV_CAPTURE_BUFFER[K1EV_CAPTURE_COUNT++];

  // Always-present prefix fields.
  s.t_ms = snap.frame_ms;
  s.event_ms = ev.event_ms;
  s.event_id = ev.event_id;
  s.kick_event_id = ev.kick_event_id;
  s.snare_event_id = ev.snare_event_id;
  s.hihat_event_id = ev.hihat_event_id;
  s.bphase_q = k1ev_i16_scale(tev.phase01, 1000.0f);
  s.bconf_q  = k1ev_i16_scale(tev.confidence, 1000.0f);
  s.bpm_q10  = k1ev_i16_scale(tev.bpm, 10.0f);

  uint8_t flags = 0;
  if (ev.onset)      flags |= 0x01;
  if (ev.bass_onset) flags |= 0x02;
  if (ev.kick)       flags |= 0x04;
  if (ev.snare)      flags |= 0x08;
  if (ev.hihat)      flags |= 0x10;
  if (tev.beat_tick) flags |= 0x20;   // printed as beat=  (tempo tick, not ev.beat)

  if (sample_frame) {
    flags |= 0x40;                     // has_chroma
    const bool have_chord = (snap.chord.type != K1ChordType::NONE);
    s.croot = have_chord ? (int8_t)snap.chord.rootNote : (int8_t)-1;
    s.ctype = (uint8_t)snap.chord.type;
    s.cconf_q = k1ev_i16_scale(snap.chord.confidence, 1000.0f);
    for (int c = 0; c < K1_CHROMA_PC_BINS; c++) {
      s.chroma_q[c] = k1ev_i16_scale(snap.chroma_pc[c], 1000.0f);
    }
    s.mode = k1_mode_selection_read_state().applied_mode;
    s.photons = k1_smart_director_read_output().photons_scalar;
  }
  // On onset-only frames the heavy fields are intentionally left unwritten (kept
  // minimal); the dump reads them ONLY when the has_chroma bit is set.
  s.flags = flags;
}

// Off the hot path. Piggybacked from the START of ap_nov_capture_dump() so this
// whole block lands BEFORE the NOV_CAPTURE_DONE marker the capture tool's
// read_until_done() stops on (device_novelty_buffer_capture.py) — the unmodified
// --capture-ap-stream flow therefore captures it with no tool edits. Reproduces the
// FROZEN [K1EV] wire format byte-for-byte so capture/parse_capture.py is unchanged.
void k1ev_capture_dump() {
  K1EV_CAPTURE_ACTIVE = false;
  USBSerial.print("K1EV_CAPTURE_BEGIN,count=");
  USBSerial.print(K1EV_CAPTURE_COUNT);
  USBSerial.print(",capacity=");
  USBSerial.print((uint32_t)K1EV_CAPTURE_CAPACITY);
  USBSerial.print(",dropped=");
  USBSerial.println(K1EV_CAPTURE_DROPPED);

  char b[384];
  for (uint32_t i = 0; i < K1EV_CAPTURE_COUNT; i++) {
    const K1EVCaptureSample& s = K1EV_CAPTURE_BUFFER[i];
    const bool onset = (s.flags & 0x01) != 0;
    const bool bass  = (s.flags & 0x02) != 0;
    const bool kick  = (s.flags & 0x04) != 0;
    const bool snare = (s.flags & 0x08) != 0;
    const bool hihat = (s.flags & 0x10) != 0;
    const bool beat  = (s.flags & 0x20) != 0;

    int p = snprintf(b, sizeof(b),
      "[K1EV] t_ms=%lu event_ms=%lu ev=%lu onset=%d bass=%d kick=%d snare=%d hihat=%d "
      "kid=%lu sid=%lu hid=%lu beat=%d bphase=%.3f bconf=%.3f bpm=%.1f",
      (unsigned long)s.t_ms, (unsigned long)s.event_ms, (unsigned long)s.event_id,
      onset ? 1 : 0, bass ? 1 : 0, kick ? 1 : 0, snare ? 1 : 0, hihat ? 1 : 0,
      (unsigned long)s.kick_event_id, (unsigned long)s.snare_event_id, (unsigned long)s.hihat_event_id,
      beat ? 1 : 0,
      (double)s.bphase_q / 1000.0, (double)s.bconf_q / 1000.0, (double)s.bpm_q10 / 10.0);

    if (s.flags & 0x40) {   // has_chroma: heavy fields present (sample frame)
      p += snprintf(b + p, sizeof(b) - p, " croot=%d ctype=%d cconf=%.3f chroma=",
                    (int)s.croot, (int)s.ctype, (double)s.cconf_q / 1000.0);
      for (int c = 0; c < K1_CHROMA_PC_BINS && p < (int)sizeof(b) - 12; c++) {
        p += snprintf(b + p, sizeof(b) - p, c ? ";%.3f" : "%.3f", (double)s.chroma_q[c] / 1000.0);
      }
      p += snprintf(b + p, sizeof(b) - p, " mode=%u photons=%.3f", (unsigned)s.mode, (double)s.photons);
    }
    if (p < (int)sizeof(b) - 1) {
      b[p++] = '\n';
    }
    USBSerial.write((const uint8_t*)b, (size_t)p);
    if ((i & 0x3F) == 0x3F) {   // yield every 64 lines (buffer holds up to 32768)
      vTaskDelay(1);
    }
  }

  USBSerial.print("K1EV_CAPTURE_DONE,count=");
  USBSerial.print(K1EV_CAPTURE_COUNT);
  USBSerial.print(",dropped=");
  USBSerial.println(K1EV_CAPTURE_DROPPED);
}

#endif  // ENABLE_K1EV_STREAM
