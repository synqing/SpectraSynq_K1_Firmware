/**
 * @file K1AudioContext.h
 * @brief K1 audio surface → effect-framework audio accessor adapter (P2).
 *
 * Replaces the P1 `AudioContextStub`. Presents the accessor surface that ported
 * v3 effects expect (rms / getBand / beatPhase / onset channels / chord /
 * chroma) over K1's OWN validated audio read surface:
 *   - `K1AudioSnapshot`   (audio/k1_audio_snapshot.h) — energy / novelty /
 *                          80-bin per-note spectrum / 12-bin A-origin chroma /
 *                          chord / silence.
 *   - `K1OnsetBeatEvent`  (audio/k1_audio_snapshot.h) — beat phase / confidence
 *                          / broadband + per-band onset (kick/snare/hihat).
 *
 * READ-ONLY ADAPTER. This type holds const pointers to caller-owned K1 structs
 * and maps their fields on demand. It does NOT call `k1_audio_snapshot_read()`
 * and adds NO behaviour to any build — the render-path wiring that actually
 * populates it from the live snapshot is P3. The K1 audio DSP is untouched.
 *
 * BINNING BRIDGE (documented gap — see evidence/p2-adapters.md):
 *   K1 produces an 80-bin per-note spectrum + 3 scalar band energies
 *   (low/mid/high). v3 effects address an 8-band ControlBus. `getBand(0..7)`
 *   folds the 80-bin spectrum into 8 contiguous mean-energy bands. The 3 scalar
 *   energies back `bass()/mid()/treble()` directly (higher fidelity than the
 *   fold for those three coarse ranges).
 *
 * CHROMA ORIGIN BRIDGE (documented):
 *   K1 `chroma_pc[12]` is A-origin (array index 0 = pitch-class A, which is
 *   C-origin pitch-class 9). v3 effects address chroma by a C-origin pitch-class
 *   LABEL (index 0 = C). The two accessors here rotate in OPPOSITE directions on
 *   purpose, and conflating them is the verified bug this header was corrected for:
 *     - `getChroma(label)` maps a C-origin LABEL → the A-origin ARRAY INDEX that
 *       holds it: arrayIndex = (label + 3) mod 12  (because +3 ≡ −9 mod 12, the
 *       INVERSE of the index→label map). Sanity: getChroma(9) [query pitch-class A]
 *       must read chroma_pc[0] (= A), and (9 + 3) mod 12 == 0. ✓
 *     - `rootNote()` maps an A-origin ARRAY/root INDEX → its C-origin LABEL:
 *       label = (index + 9) mod 12. This is the forward index→label direction and
 *       is left UNCHANGED (verified correct).
 *   They INTENTIONALLY differ: getChroma is label→index (+3), rootNote is
 *   index→label (+9); +3 and +9 are mod-12 inverses.
 *
 * Compiled ONLY under K1_EFFECT_FRAMEWORK_V1. Clean names only.
 * British English in comments and identifiers.
 */

#pragma once

#include <cstdint>

// K1 audio read surface (READ — we include the header, add no behaviour).
#include "k1_audio_snapshot.h"

namespace k1 {
namespace effects {
namespace framework {

// ─── Contract pins: catch K1-side shape drift at compile time ─────────────────
// These mirror the field widths this adapter relies on. If the K1 snapshot
// changes shape under us, the build fails here rather than silently mis-mapping.
#ifdef K1_ONSET_V2
static_assert(K1_ONSET_SPECTRUM_BINS == 80,
              "K1AudioContext binning bridge assumes an 80-bin per-note spectrum");
#endif
#ifdef K1_CHORD_V2
static_assert(K1_CHROMA_PC_BINS == 12,
              "K1AudioContext chroma bridge assumes a 12-bin pitch-class chroma");
#endif

/// Number of coarse bands the v3 ControlBus accessor surface exposes.
constexpr uint8_t K1_FRAMEWORK_BAND_COUNT = 8;
/// Number of pitch classes.
constexpr uint8_t K1_FRAMEWORK_CHROMA_COUNT = 12;
/// Rotation (semitones) mapping a K1 A-origin ARRAY/root INDEX to its C-origin
/// pitch-class LABEL: label = (index + 9) mod 12. Used by `rootNote()`.
/// (A-origin index 0 = pitch-class A = C-origin label 9.)
constexpr uint8_t K1_A_TO_C_ORIGIN_ROTATION = 9;

/// Rotation (semitones) mapping a C-origin pitch-class LABEL to the K1 A-origin
/// ARRAY INDEX that holds it: arrayIndex = (label + 3) mod 12. Used by
/// `getChroma()`. This is the INVERSE of `rootNote()`'s index→label map
/// (+3 ≡ −9 mod 12); the two directions intentionally differ.
constexpr uint8_t K1_C_TO_A_ORIGIN_ROTATION = 3;

// Proof the two rotations are mod-12 inverses (label A=9 ↔ array index 0).
static_assert((9 + K1_C_TO_A_ORIGIN_ROTATION) % K1_FRAMEWORK_CHROMA_COUNT == 0,
              "getChroma(9) [pitch-class A] must address chroma_pc[0]");
static_assert((K1_A_TO_C_ORIGIN_ROTATION + K1_C_TO_A_ORIGIN_ROTATION) %
                  K1_FRAMEWORK_CHROMA_COUNT == 0,
              "label->index (+3) and index->label (+9) must be mod-12 inverses");

/**
 * @brief Adapter presenting K1 audio over the framework accessor surface.
 *
 * Construct with pointers to the live K1 snapshot + onset event (P3 supplies
 * them from the render path). Default-constructed (both null) → `available()`
 * is false and every accessor returns a safe default, so effects compile and
 * run before the render-path wiring exists.
 */
class K1AudioContext {
public:
    K1AudioContext() = default;

