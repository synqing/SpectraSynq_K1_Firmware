#pragma once

// ============================================================================
// k1_stm.h — K1 spectral-temporal modulation (STM) producer (K1_STM, additive)
// ============================================================================
//
// RE-DERIVATION, NOT A TRANSPLANT. The donor LightwaveOS STM (STMExtractor) runs
// on `bins256` — a 256-magnitude linear FFT taken from a 512-point real FFT over
// raw PCM history. On the Goertzel-only backend the donor ZEROES bins256 and sets
// stmReady=false (donor AudioActor.cpp:795-801). K1 is Goertzel-only and has no
// 512-pt raw-PCM FFT, so a faithful transplant is impossible. This producer
// re-derives the SAME two STM semantics from the signal K1 has every AP frame:
// the 80-note post-AGC `spectrogram[]` (system/globals.h). That spectrogram is
// already a uniform LOG-frequency axis (semitone-spaced from A1=55 Hz), so both
// STM axes reduce to a Goertzel over a bounded buffer — temporal over time,
// spectral over frequency — with no mel warp, no FFT, no heap, no big tables.
//
// Rate adaptation (donor 125 Hz / 64-bin -> K1 133.33 Hz / 80-bin), full
// derivation in docs/forensics/stm-producer/STM_REDERIVATION_DESIGN.md:
//   - temporal window   16 frames (128 ms @125 Hz) -> 17 frames (127.5 ms @133.33 Hz)
//   - temporal 4 Hz probe coeff  2cos(2pi*4/125) -> 2cos(2pi*4/133.333)
//   - spectral ripple bins       42 (=6cyc/oct*7oct) -> 40 (=NUM_FREQS/2, Nyquist)
//   - attack/release EMA retuned from the donor 50 Hz reference to 133.33 Hz
//
// DOCTRINE (k1_semantic_state.h "named, reasoned, absent"):
//   - Compiled only under K1_STM; the no-flag production struct is byte-identical.
//   - During warm-up and silence the producer emits ready=false with ZEROED
//     outputs — never a fabricated 0 that a consumer could mistake for a real
//     measurement.
//   - The per-band temporal history and per-frame mel envelope are PRIVATE to the
//     .cpp; only what a consumer reads is published (two energy scalars + the
//     ripple vector). Nothing unread is exposed.
//
// HARD-RT CONTRACT (Core-0 audio hot path):
//   - No new/malloc/String, no Arduino types, no blocking calls, no portMAX_DELAY.
//   - ~1.5 KB static state; <=512 B stack; pure floating-point.
//   - British English throughout.
//
// EdgeMixer mapping (consumer wired at convergence, NOT in this lane): the fork's
// snake_case fields map to the donor camelCase the EdgeMixer expects —
//   stm.temporal_energy -> stmTemporalEnergy   (STM_DUAL strip 1)
//   stm.spectral_energy -> stmSpectralEnergy   (STM_DUAL strip 2)
//   stm.spectral[0..39] -> stmSpectral[0..39]  (STM_SPECTRAL_MAP; regenerate the
//                                               kLedToStmBin LUT for 40 bins)
//   stm.ready           -> stmReady
// ============================================================================

#include <stdint.h>

#ifdef K1_STM

// Nyquist-honest ripple-bin count for an 80-sample frequency axis (NUM_FREQS/2).
// spectral[j] carries ripple cycle k=(j+1) across the log-frequency axis:
// j=0 is the coarsest ripple (1 cycle over the whole spectrum), j=39 the finest.
#define K1_STM_SPECTRAL_BINS 40

// Upper bound on the input spectrum width the producer will process (K1 NUM_FREQS
// is 80). Keeps the TU self-contained (no NUM_FREQS include). num_bins beyond this
// is defensively clamped.
#define K1_STM_MAX_BINS 128

// Published STM result. POD, trivially copyable, embedded in K1AudioSnapshot.
struct K1StmResult {
  bool  ready;             // false during the 17-frame warm-up (outputs are zero)
  float temporal_energy;   // [0,1] mean 4 Hz temporal-shape modulation across bands
  float spectral_energy;   // [0,1] mean spectral-ripple modulation
  float spectral[K1_STM_SPECTRAL_BINS];  // [0,1] per ripple cycle, coarse..fine
};

// Process one AP frame's per-note magnitude spectrum. `spectrum` is num_bins wide,
// non-negative, ~[0,1] (post-AGC). `silence` treats the frame as zero-energy.
// Stateful (internal ring history + attack/release EMA); call exactly once per AP
// frame from the Core-0 producer. Safe on the audio hot path.
void k1_stm_process(const float* spectrum, uint8_t num_bins, bool silence, K1StmResult* out);

// Clear all internal STM state (history, warm-up counter, EMA). For test isolation
// and cold-start; not needed in normal firmware flow.
void k1_stm_reset();

#endif  // K1_STM
