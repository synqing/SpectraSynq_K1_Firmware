#ifndef K1_GDFT_CORE_H
#define K1_GDFT_CORE_H

#include <stdint.h>

// ============================================================================
// k1_gdft_core.h — Goertzel GDFT transform + novelty (declarations)
// ============================================================================
// Phase A · Lane 1 GDFT decomposition (extraction contract:
// docs/architecture/gdft-decomposition-lane.md). The DEFINITIONS of these two
// functions were lifted WHOLE & VERBATIM out of the legacy header-soup
// `audio/GDFT.h` into `audio/k1_gdft_core.cpp` — a real translation unit — so
// the spectrum tap can be host-compiled + golden-locked, and so the int64
// overflow fix becomes host-deterministic and golden-verifiable.
//
// `GDFT.h` is now a thin shim that `#include`s this header, preserving the
// `.ino`'s existing `#include "GDFT.h"` include path. The function bodies no
// longer live in any header — they live in the .cpp TU (picked up by PIO's
// firmware `.cpp` auto-glob).
//
// Behaviour-preserving by construction: the lifted bodies are statement-
// identical to the originals (same statements, same order, same `#ifdef`
// branches, same `IRAM_ATTR`, same function-static accumulators).
// ============================================================================

// Core 0 (hard real-time): Goertzel GDFT 80-bin analysis + AGC + noise cal.
// IRAM_ATTR is a no-op on host; on device it pins the body to instruction RAM.
void IRAM_ATTR process_GDFT();

// Core 0: spectral novelty (positive-change energy) for transient detection.
void calculate_novelty(uint32_t t_now);

#endif // K1_GDFT_CORE_H
