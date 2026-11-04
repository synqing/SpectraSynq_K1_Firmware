"""Compile the production capture TU; decode independently packed unequal edges."""
import re
import shutil
import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts/regression-harness"))
from score_rtrace_occupancy import parse_rtrace_occupancy

ARDUINO = r"""
#pragma once
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <mutex>
using portMUX_TYPE = std::mutex;
#define portMUX_INITIALIZER_UNLOCKED {}
#define portENTER_CRITICAL(p) (p)->lock()
#define portEXIT_CRITICAL(p) (p)->unlock()
using StackType_t = uint32_t;
struct StaticTask_t {};
using TaskHandle_t = void*;
#define pdTRUE 1
#define portMAX_DELAY 0xffffffffu
#define tskIDLE_PRIORITY 0
static unsigned notifications = 0;
inline unsigned ulTaskNotifyTake(int, unsigned) { return 1; }
inline TaskHandle_t xTaskCreateStaticPinnedToCore(void (*)(void*), const char*, unsigned,
    void*, unsigned, StackType_t*, StaticTask_t* storage, unsigned) { return storage; }
inline void xTaskNotifyGive(TaskHandle_t) { ++notifications; }
static uint32_t clock_ms = 0;
inline uint32_t millis() { return clock_ms; }
inline void vTaskDelay(unsigned) {}
struct SerialFake {
  template<class... A> void printf(const char* f, A... a) { std::printf(f, a...); }
  void println(const char* s) { std::puts(s); }
  void println() { std::putchar('\n'); }
  void print(const char* s) { std::fputs(s, stdout); }
  void print(char c) { std::putchar(c); }
};
static SerialFake USBSerial;
"""
HARNESS = r"""
#include "visual/k1_render_trace.cpp"
#include <cassert>
#include <string>
static uint8_t primary[960], secondary[960];
static void fill(uint8_t* dst, unsigned edge, unsigned frame) {
  for (unsigned i=0; i<160; ++i) {
    const uint16_t rgb[] = {uint16_t(frame*4096+edge*8192+i*31+1),
                           uint16_t(frame*1024+edge*4096+i*17+513),
                           uint16_t(frame*256+edge*16384+i*7+1027)};
    const unsigned order[] = {1,0,2};
    for (unsigned c=0; c<3; ++c) {
      dst[i*6+c*2] = rgb[order[c]] >> 8;
      dst[i*6+c*2+1] = rgb[order[c]] & 255;
    }
  }
}
int main(int argc, char** argv) {
  std::string action = argc > 1 ? argv[1] : "dual";
  char args[] = "600,1";
  rtrace_arm(args);
  const unsigned allocations_before = allocation_count;
  if (action == "capacity") {
    for (unsigned f=0; f<2100; ++f) {
      clock_ms = f;
      k1_render_trace_on_frame16_dual(primary, secondary, 160, 32);
    }
    assert(s_frames == 2000 && !s_armed);
    assert(allocation_bytes == 3850000);
    assert(allocation_count == allocations_before);
    rtrace_status();
    return 0;
  }
  if (action == "deadline") {
    char short_args[] = "1,1";
    rtrace_arm(short_args);
    clock_ms = 999;
    k1_render_trace_on_frame16_dual(primary, secondary, 4, 32);
    clock_ms = 1000;
    k1_render_trace_on_frame16_dual(primary, secondary, 4, 32);
    assert(s_frames == 1 && !s_armed);
    rtrace_status();
    return 0;
  }
  for (unsigned f=0; f<3; ++f) {
    fill(primary, 0, f); fill(secondary, 1, f);
    clock_ms = 100+f*7;
    if (action == "single") k1_render_trace_on_frame16(primary, 4, 32);
    else k1_render_trace_on_frame16_dual(primary, secondary, 4, 32);
  }
  assert(allocation_count == allocations_before);
  rtrace_dump();
  assert(s_drain_busy && notifications == 1 && !s_armed);
  rtrace_dump();
  assert(notifications == 1 && s_drain_busy);
  const auto frozen_before_drain = s_frames;
  char rejected_arm[] = "1,1";
  rtrace_arm(rejected_arm);
  assert(s_frames == frozen_before_drain && s_drain_busy);
  // Explicitly run the notified production drain once; the fake scheduler
  // deliberately does not run it in xTaskNotifyGive, proving request is async.
  rtrace_drain_once();
  assert(!s_drain_busy);
  const auto frozen = s_frames;
  k1_render_trace_on_frame16_dual(primary, secondary, 4, 32);
  assert(s_frames == frozen && !s_armed);
}
"""


