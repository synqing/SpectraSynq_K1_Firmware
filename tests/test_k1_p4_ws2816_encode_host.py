"""Host-check the P4 adapter encoder independently of FastLED / IDF."""

from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ENCODE = ROOT / "SPECTRASYNQ_K1_FIRMWARE" / "platform" / "k1_p4_ws2816_encode.h"


def _pack(v: int) -> list[int]:
    acc = 0
    for b in range(7, -1, -1):
        acc = (acc << 5) | (0x1C if ((v >> b) & 1) else 0x10)
    return [(acc >> (32 - 8 * i)) & 0xFF for i in range(5)]


def test_ws2816_encode_byte_is_host_runnable():
    zero = _pack(0)
    ff = _pack(0xFF)
    src = f"""
#include "k1_p4_ws2816_encode.h"
int main(void) {{
    uint8_t out[5];
    ws2816_encode_byte(0, out);
    if (out[0] != {zero[0]} || out[1] != {zero[1]} || out[2] != {zero[2]} ||
        out[3] != {zero[3]} || out[4] != {zero[4]}) {{
        return 1;
    }}
    ws2816_encode_byte(0xFF, out);
    if (out[0] != {ff[0]} || out[1] != {ff[1]} || out[2] != {ff[2]} ||
        out[3] != {ff[3]} || out[4] != {ff[4]}) {{
        return 2;
    }}
    return 0;
}}
"""
    with tempfile.TemporaryDirectory(prefix="k1_p4_enc_") as td:
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
