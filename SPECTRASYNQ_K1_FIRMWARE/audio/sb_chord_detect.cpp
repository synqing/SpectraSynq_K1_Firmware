// ============================================================================
// sb_chord_detect.cpp — pitch-class triad detector (SB_CHORD_V2, additive)
// ============================================================================
// Ported behaviour-for-behaviour from the donor LightwaveOS chord detector,
// ControlBus::detectChord
//   (Lightwave-Ledstrip/firmware-v3/src/audio/contracts/ControlBus.cpp:796-856).
//
// Operates on a 12-bin pitch-class chroma. The fork GDFT note table
// (system/constants.h notes[], A1 = 55 Hz, EXACTLY semitone-spaced) means a
// (bin % 12) fold of the per-note spectrogram is a TRUE pitch-class fold — the
// same fold make_smooth_chromagram() uses (visual/led_utilities.h:1577) and the
// same fold the incumbent scalar chroma_strength already performs
// (sb_audio_snapshot.cpp). Bin 0 of the chroma is the pitch class of note index
// 0 = A. The +3/+4/+6/+7/+8 interval arithmetic is modulo-12 and therefore
// rotation-invariant: detectChord is correct on an A-origin chroma; the only
// effect of the origin is that the absolute rootNote label is reported in
// A-origin units (0 = A) rather than the donor's C-origin (0 = C). Add 9 (mod
// 12) to convert an A-origin rootNote to the C-origin convention if needed.
//
// This TU pulls in NOTHING heavy (no globals.h, no fixed-point or LED-driver
// surface) so the REAL shipping detector compiles and runs on the host harness
// — no copy.
//
// NON-PRODUCTION when the flag is off: the entire file is empty without
// SB_CHORD_V2, so the production link is unchanged.
// ============================================================================
#include "sb_audio_snapshot.h"

#ifdef SB_CHORD_V2

#include <math.h>

static float sb_chord_clamp01(float v) {
  if (!isfinite(v)) return 0.0f;
  if (v < 0.0f) return 0.0f;
  if (v > 1.0f) return 1.0f;
  return v;
}

void sb_detect_chord(const float* chroma, SBChordState& cs) {
  // 1. Dominant pitch class = root candidate; accumulate total energy.
  uint8_t rootIdx = 0;
  float rootVal = chroma[0];
  float totalEnergy = chroma[0];
  for (uint8_t i = 1; i < SB_CHROMA_PC_BINS; ++i) {
    totalEnergy += chroma[i];
    if (chroma[i] > rootVal) {
      rootVal = chroma[i];
      rootIdx = i;
    }
  }
  cs.rootNote = rootIdx;
  cs.rootStrength = rootVal;

  // 2. Interval energies (circular pitch space).
  const float minorThird   = chroma[(rootIdx + 3) % 12];
  const float majorThird   = chroma[(rootIdx + 4) % 12];
  const float perfectFifth = chroma[(rootIdx + 7) % 12];
  const float dimFifth     = chroma[(rootIdx + 6) % 12];  // tritone
  const float augFifth     = chroma[(rootIdx + 8) % 12];

  // 3. Strongest third + strongest fifth classify the triad.
  const bool hasMinorThird = minorThird > majorThird;
  cs.thirdStrength = hasMinorThird ? minorThird : majorThird;

  if (perfectFifth >= dimFifth && perfectFifth >= augFifth) {
    cs.fifthStrength = perfectFifth;
    cs.type = hasMinorThird ? SBChordType::MINOR : SBChordType::MAJOR;
  } else if (dimFifth > perfectFifth && dimFifth > augFifth) {
    cs.fifthStrength = dimFifth;
    cs.type = SBChordType::DIMINISHED;  // diminished always has minor third
  } else {
    cs.fifthStrength = augFifth;
    cs.type = SBChordType::AUGMENTED;   // augmented always has major third
  }

  // 4. Confidence = triad energy ratio; a clean triad (~0.4 of total) maps to 1.0.
  const float triadEnergy = cs.rootStrength + cs.thirdStrength + cs.fifthStrength;
  if (totalEnergy > 0.01f) {
    cs.confidence = sb_chord_clamp01((triadEnergy / totalEnergy) / 0.4f);
  } else {
    cs.confidence = 0.0f;
    cs.type = SBChordType::NONE;
  }

  // Low confidence collapses to NONE (donor threshold 0.3).
  if (cs.confidence < 0.3f) {
    cs.type = SBChordType::NONE;
  }
}

#endif  // SB_CHORD_V2
