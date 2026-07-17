/**
 * @file EffectRegistry.cpp
 * @brief The single append-only EffectEntry[] table + lookup API (R1).
 *
 * One row per current legacy light mode (family 0x00, stable_id low byte aliases
 * the lightshow_modes ordinal) plus one row per ported native v3 effect (families
 * 0x10/0x11/0x12, legacy_ordinal = kNoLegacy). Every consumer is intended to
 * derive from this table in R2; R1 only defines it and self-validates.
 *
 * Static-init safety: the table stores `nullptr` for `metadata`/`effect` and they
 * are bound on first touch in registry_ensure() (Core 0, off the render hot path).
 * The legacy rows bind through legacy_effect_for_mode() (the existing .bss adapter
 * table); the native rows bind through their *_effect() singleton accessors. No
 * TU-spanning static constructor table is used.
 *
 * Compiled ONLY under K1_EFFECT_REGISTRY_V1 (which requires K1_EFFECT_FRAMEWORK_V1).
 * The shipping k1_hardware build defines NEITHER flag and never sees this TU.
 *
 * British English in comments and identifiers.
 */

#ifdef K1_EFFECT_REGISTRY_V1

#if !defined(K1_EFFECT_FRAMEWORK_V1)
#error "K1_EFFECT_REGISTRY_V1 requires K1_EFFECT_FRAMEWORK_V1"
#endif

#include "EffectRegistry.h"

#include "config_types.h"          // lightshow_modes enum, NUM_MODES, light_mode_is_enabled
#include "LegacyEffectAdapter.h"   // legacy_effect_for_mode()

// Native v3 effect singleton accessors (each returns a static IEffect*).
#include "effect_beat_pulse_resonant.h"
#include "effect_lgp_beat_prism.h"
#include "effect_lgp_flux_rift.h"
#include "effect_lgp_harmonic_tide.h"
#include "effect_lgp_transient_lattice.h"