    K1AudioContext(const K1AudioSnapshot* snapshot,
                   const K1OnsetBeatEvent* beat)
        : m_snapshot(snapshot), m_beat(beat) {}

    /// Rebind to a fresh frame's K1 structs (P3 render path calls this).
    void bind(const K1AudioSnapshot* snapshot, const K1OnsetBeatEvent* beat) {
        m_snapshot = snapshot;
        m_beat = beat;
    }

    /// True when both K1 surfaces are bound and the snapshot is not silent.
    bool available() const {
        return m_snapshot != nullptr && m_beat != nullptr && !m_snapshot->silence;
    }

    // ── Energy / level ──

    /// Overall energy level [0,1] (K1 vu_level).
    float rms() const { return m_snapshot ? clamp01(m_snapshot->vu_level) : 0.0f; }

    /// Peak-scaled transient level [0,1] (K1 peak_scaled).
    float peak() const { return m_snapshot ? clamp01(m_snapshot->peak_scaled) : 0.0f; }

    /// Spectral flux / novelty [0,1] (onset-detection proxy).
    float flux() const { return m_snapshot ? clamp01(m_snapshot->novelty) : 0.0f; }

    /// Broadband spectral energy [0,1].
    float spectralEnergy() const {
        return m_snapshot ? clamp01(m_snapshot->spectral_energy) : 0.0f;
    }

    /// True when K1's AGC silence gate is active.
    bool isSilent() const { return m_snapshot ? m_snapshot->silence : true; }

    // ── Coarse band energy (v3 ControlBus 8-band accessor surface) ──

    /// 8-band coarse energy [0,1]. Band i = mean of the 80-bin spectrum slice
    /// for that octave-eighth. Falls back to the 3 scalar energies under no-V2.
    float getBand(uint8_t i) const {
        if (i >= K1_FRAMEWORK_BAND_COUNT) return 0.0f;
#ifdef K1_ONSET_V2
        if (m_snapshot) {
            constexpr uint8_t kBins = K1_ONSET_SPECTRUM_BINS;  // 80
            const uint8_t per = kBins / K1_FRAMEWORK_BAND_COUNT;  // 10 bins/band
            const uint8_t lo = static_cast<uint8_t>(i * per);
            const uint8_t hi = static_cast<uint8_t>((i + 1) * per);
            float sum = 0.0f;
            uint8_t n = 0;
            for (uint8_t b = lo; b < hi && b < kBins; ++b) { sum += m_snapshot->spectrum[b]; ++n; }
            return (n > 0) ? clamp01(sum / static_cast<float>(n)) : 0.0f;
        }
#endif
        // No-V2 fallback: spread the 3 scalar energies across the 8 bands.
        if (!m_snapshot) return 0.0f;
        if (i < 3) return clamp01(m_snapshot->low_energy);
        if (i < 6) return clamp01(m_snapshot->mid_energy);
        return clamp01(m_snapshot->high_energy);
    }

    /// Bass energy [0,1] — K1 scalar low_energy (coarser but cleaner than fold).
    float bass() const { return m_snapshot ? clamp01(m_snapshot->low_energy) : 0.0f; }
    /// Mid energy [0,1] — K1 scalar mid_energy.
    float mid() const { return m_snapshot ? clamp01(m_snapshot->mid_energy) : 0.0f; }
    /// Treble energy [0,1] — K1 scalar high_energy.
    float treble() const { return m_snapshot ? clamp01(m_snapshot->high_energy) : 0.0f; }

    // ── Beat / tempo (K1OnsetBeatEvent) ──

    /// Beat phase [0,1] within the beat period.
    float beatPhase() const { return m_beat ? clamp01(m_beat->beat_phase) : 0.0f; }
    /// Beat-tracking confidence [0,1] (PLL lock quality).
    float beatConfidence() const { return m_beat ? clamp01(m_beat->beat_confidence) : 0.0f; }
    /// True on the frame a beat fired.
    bool isOnBeat() const { return m_beat ? m_beat->beat : false; }
    /// True on the frame a broadband onset fired.
    bool hasOnset() const { return m_beat ? m_beat->onset : false; }
    /// Broadband onset strength [0,1].
    float onsetStrength() const { return m_beat ? clamp01(m_beat->onset_strength) : 0.0f; }
    /// Bass-band onset strength [0,1].
    float bassOnsetStrength() const { return m_beat ? clamp01(m_beat->bass_onset_strength) : 0.0f; }

