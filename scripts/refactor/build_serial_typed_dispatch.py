#!/usr/bin/env python3
"""Build serial_typed_dispatch.cpp handlers from parse_command ladder (verbatim)."""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MENU_CPP = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "SPECTRASYNQ_K1_FIRMWARE/serial/serial_menu.cpp"
OUT_CPP = ROOT / "SPECTRASYNQ_K1_FIRMWARE/serial/serial_typed_dispatch.cpp"

START = "    // Now react accordingly:"
END = "    // Add backward compatibility for old commands"

HEADER = '''/*----------------------------------------
  SERIAL TYPED COMMAND DISPATCH (Stage B table handlers)
  ----------------------------------------*/
#include "serial_typed_dispatch.h"
#include "serial_cmd_handlers.h"
#include "serial_tx.h"
#include "serial_parse_helpers.h"
#include "globals.h"
#include "constants.h"
#include "k1_smart_director.h"
#include "k1_effect_queue.h"
#include "k1_ap_capture_telemetry.h"
#if ENABLE_DIAG_CAPTURE
#include "diagnostic_capture.h"
#endif
#if ENABLE_VPAB_PROBE
#include "vpab_capture.h"
#endif
#if K1_PIN_EVIDENCE_V1
#include "k1_pin_evidence.h"
#endif
#if ENABLE_VP_MOTION_LAB
#include "vp_motion_lab.h"
#endif
#if K1_EFFECT_REGISTRY_V1
#include "EffectRegistry.h"
#endif

#include <string.h>
#include <stdlib.h>
#include <math.h>

extern void check_current_function();
extern void reboot();
extern void save_config();
extern void save_config_delayed();
extern bool apply_chroma_profile(uint8_t profile);
extern void serial_queue_slot_save(uint8_t slot, bool from_secondary);
extern void serial_queue_slot_load(uint8_t slot, bool target_secondary);
extern void serial_queue_slot_arm(uint8_t slot, bool target_secondary);
extern void vp_print_status();
extern void vp_run_output_probe();
extern void vp_run_secondary_bleed_probe();
extern void vp_perf_command(const char* command_type, const char* command_data);
extern void motion_probe_arm_step(float interval_ms, int size_px, float lum);
extern void motion_probe_arm_flash(int a_px, int b_px, float gap_ms, float lum, float on_ms);
extern void motion_probe_off();
extern void motion_probe_status();
extern void ap_capture_arm(uint32_t ms);
extern void serial_print_k1_loud_guard_status();
extern void serial_cycle_k1_loud_guard_mode();
extern void serial_set_k1_loud_guard(bool value);
extern const char* serial_mode_name(uint8_t mode);
extern char mode_names[];
extern uint8_t light_mode_next_enabled(uint8_t mode, int dir);
extern bool benchmark_running;
extern uint32_t benchmark_start_time;
extern uint32_t system_fps_sum;
extern uint32_t led_fps_sum;
extern uint32_t benchmark_sample_count;
extern const uint32_t benchmark_duration;
extern bool stream_spectrogram;
extern bool stream_chromagram;
extern bool stream_agc_debug;
extern void vp_apply_profile(uint8_t profile);

'''

WRAPPERS = '''
// ---- dispatcher family wrappers ----
bool serial_typed_wrap_pure_setter(const char* command_type, char* command_data) {
  return serial_cmd_dispatch_pure_setter(command_type, command_data);
}
bool serial_typed_wrap_reboot_setter(const char* command_type, char* command_data) {
  return serial_cmd_dispatch_reboot_setter(command_type, command_data);
}
bool serial_typed_wrap_vp_tuning(const char* command_type, char* command_data) {
  return serial_cmd_dispatch_vp_tuning(command_type, command_data);
}
bool serial_typed_wrap_response_gain(const char* command_type, char* command_data) {
  return serial_cmd_dispatch_response_gain(command_type, command_data);
}
bool serial_typed_wrap_queue(const char* command_type, char* command_data) {
  return serial_cmd_dispatch_queue(command_type, command_data);
}
bool serial_typed_wrap_smart_director(const char* command_type, char* command_data) {
  return serial_cmd_dispatch_smart_director(command_type, command_data);
}
bool serial_typed_wrap_smart_visual(const char* command_type, char* command_data) {
  return serial_cmd_dispatch_smart_visual(command_type, command_data);
}
bool serial_typed_wrap_edge_mixer(const char* command_type, char* command_data) {
  return serial_cmd_dispatch_edge_mixer(command_type, command_data);
}
bool serial_typed_wrap_preset(const char* command_type, char* command_data) {
  return serial_cmd_dispatch_preset(command_type, command_data);
}
bool serial_typed_wrap_secondary(const char* command_type, char* command_data) {
  return serial_cmd_dispatch_secondary(command_type, command_data);
}
bool serial_typed_wrap_mode(const char* command_type, char* command_data) {
  return serial_cmd_dispatch_mode(command_type, command_data);
}
#if ENABLE_TEMPO_STREAM && ENABLE_AP_FRONTEND_DEBUG
bool serial_typed_wrap_ap_diag(const char* command_type, char* command_data) {
  return serial_diag_ap_dispatch(command_type, command_data);
}
#endif
#if K1_VIVID_PRECOMP_V1
bool serial_typed_wrap_vivid(const char* command_type, char* command_data) {
  return serial_cmd_dispatch_vivid(command_type, command_data);
}
#endif
#if ENABLE_GDFT_HARNESS
bool serial_typed_wrap_gdft_harness(const char* command_type, char* command_data) {
  return serial_cmd_dispatch_gdft_harness(command_type, command_data);
}
#endif
#if K1_EFFECT_FRAMEWORK_V1
bool serial_typed_wrap_beat_director(const char* command_type, char* command_data) {
  return serial_cmd_dispatch_beat_director(command_type, command_data);
}
#endif

'''