namespace k1 {
namespace effects {
namespace framework {

namespace {

// Compose a legacy stable_id from its ordinal (family 0x00, low byte == ordinal).
constexpr EffectId legacy_id(uint8_t ordinal) {
    return static_cast<EffectId>((static_cast<uint16_t>(kFamilyLegacy) << 8) |
                                 ordinal);
}

// ── The single append-only table ────────────────────────────────────────────
// `metadata` and `effect` are nullptr here and bound in registry_ensure().
// audio_deps / enabled / director_ok mirror the current K1 behaviour:
//   enabled     == light_mode_is_enabled(ordinal)  (8 modes disabled today)
//   director_ok == k1_mode_allowed(ordinal)        (9-mode director allow-list)
//   audio_deps  == best-effort per mode character.
EffectEntry g_registry[] = {
    // ── Legacy family 0x00: low byte == lightshow_modes ordinal ──
    { legacy_id(LIGHT_MODE_GDFT),                 "gdft",                 "GDFT",                  nullptr, nullptr, false, false, AudioDeps::LEVEL,                  LIGHT_MODE_GDFT },
    { legacy_id(LIGHT_MODE_GDFT_CHROMAGRAM),      "gdft_chromagram",      "CHROMAGRAM",            nullptr, nullptr, false, false, AudioDeps::CHORD | AudioDeps::LEVEL, LIGHT_MODE_GDFT_CHROMAGRAM },
    { legacy_id(LIGHT_MODE_GDFT_CHROMAGRAM_DOTS), "gdft_chromagram_dots", "CHROMAGRAM DOTS",       nullptr, nullptr, false, false, AudioDeps::CHORD | AudioDeps::LEVEL, LIGHT_MODE_GDFT_CHROMAGRAM_DOTS },
    { legacy_id(LIGHT_MODE_BLOOM),                "bloom",                "BLOOM",                 nullptr, nullptr, true,  true,  AudioDeps::LEVEL,                  LIGHT_MODE_BLOOM },
    { legacy_id(LIGHT_MODE_VU_DOT),               "vu_dot",               "VU DOT",                nullptr, nullptr, false, false, AudioDeps::LEVEL,                  LIGHT_MODE_VU_DOT },
    { legacy_id(LIGHT_MODE_KALEIDOSCOPE),         "kaleidoscope",         "KALEIDOSCOPE",          nullptr, nullptr, false, false, AudioDeps::ONSET | AudioDeps::LEVEL, LIGHT_MODE_KALEIDOSCOPE },
    { legacy_id(LIGHT_MODE_QUANTUM_COLLAPSE),     "quantum_collapse",     "QUANTUM COLLAPSE",      nullptr, nullptr, false, false, AudioDeps::LEVEL,                  LIGHT_MODE_QUANTUM_COLLAPSE },
    { legacy_id(LIGHT_MODE_WAVEFORM_FAST),        "waveform_fast",        "WAVEFORM-FAST",         nullptr, nullptr, true,  true,  AudioDeps::LEVEL,                  LIGHT_MODE_WAVEFORM_FAST },
    { legacy_id(LIGHT_MODE_WAVEFORM),             "waveform",             "WAVEFORM",              nullptr, nullptr, true,  true,  AudioDeps::LEVEL,                  LIGHT_MODE_WAVEFORM },
    { legacy_id(LIGHT_MODE_BLOOM_FAST),           "bloom_fast",           "BLOOM (FAST)",          nullptr, nullptr, true,  true,  AudioDeps::LEVEL,                  LIGHT_MODE_BLOOM_FAST },
    { legacy_id(LIGHT_MODE_VU),                   "vu",                   "VU",                    nullptr, nullptr, false, false, AudioDeps::LEVEL,                  LIGHT_MODE_VU },
    { legacy_id(LIGHT_MODE_WAVEFORM_HYBRID),      "waveform_hybrid",      "WAVEFORM_HYBRID",       nullptr, nullptr, true,  true,  AudioDeps::LEVEL,                  LIGHT_MODE_WAVEFORM_HYBRID },
    { legacy_id(LIGHT_MODE_AURORA),               "aurora",               "AURORA",                nullptr, nullptr, true,  false, AudioDeps::LEVEL,                  LIGHT_MODE_AURORA },
    { legacy_id(LIGHT_MODE_COMET),                "comet",                "COMET",                 nullptr, nullptr, true,  true,  AudioDeps::ONSET | AudioDeps::LEVEL, LIGHT_MODE_COMET },
    { legacy_id(LIGHT_MODE_SPECTRUM_RIVER),       "spectrum_river",       "SPECTRUM RIVER",        nullptr, nullptr, true,  true,  AudioDeps::LEVEL,                  LIGHT_MODE_SPECTRUM_RIVER },
    { legacy_id(LIGHT_MODE_SPECTRUM_RIVER_V2),    "spectrum_river_v2",    "SPECTRUM RIVER 2",      nullptr, nullptr, true,  false, AudioDeps::LEVEL,                  LIGHT_MODE_SPECTRUM_RIVER_V2 },
    { legacy_id(LIGHT_MODE_EMBER),                "ember",                "EMBER FIELD",           nullptr, nullptr, true,  false, AudioDeps::LEVEL,                  LIGHT_MODE_EMBER },
    { legacy_id(LIGHT_MODE_EMBER_V2),             "ember_v2",             "EMBER FIELD 2",         nullptr, nullptr, false, false, AudioDeps::LEVEL,                  LIGHT_MODE_EMBER_V2 },
    { legacy_id(LIGHT_MODE_WAVEFORM_TEMPO),       "waveform_tempo",       "WAVEFORM TEMPO",        nullptr, nullptr, true,  false, AudioDeps::BEAT | AudioDeps::LEVEL,  LIGHT_MODE_WAVEFORM_TEMPO },
    { legacy_id(LIGHT_MODE_TEMPO_RIVER),          "tempo_river",          "TEMPO RIVER",           nullptr, nullptr, true,  false, AudioDeps::BEAT | AudioDeps::LEVEL,  LIGHT_MODE_TEMPO_RIVER },
    { legacy_id(LIGHT_MODE_TEMPO_COMET),          "tempo_comet",          "TEMPO COMET",           nullptr, nullptr, true,  false, AudioDeps::BEAT | AudioDeps::ONSET,  LIGHT_MODE_TEMPO_COMET },
    { legacy_id(LIGHT_MODE_DENSE_FORGE),          "dense_forge",          "DENSE FORGE",           nullptr, nullptr, true,  true,  AudioDeps::ONSET | AudioDeps::LEVEL, LIGHT_MODE_DENSE_FORGE },
    { legacy_id(LIGHT_MODE_SNAPWAVE),             "snapwave",             "SNAPWAVE",              nullptr, nullptr, true,  true,  AudioDeps::CHORD | AudioDeps::LEVEL, LIGHT_MODE_SNAPWAVE },
    { legacy_id(LIGHT_MODE_PULSE_PRISM),          "pulse_prism",          "PULSE PRISM",           nullptr, nullptr, true,  true,  AudioDeps::ONSET | AudioDeps::BEAT,  LIGHT_MODE_PULSE_PRISM },
    { legacy_id(LIGHT_MODE_DENSE_FORGE_CHORD),    "dense_forge_chord",    "DENSE FORGE CHORD",     nullptr, nullptr, true,  false, AudioDeps::CHORD | AudioDeps::ONSET, LIGHT_MODE_DENSE_FORGE_CHORD },
    { legacy_id(LIGHT_MODE_CHROMA_CONSTELLATION), "chroma_constellation", "CHROMA CONSTELLATION",  nullptr, nullptr, true,  false, AudioDeps::CHORD | AudioDeps::LEVEL, LIGHT_MODE_CHROMA_CONSTELLATION },
    { legacy_id(LIGHT_MODE_PERCUSSION_BURST),     "percussion_burst",     "PERCUSSION BURST",      nullptr, nullptr, true,  false, AudioDeps::ONSET | AudioDeps::BEAT,  LIGHT_MODE_PERCUSSION_BURST },
    { legacy_id(LIGHT_MODE_TEMPO_COMET_ANTICIPATE),"tempo_comet_anticipate","TEMPO COMET ANTICIPATE",nullptr,nullptr,true, false, AudioDeps::BEAT | AudioDeps::ONSET,  LIGHT_MODE_TEMPO_COMET_ANTICIPATE },
    { legacy_id(LIGHT_MODE_RIVER_SURGE),          "river_surge",          "RIVER SURGE",           nullptr, nullptr, true,  false, AudioDeps::LEVEL,                  LIGHT_MODE_RIVER_SURGE },
    { legacy_id(LIGHT_MODE_TEMPO_RIVER_WALK),     "tempo_river_walk",     "TEMPO RIVER WALK",      nullptr, nullptr, true,  false, AudioDeps::BEAT | AudioDeps::CHORD,  LIGHT_MODE_TEMPO_RIVER_WALK },
    { legacy_id(LIGHT_MODE_BEAT_PULSE),           "beat_pulse",           "BEAT PULSE",            nullptr, nullptr, false, false, AudioDeps::BEAT | AudioDeps::LEVEL,  LIGHT_MODE_BEAT_PULSE },
    { legacy_id(LIGHT_MODE_BLOOM_BT),             "bloom_bt",             "BLOOM BASSTREBLE",      nullptr, nullptr, true,  false, AudioDeps::LEVEL,                  LIGHT_MODE_BLOOM_BT },
    { legacy_id(LIGHT_MODE_WAVEFORM_HYBRID_K1),   "waveform_hybrid_k1",   "WAVEFORM HYBRID K1",    nullptr, nullptr, true,  false, AudioDeps::LEVEL,                  LIGHT_MODE_WAVEFORM_HYBRID_K1 },
    { legacy_id(LIGHT_MODE_MOIRE_CATHEDRAL),      "moire_cathedral",      "MOIRE CATHEDRAL",       nullptr, nullptr, false, false, AudioDeps::LEVEL,                  LIGHT_MODE_MOIRE_CATHEDRAL },
    { legacy_id(LIGHT_MODE_CANNONADE),            "cannonade",            "CANNONADE",             nullptr, nullptr, false, false, AudioDeps::ONSET | AudioDeps::BEAT,  LIGHT_MODE_CANNONADE },
    { legacy_id(LIGHT_MODE_SHOCKWAVE),            "shockwave",            "SHOCKWAVE",             nullptr, nullptr, true,  false, AudioDeps::ONSET | AudioDeps::LEVEL, LIGHT_MODE_SHOCKWAVE },
    { legacy_id(LIGHT_MODE_IRIS),                 "iris",                 "IRIS",                  nullptr, nullptr, true,  false, AudioDeps::BEAT | AudioDeps::ONSET,  LIGHT_MODE_IRIS },
    { legacy_id(LIGHT_MODE_MELODIC_BLOOM),       "melodic_bloom",        "MELODIC BLOOM",         nullptr, nullptr, true,  false, AudioDeps::LEVEL,                    LIGHT_MODE_MELODIC_BLOOM },

    // ── Native family 0x10/0x11/0x12: the ported-but-dead IEffects go live here ──
    { 0x1001, "beat_pulse_resonant",   "Beat Pulse (Resonant)",  nullptr, nullptr, true, true, AudioDeps::BEAT | AudioDeps::LEVEL,  kNoLegacy },
    { 0x1101, "lgp_harmonic_tide",     "LGP Harmonic Tide",      nullptr, nullptr, true, true, AudioDeps::CHORD | AudioDeps::LEVEL, kNoLegacy },
    { 0x1201, "lgp_beat_prism",        "LGP Beat Prism",         nullptr, nullptr, true, true, AudioDeps::BEAT,                     kNoLegacy },
    { 0x1202, "lgp_flux_rift",         "LGP Flux Rift",          nullptr, nullptr, true, true, AudioDeps::ONSET | AudioDeps::LEVEL, kNoLegacy },
    { 0x1203, "lgp_transient_lattice", "LGP Transient Lattice",  nullptr, nullptr, true, true, AudioDeps::ONSET | AudioDeps::BEAT,  kNoLegacy },
};

constexpr uint16_t kRegistryCount =
    static_cast<uint16_t>(sizeof(g_registry) / sizeof(g_registry[0]));

// ── Compile-time id/ordinal guards ───────────────────────────────────────────
// `g_registry` is mutable (its `metadata`/`effect` pointers are bound at runtime
// in registry_ensure()), so it cannot be read in a constant expression. The
// id-space invariants are therefore checked against a `constexpr` companion of
// the immutable {stable_id, legacy_ordinal} columns. registry_validate() asserts
// at boot that the live table's id/ordinal columns still match this companion,
// so the two cannot silently diverge.
struct RegId {
    EffectId stable_id;
    uint8_t  legacy_ordinal;
};

constexpr RegId k_reg_ids[] = {
    { legacy_id(LIGHT_MODE_GDFT),                  LIGHT_MODE_GDFT },
    { legacy_id(LIGHT_MODE_GDFT_CHROMAGRAM),       LIGHT_MODE_GDFT_CHROMAGRAM },
    { legacy_id(LIGHT_MODE_GDFT_CHROMAGRAM_DOTS),  LIGHT_MODE_GDFT_CHROMAGRAM_DOTS },
    { legacy_id(LIGHT_MODE_BLOOM),                 LIGHT_MODE_BLOOM },
    { legacy_id(LIGHT_MODE_VU_DOT),                LIGHT_MODE_VU_DOT },
    { legacy_id(LIGHT_MODE_KALEIDOSCOPE),          LIGHT_MODE_KALEIDOSCOPE },
    { legacy_id(LIGHT_MODE_QUANTUM_COLLAPSE),      LIGHT_MODE_QUANTUM_COLLAPSE },
    { legacy_id(LIGHT_MODE_WAVEFORM_FAST),         LIGHT_MODE_WAVEFORM_FAST },
    { legacy_id(LIGHT_MODE_WAVEFORM),              LIGHT_MODE_WAVEFORM },
    { legacy_id(LIGHT_MODE_BLOOM_FAST),            LIGHT_MODE_BLOOM_FAST },
    { legacy_id(LIGHT_MODE_VU),                    LIGHT_MODE_VU },
    { legacy_id(LIGHT_MODE_WAVEFORM_HYBRID),       LIGHT_MODE_WAVEFORM_HYBRID },
    { legacy_id(LIGHT_MODE_AURORA),                LIGHT_MODE_AURORA },
    { legacy_id(LIGHT_MODE_COMET),                 LIGHT_MODE_COMET },
    { legacy_id(LIGHT_MODE_SPECTRUM_RIVER),        LIGHT_MODE_SPECTRUM_RIVER },
    { legacy_id(LIGHT_MODE_SPECTRUM_RIVER_V2),     LIGHT_MODE_SPECTRUM_RIVER_V2 },
    { legacy_id(LIGHT_MODE_EMBER),                 LIGHT_MODE_EMBER },
    { legacy_id(LIGHT_MODE_EMBER_V2),              LIGHT_MODE_EMBER_V2 },
    { legacy_id(LIGHT_MODE_WAVEFORM_TEMPO),        LIGHT_MODE_WAVEFORM_TEMPO },
    { legacy_id(LIGHT_MODE_TEMPO_RIVER),           LIGHT_MODE_TEMPO_RIVER },
    { legacy_id(LIGHT_MODE_TEMPO_COMET),           LIGHT_MODE_TEMPO_COMET },
    { legacy_id(LIGHT_MODE_DENSE_FORGE),           LIGHT_MODE_DENSE_FORGE },
    { legacy_id(LIGHT_MODE_SNAPWAVE),              LIGHT_MODE_SNAPWAVE },
    { legacy_id(LIGHT_MODE_PULSE_PRISM),           LIGHT_MODE_PULSE_PRISM },
    { legacy_id(LIGHT_MODE_DENSE_FORGE_CHORD),     LIGHT_MODE_DENSE_FORGE_CHORD },
    { legacy_id(LIGHT_MODE_CHROMA_CONSTELLATION),  LIGHT_MODE_CHROMA_CONSTELLATION },
    { legacy_id(LIGHT_MODE_PERCUSSION_BURST),      LIGHT_MODE_PERCUSSION_BURST },
    { legacy_id(LIGHT_MODE_TEMPO_COMET_ANTICIPATE),LIGHT_MODE_TEMPO_COMET_ANTICIPATE },
    { legacy_id(LIGHT_MODE_RIVER_SURGE),           LIGHT_MODE_RIVER_SURGE },
    { legacy_id(LIGHT_MODE_TEMPO_RIVER_WALK),      LIGHT_MODE_TEMPO_RIVER_WALK },
    { legacy_id(LIGHT_MODE_BEAT_PULSE),            LIGHT_MODE_BEAT_PULSE },
    { legacy_id(LIGHT_MODE_BLOOM_BT),              LIGHT_MODE_BLOOM_BT },
    { legacy_id(LIGHT_MODE_WAVEFORM_HYBRID_K1),    LIGHT_MODE_WAVEFORM_HYBRID_K1 },
    { legacy_id(LIGHT_MODE_MOIRE_CATHEDRAL),       LIGHT_MODE_MOIRE_CATHEDRAL },
    { legacy_id(LIGHT_MODE_CANNONADE),             LIGHT_MODE_CANNONADE },
    { legacy_id(LIGHT_MODE_SHOCKWAVE),             LIGHT_MODE_SHOCKWAVE },
    { legacy_id(LIGHT_MODE_IRIS),                  LIGHT_MODE_IRIS },
    { legacy_id(LIGHT_MODE_MELODIC_BLOOM),         LIGHT_MODE_MELODIC_BLOOM },
    { 0x1001, kNoLegacy },
    { 0x1101, kNoLegacy },
    { 0x1201, kNoLegacy },
    { 0x1202, kNoLegacy },
    { 0x1203, kNoLegacy },
};

constexpr uint16_t kRegIdCount =
    static_cast<uint16_t>(sizeof(k_reg_ids) / sizeof(k_reg_ids[0]));

// Count must fit the persisted uint8_t ordinal space (legacy low byte).
static_assert(kRegistryCount <= 255, "registry count must fit a uint8_t");
static_assert(kRegistryCount >= NUM_MODES,
              "every legacy mode must have a registry row");
static_assert(kRegIdCount == kRegistryCount,
              "companion id table must match the live registry row count");

// Per-row id-space invariants (constexpr → compile-time).
constexpr bool reg_row_family_ok(uint16_t i) {
    const uint8_t fam = effect_family(k_reg_ids[i].stable_id);
    if (fam == kFamilyLegacy) {
        // Legacy: low byte aliases the ordinal, ordinal in range.
        return effect_sequence(k_reg_ids[i].stable_id) == k_reg_ids[i].legacy_ordinal &&
               k_reg_ids[i].legacy_ordinal < NUM_MODES;
    }
    // Native: a known v3 family byte + kNoLegacy ordinal.
    return (fam == kFamilyV3Beat || fam == kFamilyV3Chord || fam == kFamilyV3Lgp) &&
           k_reg_ids[i].legacy_ordinal == kNoLegacy;
}

// Stable-id uniqueness across the whole companion table (constexpr).
constexpr bool reg_id_unique(uint16_t i) {
    for (uint16_t j = 0; j < kRegIdCount; ++j) {
        if (j != i && k_reg_ids[j].stable_id == k_reg_ids[i].stable_id) return false;
    }
    return true;
}

#define K1_REG_ROW_GUARD(i)                                                    \
    static_assert((i) >= kRegIdCount || reg_row_family_ok(i),                  \
                  "row family/ordinal-alias invariant violated");             \
    static_assert((i) >= kRegIdCount || reg_id_unique(i),                      \
                  "duplicate stable_id in the registry id space")

K1_REG_ROW_GUARD(0);  K1_REG_ROW_GUARD(1);  K1_REG_ROW_GUARD(2);  K1_REG_ROW_GUARD(3);
K1_REG_ROW_GUARD(4);  K1_REG_ROW_GUARD(5);  K1_REG_ROW_GUARD(6);  K1_REG_ROW_GUARD(7);
K1_REG_ROW_GUARD(8);  K1_REG_ROW_GUARD(9);  K1_REG_ROW_GUARD(10); K1_REG_ROW_GUARD(11);
K1_REG_ROW_GUARD(12); K1_REG_ROW_GUARD(13); K1_REG_ROW_GUARD(14); K1_REG_ROW_GUARD(15);
K1_REG_ROW_GUARD(16); K1_REG_ROW_GUARD(17); K1_REG_ROW_GUARD(18); K1_REG_ROW_GUARD(19);
K1_REG_ROW_GUARD(20); K1_REG_ROW_GUARD(21); K1_REG_ROW_GUARD(22); K1_REG_ROW_GUARD(23);
K1_REG_ROW_GUARD(24); K1_REG_ROW_GUARD(25); K1_REG_ROW_GUARD(26); K1_REG_ROW_GUARD(27);
K1_REG_ROW_GUARD(28); K1_REG_ROW_GUARD(29); K1_REG_ROW_GUARD(30); K1_REG_ROW_GUARD(31);
K1_REG_ROW_GUARD(32); K1_REG_ROW_GUARD(33); K1_REG_ROW_GUARD(34); K1_REG_ROW_GUARD(35);
K1_REG_ROW_GUARD(36); K1_REG_ROW_GUARD(37); K1_REG_ROW_GUARD(38); K1_REG_ROW_GUARD(39);
K1_REG_ROW_GUARD(40); K1_REG_ROW_GUARD(41);

#undef K1_REG_ROW_GUARD

// ── Lazy bind (static-init-safe) ─────────────────────────────────────────────
bool g_registry_bound = false;

void bind_native(EffectId id, IEffect* effect) {
    for (uint16_t i = 0; i < kRegistryCount; ++i) {
        if (g_registry[i].stable_id == id) {
            g_registry[i].effect = effect;
            g_registry[i].metadata = (effect != nullptr)
                                         ? &effect->getMetadata()
                                         : nullptr;
            return;
        }
    }
}

}  // namespace

void registry_ensure() {
    if (g_registry_bound) return;

    // Legacy rows: bind through the existing .bss adapter table + a shared
    // legacy metadata stub (the per-mode adapter forwards to the identical K1
    // dispatch). The native rows bind through their singleton accessors.
    for (uint16_t i = 0; i < kRegistryCount; ++i) {
        EffectEntry& row = g_registry[i];
        if (effect_family(row.stable_id) != kFamilyLegacy) continue;
        IEffect* adapter = legacy_effect_for_mode(row.legacy_ordinal);
        row.effect = adapter;
        row.metadata = (adapter != nullptr) ? &adapter->getMetadata() : nullptr;
    }

    bind_native(0x1001, beat_pulse_resonant_effect());
    bind_native(0x1101, lgp_harmonic_tide_effect());
    bind_native(0x1201, lgp_beat_prism_effect());
    bind_native(0x1202, lgp_flux_rift_effect());
    bind_native(0x1203, lgp_transient_lattice_effect());

    g_registry_bound = true;
}

const EffectEntry* effect_registry() {
    registry_ensure();
    return g_registry;
}

uint16_t effect_registry_count() {
    return kRegistryCount;
}

const EffectEntry* entry_for_stable_id(EffectId id) {
    registry_ensure();
    for (uint16_t i = 0; i < kRegistryCount; ++i) {
        if (g_registry[i].stable_id == id) return &g_registry[i];
    }
    return nullptr;
}

const EffectEntry* entry_for_legacy_ordinal(uint8_t ordinal) {
    if (ordinal == kNoLegacy) return nullptr;
    registry_ensure();
    for (uint16_t i = 0; i < kRegistryCount; ++i) {
        if (effect_family(g_registry[i].stable_id) == kFamilyLegacy &&
            g_registry[i].legacy_ordinal == ordinal) {
            return &g_registry[i];
        }
    }
    return nullptr;
}

bool registry_validate() {
    registry_ensure();
    for (uint16_t i = 0; i < kRegistryCount; ++i) {
        const EffectEntry& row = g_registry[i];

        // The live id/ordinal columns must still match the constexpr companion
        // the compile-time guards were proven against.
        if (row.stable_id != k_reg_ids[i].stable_id) return false;
        if (row.legacy_ordinal != k_reg_ids[i].legacy_ordinal) return false;

        // Every row must have a bound renderer + metadata.
        if (row.effect == nullptr || row.metadata == nullptr) return false;

        // Legacy rows: ordinal must alias the id and be in range.
        if (effect_family(row.stable_id) == kFamilyLegacy) {
            if (row.legacy_ordinal >= NUM_MODES) return false;
            if (effect_sequence(row.stable_id) != row.legacy_ordinal) return false;
        } else if (row.legacy_ordinal != kNoLegacy) {
            return false;  // native rows must declare kNoLegacy
        }

        // Stable-id uniqueness (O(n^2), boot-only).
        for (uint16_t j = i + 1; j < kRegistryCount; ++j) {
            if (g_registry[j].stable_id == row.stable_id) return false;
        }
    }
    return true;
}

// ─── R2-core: native runtime-ordinal mapping ────────────────────────────────
//
// The natives (legacy_ordinal == kNoLegacy) are appended to the runtime ordinal
// space at NUM_MODES + k, in the SAME order they appear in g_registry. This map
// is registry-build-only; NUM_MODES (the persisted ordinal cap) is unchanged.
namespace {

/// Native stable ids, in registry row order. Kept in sync with g_registry's
/// native rows by k_native_count == (kRegistryCount - NUM_MODES) below.
constexpr EffectId k_native_ids[] = {
    0x1001,  // beat_pulse_resonant
    0x1101,  // lgp_harmonic_tide
    0x1201,  // lgp_beat_prism
    0x1202,  // lgp_flux_rift
    0x1203,  // lgp_transient_lattice
};
constexpr uint16_t k_native_count =
    static_cast<uint16_t>(sizeof(k_native_ids) / sizeof(k_native_ids[0]));

// The native count must equal the number of non-legacy rows in the live table.
static_assert(kRegistryCount == NUM_MODES + k_native_count,
              "native runtime-ordinal map must cover every native row exactly");

// The public kRegistryNativeReserve (used by consumers that cannot see
// k_native_count, e.g. the VP-probe collision guard) must equal the real count.
static_assert(kRegistryNativeReserve == k_native_count,
              "kRegistryNativeReserve must equal the live native row count");

bool g_registry_healthy = false;

}  // namespace

uint16_t registry_native_count() {
    return k_native_count;
}

uint16_t registry_mode_count() {
    return static_cast<uint16_t>(NUM_MODES) + k_native_count;
}

EffectId stable_id_for_runtime_ordinal(uint16_t ordinal) {
    if (ordinal < NUM_MODES) {
        // Legacy: the stored ordinal aliases its stable id directly.
        return legacy_id(static_cast<uint8_t>(ordinal));
    }
    const uint16_t native_index = static_cast<uint16_t>(ordinal - NUM_MODES);
    if (native_index < k_native_count) {
        return k_native_ids[native_index];
    }
    return INVALID_EFFECT_ID;
}

const EffectEntry* entry_for_runtime_ordinal(uint16_t ordinal) {
    if (ordinal < NUM_MODES) {
        return entry_for_legacy_ordinal(static_cast<uint8_t>(ordinal));
    }
    const EffectId id = stable_id_for_runtime_ordinal(ordinal);
    if (id == INVALID_EFFECT_ID) return nullptr;
    return entry_for_stable_id(id);
}

const char* registry_display_name(uint16_t ordinal) {
    const EffectEntry* row = entry_for_runtime_ordinal(ordinal);
    return (row != nullptr) ? row->display_name : nullptr;
}

bool registry_mode_is_enabled(uint16_t ordinal) {
    const EffectEntry* row = entry_for_runtime_ordinal(ordinal);
    return (row != nullptr) && row->enabled;
}

bool registry_is_healthy() {
    return g_registry_healthy;
}

// ─── R5: dense (gap-free) navigation index ──────────────────────────────────
// Presentation-only mapping between the holey runtime-ordinal space and a
// contiguous menu index over ENABLED ordinals (legacy-enabled in enum order,
// then natives). The persisted ordinal is never changed; only the user-facing
// number is converted at the serial boundary. See the header for the contract.

uint16_t registry_dense_count() {
    const uint16_t span = registry_mode_count();
    uint16_t n = 0;
    for (uint16_t ord = 0; ord < span; ord++) {
        if (registry_mode_is_enabled(ord)) n++;
    }
    return n;
}

uint16_t registry_dense_to_ordinal(uint16_t dense_index) {
    const uint16_t span = registry_mode_count();
    uint16_t seen = 0;
    for (uint16_t ord = 0; ord < span; ord++) {
        if (registry_mode_is_enabled(ord)) {
            if (seen == dense_index) return ord;
            seen++;
        }
    }
    // Out-of-range dense index → safe default (matches sanitiser fallback).
    return static_cast<uint16_t>(LIGHT_MODE_BLOOM);
}

uint16_t registry_ordinal_to_dense(uint16_t ordinal) {
    const uint16_t span = registry_mode_count();
    uint16_t dense = 0;
    for (uint16_t ord = 0; ord < span; ord++) {
        if (ord == ordinal) return dense;           // enabled: its own index;
                                                    // disabled: next-enabled index
        if (registry_mode_is_enabled(ord)) dense++;
    }
    return dense;  // ordinal beyond span → end of menu
}

uint8_t registry_sanitize_persisted(uint8_t mode) {
    // A persisted ordinal that owns a registry row is kept. Legacy ordinals
    // (< NUM_MODES) resolve through entry_for_legacy_ordinal(); native runtime
    // ordinals (>= NUM_MODES, registry-build only) resolve through
    // entry_for_runtime_ordinal(). Anything unmapped clamps to BLOOM. The
    // persisted field stays uint8_t and NUM_MODES is not widened.
    if (entry_for_runtime_ordinal(static_cast<uint16_t>(mode)) != nullptr) {
        return mode;
    }
    return static_cast<uint8_t>(LIGHT_MODE_BLOOM);
}

bool registry_boot() {
    registry_ensure();
    g_registry_healthy = registry_validate();
    return g_registry_healthy;
}

}  // namespace framework
}  // namespace effects
}  // namespace k1

#endif  // K1_EFFECT_REGISTRY_V1
