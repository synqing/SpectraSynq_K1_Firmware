#pragma once
// ─────────────────────────────────────────────────────────────────────────────
// Mode-A `[K1EV]` read-only telemetry tap  (K1 Offline Analysis Pairing).
// Contract: k1-analysis-harness/capture/CAPTURE_CONTRACT.md v0.2.
//
// Emits ONE `[K1EV]` line per audio frame over USB-serial from the loop() post-tempo
// call site. ADDITIVE + READ-ONLY: it only reads already-computed snapshot/onset/tempo/
// director state and prints — no DSP, effect, render, or state mutation. It #ifdefs to
// nothing unless ENABLE_K1EV_STREAM is defined (only [env:k1_bench_ap_frontend_probe]),
// so k1_prod_im73d / k1_hardware / k1_bench_im73d stay byte-identical.
//
// Field notes (see CAPTURE_CONTRACT.md §v0.2):
//  * t_ms   = snap.frame_ms  — FRESH every frame (NOT event.event_ms, which is stale
//             between onsets; that is carried separately as event_ms).
//  * croot / chroma are A-ORIGIN (bin 0 = A); the harness rotates +9 to C-origin.
//  * croot  = -1 synthesised when chord.type == NONE (0 would collide with a real A chord).
//  * ctype  enum: 0=NONE,1=MAJOR,2=MINOR,3=DIMINISHED,4=AUGMENTED.
// ─────────────────────────────────────────────────────────────────────────────
#ifdef ENABLE_K1EV_STREAM
#include <Arduino.h>
#include "k1_audio_snapshot.h"   // K1AudioSnapshot, K1OnsetBeatEvent, K1ChordType, K1_CHROMA_PC_BINS
#include "k1_tempo.h"            // K1TempoEvent, k1_tempo_read()
#include "k1_mode_selection.h"   // K1ModeSelectionState, k1_mode_selection_read_state()
#include "k1_smart_director.h"   // K1SmartDirectorOutput, k1_smart_director_read_output()

#ifndef K1EV_STREAM_DECIMATE
#define K1EV_STREAM_DECIMATE 1   // emit every Nth frame (1 = every 7.5 ms frame)
#endif

static inline void k1ev_emit(const K1AudioSnapshot& snap, const K1OnsetBeatEvent& ev) {
  static uint32_t k1ev_frame_n = 0;
  if ((k1ev_frame_n++ % (uint32_t)K1EV_STREAM_DECIMATE) != 0) {
    return;
  }

  const K1TempoEvent tev  = k1_tempo_read();                                // fresh: post k1_tempo_update
  const uint8_t      mode = k1_mode_selection_read_state().applied_mode;    // director/k1_mode_selection.h
  const float        phot = k1_smart_director_read_output().photons_scalar;  // director/k1_smart_director.h

  const bool have_chord = (snap.chord.type != K1ChordType::NONE);
  const int  croot      = have_chord ? (int)snap.chord.rootNote : -1;        // A-origin (0 = A)
  const int  ctype      = (int)snap.chord.type;                             // 0=NONE..4=AUG

  USBSerial.printf(
    "[K1EV] t_ms=%lu event_ms=%lu ev=%lu onset=%d bass=%d kick=%d snare=%d hihat=%d "
    "kid=%lu sid=%lu hid=%lu beat=%d bphase=%.3f bconf=%.3f bpm=%.1f "
    "croot=%d ctype=%d cconf=%.3f chroma=",
    (unsigned long)snap.frame_ms,          // t_ms     — frame clock, fresh every frame
    (unsigned long)ev.event_ms,            // event_ms — last onset-accept stamp (stale between onsets)
    (unsigned long)ev.event_id,            // ev
    ev.onset ? 1 : 0,                      // onset
    ev.bass_onset ? 1 : 0,                 // bass
    ev.kick ? 1 : 0,                       // kick   (K1_ONSET_V2)
    ev.snare ? 1 : 0,                      // snare  (K1_ONSET_V2)
    ev.hihat ? 1 : 0,                      // hihat  (K1_ONSET_V2)
    (unsigned long)ev.kick_event_id,       // kid
    (unsigned long)ev.snare_event_id,      // sid
    (unsigned long)ev.hihat_event_id,      // hid
    tev.beat_tick ? 1 : 0,                 // beat
    (double)tev.phase01,                   // bphase
    (double)tev.confidence,                // bconf
    (double)tev.bpm,                       // bpm
    croot, ctype,                          // croot / ctype (A-origin; -1 on NONE)
    (double)snap.chord.confidence);        // cconf
  for (uint8_t c = 0; c < K1_CHROMA_PC_BINS; c++) {   // chroma_pc[12], A-origin
    USBSerial.printf(c ? ";%.3f" : "%.3f", (double)snap.chroma_pc[c]);
  }
  USBSerial.printf(" mode=%u photons=%.3f", (unsigned)mode, (double)phot);
  USBSerial.println();
}
#endif  // ENABLE_K1EV_STREAM
