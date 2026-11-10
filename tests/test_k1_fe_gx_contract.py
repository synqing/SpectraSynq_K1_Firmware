"""Exercise actual Gx startup, power policy and logical-pixel limiter on host.

GPIO/ADC/clock/serial use test doubles; production C++ performs all decisions.
This proves source behaviour, not measured CC accuracy, load current or timing.
"""
from pathlib import Path
import json
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[1]
FW = ROOT / "SPECTRASYNQ_K1_FIRMWARE"


def _compiler():
    result = shutil.which("g++-16") or shutil.which("g++")
    assert result, "C++17 host compiler required"
    return result


def _build_run(tmp_path, sources, flags=()):
    output = tmp_path / "gx_host"
    command = [_compiler(), "-std=c++17", "-O1", "-g", "-Wall", "-Wextra",
               "-Werror", "-fsanitize=address,undefined",
               "-fno-sanitize-recover=all", f"-I{tmp_path}",
               f"-I{FW / 'system'}", f"-I{FW / 'visual'}", *flags,
               *map(str, sources), "-o", str(output)]
    built = subprocess.run(command, text=True, capture_output=True)
    assert built.returncode == 0, built.stdout + built.stderr
    run = subprocess.run([str(output)], text=True, capture_output=True)
    assert run.returncode == 0, run.stdout + run.stderr
    print(run.stdout, end="")


def test_gx_pin_contract_matches_frozen_native_board(tmp_path):
    fixture = json.loads((Path(__file__).parent / "fixtures/k1_fe_gx_native_pin_map.json").read_text())
    result = subprocess.run([_compiler(), "-E", "-dM", "-x", "c++",
                             "-DK1_FE_BOARD_V1", "-DK1_FE_BOARD_GX",
                             str(FW / "system/k1_fe_board.h")],
                            capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    macros = {line.split()[1]: line.split()[2] for line in result.stdout.splitlines()
              if line.startswith("#define ") and len(line.split()) == 3}
    observed = {name: int(macros[name]) for name in fixture["gpio_by_macro"]}
    assert observed == fixture["gpio_by_macro"]
    assert not set(observed.values()) & {35, 36, 37}
    assert len(set(observed.values())) == len(observed)


def test_gx_source_and_two_edge_current_model(tmp_path):
    _build_run(tmp_path, [Path(__file__).with_name("k1_fe_gx_power_host.cpp")])


def test_actual_gx_startup_and_power_handoff(tmp_path):
    (tmp_path / "driver").mkdir()
    (tmp_path / "Arduino.h").write_text(r'''
#pragma once
#include <stdint.h>
#include <stdarg.h>
#include <stdio.h>
#include <string>
inline uint32_t test_now = 0;
inline int test_levels[49] = {};
inline int test_modes[49] = {};
inline uint32_t test_adc_mv[49] = {};
inline bool test_adc_pin[49] = {};
inline uint32_t millis() { return test_now; }
inline int digitalRead(int pin) { return test_levels[pin]; }
inline uint32_t analogReadMilliVolts(int pin) { test_adc_pin[pin]=true; return test_adc_mv[pin]; }
inline void analogSetPinAttenuation(int, int) {}
constexpr int ADC_11db = 3;
struct TestSerial {
  std::string log;
  void printf(const char* format, ...) {
    char buffer[1024]; va_list ap; va_start(ap,format);
    vsnprintf(buffer,sizeof(buffer),format,ap); va_end(ap); log += buffer;
  }
  void println(const char* text) { log += text; log += '\n'; }
};
inline TestSerial Serial;
''')
    (tmp_path / "Wire.h").write_text(r'''
#pragma once
struct TestWire { bool begin(int sda,int scl,int hz) { return sda==2 && scl==1 && hz==100000; } };
inline TestWire Wire;
''')
    (tmp_path / "driver/gpio.h").write_text(r'''
#pragma once
#include "Arduino.h"
using gpio_num_t = int;
constexpr int GPIO_MODE_INPUT=1, GPIO_MODE_OUTPUT=2;
constexpr int GPIO_PULLUP_DISABLE=0, GPIO_PULLDOWN_DISABLE=0, GPIO_INTR_DISABLE=0;
struct gpio_config_t { uint64_t pin_bit_mask; int mode,pull_up_en,pull_down_en,intr_type; };
inline int gpio_set_level(int pin,int value) { test_levels[pin]=value; return 0; }
inline int gpio_config(const gpio_config_t* c) {
  for(int i=0;i<49;++i) if(c->pin_bit_mask & (1ull<<i)) test_modes[i]=c->mode;
  return 0;
}
''')
    (tmp_path / "k1_pcm1808_input.h").write_text(r'''
#pragma once
inline bool k1_pcm1808_clock_gate_pass() { return true; }
inline void k1_pcm1808_print_telemetry() {}
''')
    _build_run(tmp_path,
               [Path(__file__).with_name("k1_fe_gx_board_host.cpp"),
                FW / "system/k1_fe_board.cpp"],
               ["-DK1_FE_BOARD_V1", "-DK1_FE_BOARD_GX", "-DK1_PCM1808_LINE_SWITCH=1"])


def _production_function(source, name):
    start = source.index("inline void " + name + "(")
    brace = source.index("{", start)
    depth = 0
    for pos in range(brace, len(source)):
        depth += (source[pos] == "{") - (source[pos] == "}")
        if depth == 0:
            return source[start:pos + 1]
    raise AssertionError("unbalanced production function " + name)


def test_actual_gx_brightness_composition_and_output(tmp_path):
    (tmp_path / "Arduino.h").write_text("#pragma once\n#include <stdint.h>\n")
    (tmp_path / "FastLED.h").write_text(r'''
#pragma once
#include <stdint.h>
struct CRGB {
  uint8_t r=0,g=0,b=0;
  CRGB() = default;
  CRGB(uint8_t rr,uint8_t gg,uint8_t bb):r(rr),g(gg),b(bb){}
  void nscale8_video(uint8_t) {} // unused RGB8 convenience packer
};
static_assert(sizeof(CRGB)==3,"raw RGB carrier layout");
''')
    production = (FW / "visual/led_utilities.h").read_text()
    (tmp_path / "gx_output_integration.h").write_text("\n".join(
        _production_function(production, name) for name in
        ("apply_brightness", "apply_brightness_secondary", "k1_fe_gx_prepare", "k1_fe_gx_pack")))
    _build_run(tmp_path, [Path(__file__).with_name("k1_fe_gx_output_host.cpp")],
               ["-DK1_FE_BOARD_GX", "-DK1_LOOK_LIB_V1", "-DK1_DROP_CUT_V1",
                "-DPHOTONS_CURVE_MODE=2", "-fno-exceptions", "-fno-rtti",
                f"-I{ROOT / '.pio/libdeps/k1_fe/FixedPoints/src'}"])