def compile_capture(tmp, harness, defines):
    (tmp / "visual").mkdir()
    (tmp / "system").mkdir()
    for name in ("k1_render_trace.cpp", "k1_render_trace.h"):
        shutil.copyfile(ROOT / "SPECTRASYNQ_K1_FIRMWARE/visual" / name, tmp / "visual" / name)
    (tmp / "system/globals.h").write_text("")
    (tmp / "Arduino.h").write_text(ARDUINO)
    (tmp / "esp32-hal-psram.h").write_text(
        '#pragma once\nstatic unsigned allocation_count = 0;\nstatic size_t allocation_bytes = 0;\n'
        'inline void* ps_malloc(size_t n) { ++allocation_count; allocation_bytes += n; return malloc(n); }\n')
    # Independent bitwise IEEE CRC, compared with the decoder's zlib CRC.
    (tmp / "esp_crc.h").write_text(r"""
#pragma once
inline uint32_t esp_crc32_le(uint32_t crc, const uint8_t* p, size_t n) {
  crc = ~crc;
  for (size_t i=0; i<n; ++i) {
    crc ^= p[i];
    for (unsigned b=0; b<8; ++b) crc = (crc >> 1) ^ ((crc & 1) ? 0xedb88320u : 0u);
  }
  return ~crc;
}
""")
    (tmp / "harness.cpp").write_text(harness)
    binary = tmp / "capture"
    subprocess.run(["clang++", "-std=c++17", "-Wall", "-Wextra", "-Werror",
                    "-fsanitize=address,undefined", "-DK1_RENDER_TRACE_V1",
                    *defines, "-I", str(tmp), str(tmp / "harness.cpp"),
                    "-o", str(binary)], check=True, capture_output=True, text=True)
    return binary


@pytest.fixture(scope="module")
def capture_binary(tmp_path_factory):
    return compile_capture(tmp_path_factory.mktemp("rtrace-product"), HARNESS,
                           ["-DK1_B489_WS2816_V1"])


def test_legacy_product_preserves_allocation_and_capacity(tmp_path):
    harness = r"""
#include "visual/k1_render_trace.cpp"
#include <cassert>
int main() {
  char args[] = "600,1";
  rtrace_arm(args);
  assert(allocation_count == 3 && allocation_bytes == 2895000);
  uint8_t wire[960] = {};
  for (unsigned f=0; f<3100; ++f) {
    clock_ms = f;
    k1_render_trace_on_frame16(wire, 160, 32);
  }
  assert(s_frames == 3000 && !s_armed);
  assert(allocation_count == 3 && allocation_bytes == 2895000);
  assert(K1_RTRACE_FRAME_BYTES == 960);
}
"""
    binary = compile_capture(tmp_path, harness, [])
    subprocess.run([str(binary)], check=True, capture_output=True, text=True)


def capture(capture_binary, tmp_path, action="dual"):
    text = subprocess.check_output([str(capture_binary), action], text=True)
    path = tmp_path / "capture.log"
    path.write_text(text)
    return path


@pytest.mark.parametrize("action,edges", [("dual", 2), ("single", 1)])
def test_product_capture_decodes_exact_unequal_channels(capture_binary, tmp_path, action, edges):
    path = capture(capture_binary, tmp_path, action)
    fmt, frames, dropped = parse_rtrace_occupancy(str(path))
    assert fmt == "rgb16hex" and dropped == 0 and len(frames) == 3 * edges
    for index, frame in enumerate(frames):
        f, edge = divmod(index, edges)
        assert (frame["idx"], frame["edge"], frame["ms"], frame["mode"]) == (f, edge, 100+f*7, 32)
        expected = [[f*4096+edge*8192+i*31+1,
                     f*1024+edge*4096+i*17+513,
                     f*256+edge*16384+i*7+1027] for i in range(4)]
        np.testing.assert_array_equal(frame["rgb16"], expected)
        assert frame["crc_verified"]
    if action == "single":
        assert "edges=" not in path.read_text()  # Exact legacy marker/CRC stride.


