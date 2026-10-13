// ============================================================================
//  k1_render_trace.h — LED-level render capture (diagnostic envs only)
//
//  Gated ENTIRELY on K1_RENDER_TRACE_V1. MEASUREMENT instrument, not a
//  product feature. Arm → tick → dump: PSRAM ring, no live printf on the
//  render path (firmware-telemetry-instrumentation).
//
//  Two artefact taps (only one fires per env):
//    k1_render_trace_on_frame     WS2812 path: post-gamma RGB8 leds_out
//    k1_render_trace_on_frame16   Lever-2 path: packed WS2816 wire
//                                 (6 bytes/logical LED, GRB 16-bit split)
//                                 MUST be called before the Lever-2 return
//                                 in show_leds — leds_out is never filled.
//
//  Serial surface (typed, CMD_HARNESS):
//    :rtrace_arm=<seconds 1..600>[,<every_n 1..100>]
//    :rtrace_status=1
//    :rtrace_dump=1    [RTRACE-BEGIN fmt=rgb8hex|rgb16hex ...] ... [RTRACE-END]
//
//  rgb16hex dump is unpacked R16BE G16BE B16BE per pixel (host occupancy).
//  Decoder: hue_coverage.py (rgb8) / score_rtrace_occupancy.py (rgb16).
//  B489 dual extension: edges=2, F,index,millis,primary_mode,RGB16,RGB16;
//  CRC covers both padded 160-pixel GRB16 edge slots in emitted frame order.
//  Legacy single-edge marker/CRC stride and capacity 3000 remain unchanged.
//  B489 dual capacity is 2000.
//  B489 dump returns immediately and drains on a diagnostic task. Stop serial
//  diagnostic streams before requesting it and send no commands until END;
//  music processing/rendering continue. Arm is rejected while drain is busy.
// ============================================================================
#ifdef K1_RENDER_TRACE_V1
#ifndef K1_RENDER_TRACE_H
#define K1_RENDER_TRACE_H

#include <stdint.h>
#include <stddef.h>

void k1_render_trace_on_frame(const uint8_t* rgb_bytes, uint16_t led_count,
                              uint8_t lightshow_mode);

void k1_render_trace_on_frame16(const uint8_t* packed6, uint16_t led_count,
                                uint8_t lightshow_mode);

#ifdef K1_B489_WS2816_V1
// Score qualification tap: capture the two registered logical-edge buffers in
// the same frame. A primary-only dump cannot prove secondary coherence or the
// four physical DIN submissions driven from these two 960-byte buffers.
void k1_render_trace_on_frame16_dual(const uint8_t* primary_packed6,
                                     const uint8_t* secondary_packed6,
                                     uint16_t led_count,
                                     uint8_t lightshow_mode);

#endif

// Diagnostic paint: when arm args include ",stim", overwrite leds_scaled
// with a TRUE16 ramp so occupancy can be scored without live audio.
bool k1_render_trace_stim_active(void);

bool k1_render_trace_dispatch(const char* command_type, char* command_data);

#endif  // K1_RENDER_TRACE_H
#endif  // K1_RENDER_TRACE_V1
