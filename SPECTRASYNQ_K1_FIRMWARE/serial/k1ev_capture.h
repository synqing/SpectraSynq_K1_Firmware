#pragma once
// ─────────────────────────────────────────────────────────────────────────────
// Mode-A `[K1EV]` BUFFERED telemetry capture  (K1 Offline Analysis Pairing).
// Contract: k1-analysis-harness/capture/CAPTURE_CONTRACT.md v0.2.
//
// Supersedes the live per-frame emit in serial/k1ev_stream.h. That tap formatted
// and wrote ~200 chars over USBSerial EVERY audio frame from the loop() post-tempo
// call site, which perturbed the very pipeline it measures (measured active_p95
// 8448 us against a 7500 us budget; the shipping DSP already sits ~7040 us p95).
//
// This unit instead APPENDS a compact fixed-point struct per frame (sub-us, no
// printf, no USB) into a PSRAM ring, then formats + emits the WHOLE run AFTER it,
// off the hot path — exactly like ap_nov_capture / ap_cad_capture. The dump
// reproduces the FROZEN `[K1EV]` wire format byte-for-byte (see k1ev_capture.cpp),
// so capture/parse_capture.py is unchanged.
//
// ADDITIVE + gated: nothing here compiles unless ENABLE_K1EV_STREAM is defined
// (only [env:k1_bench_ap_frontend_probe]); k1_prod_im73d / k1_hardware stay
// byte-identical.
//
// Field notes (see CAPTURE_CONTRACT.md §v0.2 / k1ev_stream.h history):
//  * t_ms   = snap.frame_ms  — FRESH every frame (NOT event.event_ms, stale between
//             onsets; carried separately as event_ms).
//  * beat=  = tempo beat_tick (k1_tempo_read), NOT the onset event's beat flag.
//  * croot / chroma are A-ORIGIN (bin 0 = A); the harness rotates +9 to C-origin.
//  * croot  = -1 synthesised when chord.type == NONE (0 would collide with A).
//  * ctype  enum: 0=NONE,1=MAJOR,2=MINOR,3=DIMINISHED,4=AUGMENTED.
// ─────────────────────────────────────────────────────────────────────────────
#ifdef ENABLE_K1EV_STREAM
#include <stdint.h>
#include "k1_audio_snapshot.h"   // K1AudioSnapshot, K1OnsetBeatEvent, K1ChordType, K1_CHROMA_PC_BINS

#ifndef K1EV_STREAM_DECIMATE
#define K1EV_STREAM_DECIMATE 3   // heavy (chroma) sample cadence: every Nth in-window
#endif                           // frame. 3 -> 44.4 Hz at the 133 Hz AP rate. Onset
                                 // frames ALWAYS append (chroma optional to the parser).
#ifndef K1EV_CAPTURE_CAPACITY
#define K1EV_CAPTURE_CAPACITY 65536   // 65536 * 64 B = 4 MiB PSRAM (of 8 MiB N16R8). Sized for
#endif                                // the longest corpus track (Sgadi Li Mi 300.6 s) at the
                                      // MEASURED 107 samples/s (48,231 w/ 1.5 safety) AND the
                                      // absolute every-frame-@133Hz worst case (60,118) -> both
                                      // < 65,536. 32,768 (2 MiB) overflowed both. Alloc fails
                                      // safe (arm returns false) if 4 MiB PSRAM is unavailable.
#ifndef K1EV_CAPTURE_MAX_MS
#define K1EV_CAPTURE_MAX_MS 180000UL  // mirror AP_NOV_CAPTURE_MAX_MS (the piggyback arm
#endif                                // duration comes straight from nov_capture=<ms>).

// Compact per-frame record (64 B, naturally aligned; sizeof == 64 — static_assert'd
// in the .cpp). Floats are scaled to int16 with a saturating helper and re-expanded
// in the dump to the exact %.3f/%.1f the live emit produced (round(x*S)/S == %.Nf(x)).
// photons is stored full-precision (float) because the director scalar has no bounded
// range, so a fixed 16-bit scale would risk overflow / clipping.
struct K1EVCaptureSample {
  uint32_t t_ms;            // snap.frame_ms                (always)
  uint32_t event_ms;        // ev.event_ms                  (always)
  uint32_t event_id;        // ev.event_id                  (always)
  uint32_t kick_event_id;   // ev.kick_event_id             (always)
  uint32_t snare_event_id;  // ev.snare_event_id            (always)
  uint32_t hihat_event_id;  // ev.hihat_event_id            (always)
  float    photons;         // photons_scalar (%.3f)        (sample frame)
  int16_t  bphase_q;        // phase01           * 1000 (%.3f)  (always)
  int16_t  bconf_q;         // confidence        * 1000 (%.3f)  (always)
  int16_t  bpm_q10;         // bpm               * 10   (%.1f)  (always)
  int16_t  cconf_q;         // chord.confidence  * 1000 (%.3f)  (sample frame)
  int16_t  chroma_q[12];    // chroma_pc[c]      * 1000 (%.3f)  (sample frame)
  uint8_t  flags;           // b0 onset|b1 bass|b2 kick|b3 snare|b4 hihat|b5 beat_tick|b6 has_chroma
  int8_t   croot;           // A-origin root; -1 on NONE        (sample frame)
  uint8_t  ctype;           // 0=NONE..4=AUG                    (sample frame)
  uint8_t  mode;            // applied_mode                     (sample frame)
};

// State (external linkage; defined in k1ev_capture.cpp). Shared between the loop()
// tick call site (.ino) and the arm/dump piggyback in k1_ap_capture_telemetry.cpp.
extern K1EVCaptureSample* K1EV_CAPTURE_BUFFER;
extern uint32_t K1EV_CAPTURE_COUNT;
extern uint32_t K1EV_CAPTURE_DROPPED;
extern uint32_t K1EV_CAPTURE_FRAME_N;
extern uint32_t K1EV_CAPTURE_START_MS;
extern uint32_t K1EV_CAPTURE_END_MS;
extern bool     K1EV_CAPTURE_ACTIVE;
extern bool     K1EV_CAPTURE_ALLOC_FAILED;

bool k1ev_capture_ensure_buffer();                 // lazy PSRAM alloc (internal fallback)
bool k1ev_capture_arm(uint32_t duration_ms);       // reset + window; piggybacked by nov arm
void k1ev_capture_tick(const K1AudioSnapshot& snap, const K1OnsetBeatEvent& ev);  // hot path: append only
void k1ev_capture_dump();                          // off hot path; piggybacked by nov dump

#endif  // ENABLE_K1EV_STREAM