@pytest.mark.parametrize("action", ["capacity", "deadline"])
def test_product_capture_bounds(capture_binary, tmp_path, action):
    capture(capture_binary, tmp_path, action)


@pytest.mark.parametrize("damage", ["missing_edge", "corrupt", "truncated", "missing_frame",
                                     "duplicate_frame", "zero_crc", "no_crc", "bad_px", "bad_bpp", "zero_edges"])
def test_transport_rejects_damaged_product_capture(capture_binary, tmp_path, damage):
    path = capture(capture_binary, tmp_path)
    lines = path.read_text().splitlines()
    row = next(i for i, line in enumerate(lines) if line.startswith("F,"))
    if damage == "missing_edge":
        lines[row] = lines[row].rsplit(",", 1)[0]
    elif damage == "corrupt":
        lines[row] = lines[row][:-1] + ("0" if lines[row][-1] != "0" else "1")
    elif damage == "truncated":
        lines = lines[:-1]
    elif damage == "missing_frame":
        del lines[row]
    elif damage == "duplicate_frame":
        lines.insert(row, lines[row])
    elif damage == "zero_crc":
        lines = [re.sub(r"crc32=[0-9a-f]+", "crc32=00000000", line) for line in lines]
    elif damage == "no_crc":
        lines = [re.sub(r" crc32=[0-9a-f]+", "", line) for line in lines]
    elif damage == "bad_px":
        lines = [line.replace("px=4", "px=161") for line in lines]
    elif damage == "bad_bpp":
        lines = [line.replace("bpp=16", "bpp=8") for line in lines]
    elif damage == "zero_edges":
        lines = [line.replace("edges=2", "edges=0") for line in lines]
    path.write_text("\n".join(lines) + "\n")
    with pytest.raises(ValueError):
        parse_rtrace_occupancy(str(path))


def test_flag_off_preprocesses_to_empty_translation_unit(tmp_path):
    source = ROOT / "SPECTRASYNQ_K1_FIRMWARE/visual/k1_render_trace.cpp"
    output = subprocess.check_output(["clang++", "-E", "-P", str(source)], text=True)
    assert not output.strip()



def test_reverse_preserves_complete_wire_pixels(tmp_path):
    source = (ROOT / "SPECTRASYNQ_K1_FIRMWARE/visual/led_utilities.h").read_text()
    start = source.index("inline void k1_b489_reverse_packed_pixels(")
    function = source[start:source.index("\n#endif", start)]
    harness = r"""
#include <cstdint>
#include <cstddef>
#include <cassert>
#include <cstring>
FUNCTION
int main() {
  for (uint16_t count : {uint16_t(0), uint16_t(1), uint16_t(5), uint16_t(160)}) {
    uint8_t original[962], actual[962];
    for (unsigned i=0; i<962; ++i) original[i] = uint8_t(i*31+17);
    memcpy(actual, original, sizeof(actual));
    k1_b489_reverse_packed_pixels(actual+1, count);
    assert(actual[0] == original[0] && actual[count*6+1] == original[count*6+1]);
    for (unsigned i=0; i<count; ++i)
      for (unsigned b=0; b<6; ++b)
        assert(actual[1+i*6+b] == original[1+(count-1-i)*6+b]);
    k1_b489_reverse_packed_pixels(actual+1, count);
    assert(memcmp(actual, original, sizeof(actual)) == 0);
  }
}
""".replace("FUNCTION", function).replace("#include <cstring>", "#include <cstring>\n#include <initializer_list>")
    cpp = tmp_path / "reverse.cpp"
    cpp.write_text(harness)
    binary = tmp_path / "reverse"
    subprocess.run(["clang++", "-std=c++17", "-Wall", "-Wextra", "-Werror",
                    "-fsanitize=address,undefined", str(cpp), "-o", str(binary)], check=True)
    subprocess.run([str(binary)], check=True)