    // ── Percussive channels (V2; safe defaults under no-V2) ──

    bool isKickHit() const {
#ifdef K1_ONSET_V2
        return m_beat ? m_beat->kick : false;
#else
        return m_beat ? m_beat->bass_onset : false;  // fallback: bass onset
#endif
    }
    bool isSnareHit() const {
#ifdef K1_ONSET_V2
        return m_beat ? m_beat->snare : false;
#else
        return false;
#endif
    }
    bool isHihatHit() const {
#ifdef K1_ONSET_V2
        return m_beat ? m_beat->hihat : false;
#else
        return false;
#endif
    }
    /// Kick channel decaying level [0,1] (for trails). 0 under no-V2.
    float kickLevel() const {
#ifdef K1_ONSET_V2
        return m_beat ? clamp01(m_beat->kick_level) : 0.0f;
#else
        return 0.0f;
#endif
    }
    /// Snare channel decaying level [0,1]. 0 under no-V2.
    float snareLevel() const {
#ifdef K1_ONSET_V2
        return m_beat ? clamp01(m_beat->snare_level) : 0.0f;
#else
        return 0.0f;
#endif
    }
    /// Hi-hat channel decaying level [0,1]. 0 under no-V2.
    float hihatLevel() const {
#ifdef K1_ONSET_V2
        return m_beat ? clamp01(m_beat->hihat_level) : 0.0f;
#else
        return 0.0f;
#endif
    }

    // ── Chroma / chord (V2; safe defaults under no-V2) ──

    /// Chroma energy [0,1] for a C-origin pitch-class LABEL (0 = C). 0 under no-V2.
    /// Maps the C-origin label to the A-origin array index that holds it:
    /// arrayIndex = (label + 3) mod 12 (≡ label − 9 mod 12). This is the INVERSE
    /// of `rootNote()`'s index→label (+9) rotation — the directions differ on
    /// purpose. Sanity: getChroma(9) [pitch-class A] reads chroma_pc[0].
    float getChroma(uint8_t cOriginLabel) const {
#ifdef K1_CHORD_V2
        if (!m_snapshot || cOriginLabel >= K1_FRAMEWORK_CHROMA_COUNT) return 0.0f;
        const uint8_t aOriginIndex =
            static_cast<uint8_t>((cOriginLabel + K1_C_TO_A_ORIGIN_ROTATION) %
                                 K1_FRAMEWORK_CHROMA_COUNT);
        return clamp01(m_snapshot->chroma_pc[aOriginIndex]);
#else
        (void)cOriginLabel;
        return 0.0f;
#endif
    }

    /// Overall chroma strength [0,1] (single-value harmonic salience proxy).
    float chromaStrength() const {
        return m_snapshot ? clamp01(m_snapshot->chroma_strength) : 0.0f;
    }

    /// True when a chord is detected (not NONE). False under no-V2.
    bool hasChord() const {
#ifdef K1_CHORD_V2
        return m_snapshot && m_snapshot->chord.type != K1ChordType::NONE;
#else
        return false;
#endif
    }
    /// Chord root note in C-origin units (0=C). 0 under no-V2.
    uint8_t rootNote() const {
#ifdef K1_CHORD_V2
        if (!m_snapshot) return 0;
        return static_cast<uint8_t>((m_snapshot->chord.rootNote + K1_A_TO_C_ORIGIN_ROTATION) %
                                    K1_FRAMEWORK_CHROMA_COUNT);
#else
        return 0;
#endif
    }
    /// Chord detection confidence [0,1]. 0 under no-V2.
    float chordConfidence() const {
#ifdef K1_CHORD_V2
        return m_snapshot ? clamp01(m_snapshot->chord.confidence) : 0.0f;
#else
        return 0.0f;
#endif
    }
    bool isMajor() const {
#ifdef K1_CHORD_V2
        return m_snapshot && m_snapshot->chord.type == K1ChordType::MAJOR;
#else
        return false;
#endif
    }
    bool isMinor() const {
#ifdef K1_CHORD_V2
        return m_snapshot && m_snapshot->chord.type == K1ChordType::MINOR;
#else
        return false;
#endif
    }

private:
    static float clamp01(float x) {
        if (x < 0.0f) return 0.0f;
        if (x > 1.0f) return 1.0f;
        return x;
    }

    const K1AudioSnapshot* m_snapshot = nullptr;
    const K1OnsetBeatEvent* m_beat = nullptr;
};

}  // namespace framework
}  // namespace effects
}  // namespace k1
