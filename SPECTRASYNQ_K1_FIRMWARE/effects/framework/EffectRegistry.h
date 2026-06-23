/**
 * @file EffectRegistry.h
 * @brief Single append-only EffectEntry table — the sole effect-registration
 *        authority for the K1 effect framework (R1 foundation).
 *
 * One self-describing row per effect carries: a stable namespaced id, stable +
 * display names, a metadata pointer, an IEffect* renderer (a LegacyEffectAdapter
 * for legacy light_mode_* effects, or a native v3 IEffect singleton), enable /
 * director bits, an audio-dependency mask, and a legacy-ordinal bridge key.
 * Every future consumer (dispatch, name, enable, cycle, director, NVS resolve,
 * VP probe) is intended to derive from this one table — there is no second file
 * to forget.
 *
 * R1 SCOPE — additive foundation ONLY. This TU DEFINES the table, the lookup
 * API, and the boot self-check. It does NOT rewire any consumer (that is R2).
 * Nothing in the production render path calls it yet.
 *
 * Identifier scheme (Fork F1 — ordinal-aliasing, Captain-ratified):
 *   - Legacy family 0x00: stable_id low byte == lightshow_modes ordinal EXACTLY,
 *     so migration from a persisted ordinal is a cast (no lookup table). The
 *     static_assert in the .cpp enforces low_byte(stable_id) == legacy_ordinal
 *     for every legacy row.
 *   - Native v3 effects use family 0x10 (V3_BEAT), 0x11 (V3_CHORD), 0x12 (V3_LGP);
 *     their legacy_ordinal is kNoLegacy (0xFF).
 *
 * Persistence (Fork F2 — no struct-layout change): the persisted field stays
 * `uint8_t LIGHTSHOW_MODE` (the legacy ordinal). The registry maps ordinal <->
 * stable_id at its boundary. R1 only DEFINES that mapping; consumers are rewired
 * in R2. No `struct conf` change ships here.
 *
 * Compiled ONLY under K1_EFFECT_REGISTRY_V1 (which itself requires
 * K1_EFFECT_FRAMEWORK_V1). The shipping k1_hardware build defines NEITHER flag
 * and never sees this TU, so the production firmware is byte-unchanged.
 *
 * Namespace: `k1::effects::framework`. Clean names only.
 * British English in comments and identifiers.
 */

#pragma once

#include <cstdint>

#include "EffectId.h"        // using EffectId = uint16_t; INVALID_EFFECT_ID
#include "EffectMetadata.h"  // EffectMetadata, EffectCategory, EffectRoleFlags
#include "IEffect.h"         // IEffect interface