def strip_dispatch_blocks(text: str) -> str:
    """Remove serial_cmd_dispatch_* fan-out arms and ap_diag dispatch arm."""
    patterns = [
        r"\n    //[^\n]*\n(?:    //[^\n]*\n)*#ifdef[^\n]*\n    else if \(serial_cmd_dispatch_\w+\(command_type, command_data\)\) \{\s*\n(?:    //[^\n]*\n)*    \}\n#endif[^\n]*\n",
        r"\n    //[^\n]*\n(?:    //[^\n]*\n)*    else if \(serial_cmd_dispatch_\w+\(command_type, command_data\)\) \{\s*\n(?:    //[^\n]*\n)*    \}\n",
        r"\n#if ENABLE_TEMPO_STREAM && ENABLE_AP_FRONTEND_DEBUG\n    else if \(serial_diag_ap_dispatch\(command_type, command_data\)\) \{ \}\n#endif\n",
    ]
    for pat in patterns:
        text = re.sub(pat, "\n", text, flags=re.MULTILINE)
    return text


def extract_arms(ladder: str) -> str:
    ladder = strip_dispatch_blocks(ladder)
    out: list[str] = []
    # split on command arms
    parts = re.split(r"\n    (?=(?:if|else if) \(strcmp\(command_type)", ladder)
    for part in parts:
        part = part.strip()
        if not part or part.startswith("//"):
            continue
        if "serial_cmd_dispatch_" in part or "serial_diag_ap_dispatch" in part:
            continue
        if part.startswith("if ("):
            part = "else if (" + part[3:]
        m = re.match(
            r'else if \(strcmp\(command_type, "([^"]+)"\) == 0(?:\s*\|\|\s*\n\s*strcmp\(command_type, "([^"]+)"\) == 0)?\)',
            part,
        )
        if not m:
            continue
        name = m.group(1)
        body_start = part.index("{") + 1
        body = part[body_start:].strip()
        if body.endswith("}"):
            body = body[:-1].strip()
        fn = f"serial_typed_{name}"
        out.append(
            f"bool {fn}(const char* command_type, char* command_data) {{\n"
            f"  (void)command_type;\n  {body}\n  return true;\n}}\n"
        )
        if m.group(2):
            # slot_arm shares slot_load body — alias function
            out.append(
                f"bool serial_typed_{m.group(2)}(const char* command_type, char* command_data) {{\n"
                f"  return serial_typed_{name}(command_type, command_data);\n}}\n"
            )
    return "\n".join(out)


def main() -> None:
    text = MENU_CPP.read_text(encoding="utf-8")
    start = text.index(START)
    end = text.index(END, start)
    ladder = text[start:end]
    handlers = extract_arms(ladder)

    # vp_profile used `if` not `else if` — add manually if missing
    if "serial_typed_vp_profile" not in handlers:
        handlers = (
            "bool serial_typed_vp_profile(const char* command_type, char* command_data) {\n"
            "  if (strcmp(command_data, \"original\") == 0) {\n"
            "    vp_apply_profile(VP_PROFILE_ORIGINAL);\n"
            "    vp_print_status();\n"
            "  } else if (strcmp(command_data, \"clean\") == 0) {\n"
            "    vp_apply_profile(VP_PROFILE_CLEAN);\n"
            "    vp_print_status();\n"
            "  } else if (strcmp(command_data, \"candidate\") == 0) {\n"
            "    vp_apply_profile(VP_PROFILE_CANDIDATE);\n"
            "    vp_print_status();\n"
            "  } else {\n"
            "    bad_command(command_type, command_data);\n"
            "  }\n"
            "  return true;\n"
            "}\n\n" + handlers
        )

  # start_benchmark + stream toggles were after deprecated block in ladder — append
    tail = '''
bool serial_typed_start_benchmark(const char* command_type, char* command_data) {
  (void)command_type;
  (void)command_data;
  if (!benchmark_running) {
    benchmark_running = true;
    benchmark_start_time = millis();
    system_fps_sum = 0;
    led_fps_sum = 0;
    benchmark_sample_count = 0;
    ack();
    tx_begin();
    USBSerial.print("Benchmark started (Duration: ");
    USBSerial.print(benchmark_duration / 1000);
    USBSerial.println(" seconds)...");
    tx_end();
  } else {
    tx_begin(true);
    USBSerial.println("Benchmark already running.");
    tx_end(true);
  }
  return true;
}

bool serial_typed_stream_spectrogram(const char* command_type, char* command_data) {
  (void)command_type;
  (void)command_data;
  stream_spectrogram = !stream_spectrogram;
  USBSerial.print("STREAM_SPECTROGRAM: ");
  USBSerial.println(stream_spectrogram);
  return true;
}

bool serial_typed_stream_agc(const char* command_type, char* command_data) {
  (void)command_type;
  (void)command_data;
  stream_agc_debug = !stream_agc_debug;
  USBSerial.print("STREAM_AGC_DEBUG: ");
  USBSerial.println(stream_agc_debug ? "ON" : "OFF");
  return true;
}

bool serial_typed_stream_chromagram(const char* command_type, char* command_data) {
  (void)command_type;
  (void)command_data;
  stream_chromagram = !stream_chromagram;
  USBSerial.print("STREAM_CHROMAGRAM: ");
  USBSerial.println(stream_chromagram);
  return true;
}
'''
    OUT_CPP.write_text(HEADER + WRAPPERS + handlers + tail, encoding="utf-8")
    print(f"Wrote {OUT_CPP} ({OUT_CPP.stat().st_size} bytes)")

if __name__ == "__main__":
    main()
