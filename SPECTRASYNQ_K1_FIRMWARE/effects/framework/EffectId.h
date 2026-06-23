/**
 * @file EffectId.h
 * @brief Stable effect identifier type for the K1 effect framework.
 *
 * P1 minimal port. In firmware-v3 the concrete ID constants live in an
 * auto-generated `effect_ids.h` (200+ EIDs from inventory.json). That registry
 * is OUT OF SCOPE for the self-contained spine — it arrives with the catalog
 * batches (later phase). For P1 we port only the ID *type* and the invalid
 * sentinel so EffectMetadata and the interface compile.
 *
 * TODO(P7 catalog): replace/extend with the generated EID constant set when the
 *   v3 effect catalogue is ported. Keep the type width (uint16_t) and the
 *   high-byte=family / low-byte=sequence convention from v3.
 *
 * Namespace: `k1::effects::framework`. Clean names only.
 * British English in comments and identifiers.
 */

#pragma once

#include <cstdint>

namespace k1 {
namespace effects {
namespace framework {

/// Stable namespaced effect identifier. High byte = family, low byte = sequence.
using EffectId = uint16_t;

/// Sentinel: metadata not yet registered / invalid.
constexpr EffectId INVALID_EFFECT_ID = 0xFFFF;

}  // namespace framework
}  // namespace effects
}  // namespace k1
