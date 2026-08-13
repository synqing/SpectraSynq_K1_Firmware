// ============================================================================
//  k1_render_trace.h — colour-fix-lane LED-level render capture (bench only)
//
//  Gated ENTIRELY on K1_RENDER_TRACE_V1 (env k1_bench_im69d_hueaud). This is a
//  MEASUREMENT instrument, not a product feature: it captures the FINAL
//  post-gamma primary output buffer (leds_out — the artefact boundary, the
//  bytes the strip receives) into a PSRAM ring (arm → tick → dump, per the
//  firmware-telemetry-instrumentation discipline — no live printf on the
//  render path) so hue-coverage/entropy can be computed OFFLINE against the
//  palette-derived reference (docs/forensics/colour-fix-lane-2026-08-13.md).
//
//  Serial surface (typed, CMD_HARNESS):
//    :rtrace_arm=<seconds 1..600>[,<every_n 1..100>]  arm; captures every Nth
//                                                     rendered frame (default 4)
//    :rtrace_status=1                                 armed/frames/capacity line
//    :rtrace_dump=1    [RTRACE-BEGIN ...] hex frames [RTRACE-END]; blocking,
//                      post-capture only — render starves during dump by design
//
//  Decoder: scripts/regression-harness/hue_coverage.py (rtrace mode)
// ============================================================================
#ifdef K1_RENDER_TRACE_V1
#ifndef K1_RENDER_TRACE_H
#define K1_RENDER_TRACE_H

#include <stdint.h>
#include <stddef.h>

// Render-path hook: called once per show_leds() on Core 1 with the final
// post-gamma primary buffer. O(n) memcpy while armed, heap-free, silent.
void k1_render_trace_on_frame(const uint8_t* rgb_bytes, uint16_t led_count,
                              uint8_t lightshow_mode);

// Typed serial dispatch for rtrace_arm / rtrace_status / rtrace_dump.
// Returns true when the command was handled. Allocates the PSRAM ring
// lazily on first arm (loud failure if PSRAM refuses).
bool k1_render_trace_dispatch(const char* command_type, char* command_data);

#endif  // K1_RENDER_TRACE_H
#endif  // K1_RENDER_TRACE_V1
