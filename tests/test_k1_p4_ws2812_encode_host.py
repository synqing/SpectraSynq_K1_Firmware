"""Host-check the P4 WS2812 SPI encoder independently of FastLED / IDF."""

from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ENCODE = ROOT / "SPECTRASYNQ_K1_FIRMWARE" / "platform" / "k1_p4_ws2812_encode.h"


def test_ws2812_encode_byte_and_grb_pixel_is_host_runnable():
    src = r"""
#include "k1_p4_ws2812_encode.h"
#include <string.h>
int main(void) {
    uint8_t out[3];
    ws2812_encode_byte(0, out);
    if (out[0] != 0x92u || out[1] != 0x49u || out[2] != 0x24u) {
        return 1;
    }
    ws2812_encode_byte(0xFFu, out);
    if (out[0] != 0xDBu || out[1] != 0x6Du || out[2] != 0xB6u) {
        return 2;
    }
    uint8_t pixel[WS2812_SPI_BYTES_PER_PX];
    uint8_t green[3], red[3], blue[3];
    ws2812_encode_pixel(0x12u, 0x34u, 0x56u, pixel);
    ws2812_encode_byte(0x34u, green);
    ws2812_encode_byte(0x12u, red);
    ws2812_encode_byte(0x56u, blue);
    if (memcmp(&pixel[0], green, 3) != 0) return 3;
    if (memcmp(&pixel[3], red, 3) != 0) return 4;
    if (memcmp(&pixel[6], blue, 3) != 0) return 5;
    if (WS2812_SPI_BYTES_PER_PX != 9u) return 6;
    return 0;
}
"""
    with tempfile.TemporaryDirectory(prefix="k1_p4_ws2812_") as td:
        work = Path(td)
        cfile = work / "enc.c"
        cfile.write_text(src, encoding="utf-8")
        bin_path = work / "enc"
        r = subprocess.run(
            [
                "cc",
                "-std=c11",
                "-Wall",
                "-Werror",
                f"-I{ENCODE.parent}",
                str(cfile),
                "-o",
                str(bin_path),
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        assert r.returncode == 0, r.stderr
        r2 = subprocess.run([str(bin_path)], capture_output=True, text=True, check=False)
        assert r2.returncode == 0, (r2.stdout, r2.stderr)
