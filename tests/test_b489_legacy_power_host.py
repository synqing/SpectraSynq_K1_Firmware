"""Compile production native limiter against unchanged FastLED 3.10.3 oracle.

Hardware transport/controller storage uses test doubles; the original estimator,
FixedPoints, look, conversion and packer arithmetic execute on the host.
This establishes a code-space compatibility envelope, not WS2816 current.
"""
from pathlib import Path
import hashlib
import json
import subprocess
import shutil

ROOT = Path(__file__).resolve().parents[1]
VISUAL = ROOT / "SPECTRASYNQ_K1_FIRMWARE/visual"
DEPS = ROOT / ".pio/libdeps/k1_bench_im69d_led150"
ORACLE_SHA256 = "95aefcb6be05286bcf5cd7e01e2e30325871d99178c0247971e4bc664c1eb10c"


def _function(source, name):
    start = source.index("inline void " + name + "(")
    brace = source.index("{", start)
    depth = 0
    for pos in range(brace, len(source)):
        depth += (source[pos] == "{") - (source[pos] == "}")
        if depth == 0:
            return source[start:pos + 1]
    raise AssertionError("unbalanced production function " + name)


def test_native_limit_matches_pinned_fastled_and_production_pack(tmp_path):
    oracle = (DEPS / "FastLED/src/power_mgt.cpp").read_bytes()
    assert hashlib.sha256(oracle).hexdigest() == ORACLE_SHA256
    assert json.loads((DEPS / "FastLED/library.json").read_text())["version"] == "3.10.3"
    # Keep the whole original oracle TU byte-identical; substitute only platform
    # includes/controller access. No cloned estimator in the harness.
    (tmp_path / "oracle.cpp").write_bytes(oracle)
    (tmp_path / "fl").mkdir()
    (tmp_path / "fl/namespace.h").write_text(
        "#define FASTLED_NAMESPACE_BEGIN\n#define FASTLED_NAMESPACE_END\n")
    (tmp_path / "Arduino.h").write_text("#pragma once\n#include <stdint.h>\n")
    (tmp_path / "power_mgt.h").write_text("""
#pragma once
#include <stdint.h>
uint32_t calculate_unscaled_power_mW(const CRGB*, uint16_t);
uint8_t calculate_max_brightness_for_power_mW(const CRGB*, uint16_t, uint8_t, uint32_t);
uint8_t calculate_max_brightness_for_power_mW(uint8_t, uint32_t);
""")
    (tmp_path / "FastLED.h").write_text("""
#pragma once
#include <stdint.h>
namespace fl { using u32 = uint32_t; }
struct CRGB {
 uint8_t r=0,g=0,b=0;
 CRGB() = default;
 CRGB(uint8_t rr,uint8_t gg,uint8_t bb):r(rr),g(gg),b(bb){}
 void nscale8_video(uint8_t) {} // unused RGB8 convenience packer
};
static_assert(sizeof(CRGB)==3, "oracle raw RGB layout");
struct CLEDController {
 CRGB* data=nullptr; uint16_t count=0; CLEDController* link=nullptr;
 static inline CLEDController* first=nullptr;
 static CLEDController* head(){return first;}
 CRGB* leds(){return data;} uint16_t size(){return count;}
 CLEDController* next(){return link;}
};
struct Pin { explicit Pin(uint8_t){} void lo(){} void hi(){} };
struct FastLEDDouble {
 void setMaxPowerInVoltsAndMilliamps(uint8_t,uint32_t){}
 void setMaxPowerInMilliWatts(uint32_t){} void show(){} void delay(uint16_t){}
};
inline FastLEDDouble FastLED;
""")
    production = (VISUAL / "led_utilities.h").read_text()
    (tmp_path / "integration.h").write_text("\n".join(
        _function(production, name) for name in
        ("k1_b489_prepare_native", "k1_b489_pack_limited")))
    binary = tmp_path / "native_power"
    # FixedPoints' in-class constexpr members require its GCC toolchain; clang
    # rejects that dependency before reaching the production functions.
    compiler = shutil.which("g++-16") or shutil.which("g++")
    assert compiler is not None, "GCC host C++ compiler required for FixedPoints"
    command = [compiler, "-std=c++17", "-O1", "-g", "-Wall", "-Wextra",
               "-Werror", "-fno-exceptions", "-fno-rtti",
               "-fsanitize=address,undefined", "-fno-sanitize-recover=all",
               "-DK1_B489_WS2816_V1", "-DK1_LOOK_LIB_V1",
               f"-I{tmp_path}", f"-I{VISUAL}",
               f"-I{DEPS / 'FixedPoints/src'}",
               str(Path(__file__).with_suffix(".cpp")),
               str(tmp_path / "oracle.cpp"), "-o", str(binary)]
    build = subprocess.run(command, capture_output=True, text=True)
    assert build.returncode == 0, build.stdout + build.stderr
    run = subprocess.run([str(binary)], capture_output=True, text=True)
    assert run.returncode == 0, run.stdout + run.stderr
    print(run.stdout, end="")