namespace k1 {
namespace effects {
namespace framework {

// ─── Family bytes (high byte of stable_id) ──────────────────────────────────
constexpr uint8_t kFamilyLegacy  = 0x00;  // low byte == lightshow_modes ordinal
constexpr uint8_t kFamilyV3Beat  = 0x10;  // beat / tempo-reactive native IEffect
constexpr uint8_t kFamilyV3Chord = 0x11;  // chord / harmonic native IEffect
constexpr uint8_t kFamilyV3Lgp   = 0x12;  // LGP-physics native IEffect

/// Sentinel legacy_ordinal for native (non-legacy) rows.
constexpr uint8_t kNoLegacy = 0xFF;

/// High byte (family) of a stable id.
constexpr uint8_t effect_family(EffectId id) {
    return static_cast<uint8_t>((id >> 8) & 0xFF);
}

/// Low byte (sequence; == legacy ordinal for the legacy family) of a stable id.
constexpr uint8_t effect_sequence(EffectId id) {
    return static_cast<uint8_t>(id & 0xFF);
}

// ─── Audio-signal dependency mask ───────────────────────────────────────────
/// Lets a future director pre-filter rows by lock state (e.g. skip a BEAT row
/// while tempo confidence is below the lock floor) instead of relying on
/// per-effect runtime guards. Stored as a raw mask; combine with the operators
/// below. A scoped enum keeps the values type-checked at row-declaration sites.
enum class AudioDeps : uint8_t {
    NONE  = 0,
    BEAT  = 1u << 0,   // needs tempo lock / beat phase
    ONSET = 1u << 1,   // needs per-band onset
    CHORD = 1u << 2,   // needs chord / harmonic saliency
    LEVEL = 1u << 3,   // needs broadband level only (always available)
};

/// Bitwise OR for AudioDeps (scoped enum → explicit operator).
constexpr AudioDeps operator|(AudioDeps a, AudioDeps b) {
    return static_cast<AudioDeps>(static_cast<uint8_t>(a) |
                                  static_cast<uint8_t>(b));
}

/// Bitwise AND for AudioDeps (membership test).
constexpr AudioDeps operator&(AudioDeps a, AudioDeps b) {
    return static_cast<AudioDeps>(static_cast<uint8_t>(a) &
                                  static_cast<uint8_t>(b));
}

/// True if `dep` is set within `deps`.
constexpr bool hasAudioDep(AudioDeps deps, AudioDeps dep) {
    return static_cast<uint8_t>(deps & dep) != 0;
}

// ─── EffectEntry — THE single source of truth. Append-only. ─────────────────
/**
 * @brief One self-describing effect row.
 *
 * `metadata` and `effect` are bound lazily in registry_ensure() (they are not
 * constexpr — the native renderers are singletons in other TUs and the legacy
 * adapters live in a .bss table). The id / name / flag fields ARE constant and
 * are static_assert-checked at compile time.
 */
struct EffectEntry {
    EffectId              stable_id;       // permanent: high byte family, low byte sequence
    const char*           stable_name;     // immutable token (logs, future NVS-by-name). .rodata
    const char*           display_name;    // UI / serial label; may change. .rodata
    const EffectMetadata* metadata;        // bound in registry_ensure(); never null after bind
    IEffect*              effect;          // bound in registry_ensure(); never null after bind
    bool                  enabled;         // user-selectable; false = present-but-unreachable (id kept stable)
    bool                  director_ok;     // director may auto-select this row
    AudioDeps             audio_deps;      // director pre-filter mask
    uint8_t               legacy_ordinal;  // lightshow_modes value for legacy rows; kNoLegacy for native
};

// ─── Lookup API (the ONLY way any consumer reaches an effect) ───────────────

/// Core-0 lazy bind of every row's `metadata` + `effect` pointers. Idempotent.
/// Safe against C++ static-init order: pointers are bound on first touch (off
/// the render hot path), never via a TU-spanning static constructor table.
void registry_ensure();

/// Pointer to the (bound) table. Calls registry_ensure() first.
const EffectEntry* effect_registry();

/// Number of rows in the table.
uint16_t effect_registry_count();

/// Row for a stable id, or nullptr if absent.
const EffectEntry* entry_for_stable_id(EffectId id);

/// Row for a legacy lightshow_modes ordinal, or nullptr if no legacy row aliases it.
const EffectEntry* entry_for_legacy_ordinal(uint8_t ordinal);

/// Boot self-check (Core 0). Returns false if any row has a null effect or
/// metadata after bind, a duplicate stable id, or a legacy row whose ordinal
/// does not alias its id. A false result means halt-before-render.
bool registry_validate();

// ─── R2-core: native selectability through the uint8 LIGHTSHOW_MODE path ────
//
// The native v3 effects carry legacy_ordinal == kNoLegacy, so the persisted
// `uint8_t LIGHTSHOW_MODE` ordinal space (0..NUM_MODES-1) cannot reach them.
// To make them selectable WITHOUT widening any persisted field, the registry
// appends RUNTIME ordinals for the natives at NUM_MODES..NUM_MODES+N-1. These
// ordinals exist ONLY in the registry build (under K1_EFFECT_REGISTRY_V1); the
// stored field stays a uint8_t. A native ordinal persisted in the registry
// build is out-of-range in a rollback firmware, where the existing
// light_mode_sanitize_persisted() clamps it to BLOOM — accepted + documented;
// the persisted TYPE never changes.
//
// kRegistryModeCount == NUM_MODES + native count. Selection / director / name /
// enable code that wants the natives iterates to registry_mode_count() under
// the flag instead of NUM_MODES.

/// Number of native (non-legacy) rows appended after the legacy ordinal space.
uint16_t registry_native_count();

/// Total runtime ordinal count (NUM_MODES + native count). Grows only in the
/// registry build; the persisted field stays uint8_t.
uint16_t registry_mode_count();

/// Stable id for a runtime ordinal. Legacy ordinals (< NUM_MODES) alias their
/// stable id directly; native ordinals (NUM_MODES..registry_mode_count()-1)
/// resolve through the appended native mapping. Returns INVALID_EFFECT_ID for
/// an out-of-range ordinal.
EffectId stable_id_for_runtime_ordinal(uint16_t ordinal);

/// Registry row for a runtime ordinal (legacy or appended native), or nullptr.
const EffectEntry* entry_for_runtime_ordinal(uint16_t ordinal);

/// Display name for a runtime ordinal, derived from the registry row. Returns
/// nullptr when no row owns the ordinal (caller falls back to the legacy table).
const char* registry_display_name(uint16_t ordinal);

/// Whether a runtime ordinal is user-selectable, derived from the registry row.
/// Native ordinals are governed by their row's `enabled` bit. Returns false for
/// an unmapped ordinal.
bool registry_mode_is_enabled(uint16_t ordinal);

/// Whether the registry passed its boot self-check. Set by registry_boot();
/// consumers fall back to the legacy path when this is false (fail-safe).
bool registry_is_healthy();

// ─── R5: dense (gap-free) navigation index ──────────────────────────────────
//
// The runtime ordinal space (0..registry_mode_count()-1) has HOLES: disabled
// legacy modes keep their ordinal for NVS ID-stability but are unselectable, so
// a user stepping through modes sees gaps (… 9, 11, 12 …) and the natives jump
// to NUM_MODES+. The DENSE index is the gap-free menu position over ENABLED
// runtime ordinals only — legacy-enabled in enum order, then the natives — so
// the user-facing numbering is 0..registry_dense_count()-1 with no holes.
//
// This is a PRESENTATION layer only: the persisted field stays the real uint8
// ordinal (presets/NVS untouched). These convert the number the user types /
// sees at the serial boundary; nothing in storage or render order changes.

/// Count of selectable (enabled) runtime ordinals = the gap-free menu length.
uint16_t registry_dense_count();

/// Dense menu index -> real runtime ordinal. Out-of-range clamps to BLOOM.
uint16_t registry_dense_to_ordinal(uint16_t dense_index);

/// Real runtime ordinal -> dense menu index. A disabled ordinal maps to the
/// dense index of the next enabled effect (sensible display fallback).
uint16_t registry_ordinal_to_dense(uint16_t ordinal);

// ─── R2b consumer surface ───────────────────────────────────────────────────

/// Compile-time count of native (non-legacy) runtime ordinals the registry
/// appends after the legacy ordinal space. Exposed as a constant so consumers
/// that cannot see the private `k_native_count` (e.g. the VP probe's collision
/// guard) can still reason about the full runtime span at compile time. Kept in
/// lock-step with the live native rows by a static_assert in the .cpp.
constexpr uint16_t kRegistryNativeReserve = 5;

/// Registry-backed NVS sanitiser (R2b CL-5/F2). Replaces the legacy
/// light_mode_sanitize_persisted() at its call sites under the registry flag so
/// the persisted ordinal is validated against the single source of truth.
///
/// Contract (persisted TYPE stays uint8_t; NUM_MODES NOT widened):
///   - An ordinal that maps to a valid registry row is KEPT as-is.
///   - An out-of-range / unmapped ordinal clamps to LIGHT_MODE_BLOOM.
///
/// Rollback behaviour (documented, accepted): a native runtime ordinal
/// (>= NUM_MODES) saved by a registry build, read by a non-registry build, is
/// out-of-range there and the legacy sanitiser clamps it to BLOOM. The persisted
/// field is never widened, so there is no blob corruption — only the clamp.
uint8_t registry_sanitize_persisted(uint8_t mode);

/// One-shot boot bind + self-check (Core 0). Calls registry_ensure() then
/// registry_validate(), latches the result for registry_is_healthy(). Returns
/// the health result. Safe to call more than once.
bool registry_boot();

}  // namespace framework
}  // namespace effects
}  // namespace k1
