// ============================================================================
//  k1_stereo_probe.h — Stage 2 IM69D130 stereo capture instrument (bench only)
//
//  Gated ENTIRELY on K1_MIC_IM69D_STEREO_V1 (env k1_bench_im69d_stereo). This is
//  a MEASUREMENT instrument, not a product feature: it captures the raw
//  interleaved L/R int16 stream into a PSRAM ring (arm → tick → dump, per the
//  firmware-telemetry-instrumentation discipline — no live printf on the audio
//  path) so inter-channel correlation ρ and coherence can be computed OFFLINE
//  with pre-registered criteria (design im69d130-dual-mic-eval-2026-08-05 §5.3).
//
//  Serial surface (typed, CMD_HARNESS):
//    :scap_arm=<seconds 1..24>   arm a capture window (starts on next chunk)
//    :scap_status=1              armed/filled/CRC state, one line
//    :scap_dump=1                [SCAP-BEGIN ...] hex dump [SCAP-END]; blocking,
//                                post-leg only — audio starves during dump by design
//
//  Decoder: scripts/regression-harness/stereo_probe_decode.py
// ============================================================================
#ifdef K1_MIC_IM69D_STEREO_V1
#ifndef K1_STEREO_PROBE_H
#define K1_STEREO_PROBE_H

#include <stdint.h>
#include <stddef.h>

// Allocate the PSRAM ring (call once from setup, after PSRAM init).
void k1_stereo_probe_init();

// Audio-path hook: append one chunk of interleaved L/R frames while armed.
// O(n) memcpy, heap-free, silent. Safe on the hot path.
void k1_stereo_probe_on_chunk(const int16_t* interleaved, uint16_t frames);

// Typed serial dispatch for scap_arm / scap_status / scap_dump.
// Returns true when the command was handled.
bool k1_stereo_probe_dispatch(const char* command_type, char* command_data);

#endif  // K1_STEREO_PROBE_H
#endif  // K1_MIC_IM69D_STEREO_V1
