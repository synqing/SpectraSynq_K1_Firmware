#pragma once

#include <stdint.h>

enum K1MusicState : uint8_t {
  K1_MUSIC_SILENCE = 0,
  K1_MUSIC_AMBIENT,
  K1_MUSIC_STEADY,
  K1_MUSIC_BUILD,
  K1_MUSIC_DROP,
  K1_MUSIC_BREAKDOWN,
  K1_MUSIC_DENSE
};

#ifdef K1_ONSET_V2
// V2 onset front-end runs a donor-shaped log-spectral-flux detector over the
// fork's per-note spectrogram. The detector needs the per-bin spectrum, not just
// the 3 scalar band energies, so the snapshot carries it ONLY in the V2 build.
// Kept independent of NUM_FREQS so the snapshot header stays self-contained
// (stdint-only); a static_assert in k1_audio_snapshot.cpp pins this to NUM_FREQS.
#define K1_ONSET_SPECTRUM_BINS 80
#endif

#ifdef K1_CHORD_V2
// Pitch-class-aligned 12-bin chroma. The fork GDFT note table (constants.h
// notes[], A1=55 Hz, exactly semitone-spaced) means folding the per-note
// spectrogram by (bin % 12) is a pitch-class fold. The snapshot fold is
// Nyquist-clamped by the runtime sample rate and NOTE_OFFSET in
// k1_audio_snapshot.cpp.
// Bin 0 of THIS vector is the pitch class of note index 0 = A (55 Hz). The
// donor ChordState rootNote convention is C=0; the +3/+4/+6/+7/+8 interval
// arithmetic is rotation-invariant (modulo 12), so detectChord works correctly
// on an A-origin chroma — only the absolute rootNote label is rotated by +9
// vs. a C-origin chroma. detectChord here therefore reports rootNote in
// "A-origin" pitch-class units (0 = A). Additive: present only under
// K1_CHORD_V2 so the production struct stays byte-identical.
#define K1_CHROMA_PC_BINS 12

enum class K1ChordType : uint8_t {
  NONE = 0,        // no chord / insufficient confidence
  MAJOR = 1,       // root + major 3rd (+4) + perfect 5th (+7)
  MINOR = 2,       // root + minor 3rd (+3) + perfect 5th (+7)
  DIMINISHED = 3,  // root + minor 3rd (+3) + diminished 5th (+6)
  AUGMENTED = 4    // root + major 3rd (+4) + augmented 5th (+8)
};

struct K1ChordState {
  uint8_t rootNote = 0;                       // 0-11 pitch class (A-origin: 0 = A)
  K1ChordType type = K1ChordType::NONE;
  float confidence = 0.0f;                    // 0..1 triad energy ratio
  float rootStrength = 0.0f;
  float thirdStrength = 0.0f;
  float fifthStrength = 0.0f;
};
#endif

struct K1AudioSnapshot {
  uint32_t frame_ms;
  float peak_scaled;
  float vu_level;
  float novelty;
  float spectral_energy;
  float low_energy;
  float mid_energy;
  float high_energy;
  float chroma_strength;
  bool silence;
#ifdef K1_ONSET_V2
  // Exclusive high bin whose runtime target frequency is valid for the current
  // sample-rate Nyquist limit. The producer derives this from CONFIG.SAMPLE_RATE,
  // CONFIG.NOTE_OFFSET, and constants.h notes[].
  uint8_t nyquist_safe_bin_hi;
  // Per-note magnitude spectrum (runtime bin i -> notes[i + NOTE_OFFSET]),
  // post-AGC, [0,1]-clamped. Additive: present only under K1_ONSET_V2 so the
  // no-flag struct is byte-identical.
  float spectrum[K1_ONSET_SPECTRUM_BINS];
#endif
#ifdef K1_CHORD_V2
  // Pitch-class-aligned 12-bin chroma (A-origin) and the triad detected from it.
  // Additive: present only under K1_CHORD_V2.
  float chroma_pc[K1_CHROMA_PC_BINS];
  K1ChordState chord;
#endif
};

struct K1OnsetBeatEvent {
  uint32_t event_id;
  uint32_t event_ms;
  uint32_t event_age_ms;
  float onset_strength;
  float bass_onset_strength;
  float beat_phase;
  float beat_confidence;
  bool onset;
  bool bass_onset;
  bool beat;
#ifdef K1_ONSET_V2
  // Additive semantic channels (V2 only). k1_tempo still owns beat/downbeat;
  // these carry percussive onset semantics. Each: fired (this frame), strength
  // ([0,1] thresholded envelope), held (decaying level for trails), and a
  // monotonic per-channel event id so consumers can dedupe on a fresh hit.
  bool  transient;
  bool  kick;
  bool  snare;
  bool  hihat;
  float transient_strength;
  float kick_strength;
  float snare_strength;
  float hihat_strength;
  float transient_level;
  float kick_level;
  float snare_level;
  float hihat_level;
  uint32_t transient_event_id;
  uint32_t kick_event_id;
  uint32_t snare_event_id;
  uint32_t hihat_event_id;
#endif
};

void k1_audio_snapshot_update(uint32_t frame_ms);
K1AudioSnapshot k1_audio_snapshot_read();

#ifdef K1_CHORD_V2
// Triad detection ported from donor ControlBus::detectChord (ControlBus.cpp:796).
// Operates on a 12-bin pitch-class chroma: dominant pitch class = root, then the
// strongest of +3/+4 (third) and +6/+7/+8 (fifth) classifies the triad;
// confidence = clamp01((root+third+fifth energy / total energy) / 0.4). Pure /
// stateless / no Arduino deps so it is host-unit-testable in isolation.
void k1_detect_chord(const float* chroma_pc, K1ChordState& out);
#endif
