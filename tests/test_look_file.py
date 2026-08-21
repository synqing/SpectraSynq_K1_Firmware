"""K1LT file ABI — host parse of k1_look_file.h contract."""

from __future__ import annotations

import struct
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts" / "regression-harness" / "golden"))

from oracle_bridge_fs_codec import _find_compiler  # noqa: E402

FW = ROOT / "SPECTRASYNQ_K1_FIRMWARE"
MAGIC = 0x4B314C54
HEADER = FW / "visual" / "k1_look_file.h"


DRIVER = r"""
#define K1_LOOK_LIB_V1 1
#include "k1_look_file.h"
#include <cstdio>
#include <vector>
int main() {
  uint8_t payload[48] = {0};
  // identity-ish matrix Q16 on diagonal 65536
  int32_t m[12] = {65536,0,0,0, 0,65536,0,0, 0,0,65536,0};
  std::memcpy(payload, m, 48);
  uint8_t buf[128];
  size_t n = 0;
  if (!k1_look_build_k1lt(3, 0, payload, 48, buf, sizeof(buf), &n)) {
    std::printf("build_fail\n");
    return 1;
  }
  K1LookParsed p;
  if (!k1_look_parse_k1lt(buf, n, &p) || p.type != 3 || p.payload_bytes != 48) {
    std::printf("parse_fail\n");
    return 1;
  }
  buf[0] ^= 0xFF;
  if (k1_look_parse_k1lt(buf, n, &p)) {
    std::printf("bad_magic_accepted\n");
    return 1;
  }
  buf[0] ^= 0xFF;
  buf[n-1] ^= 0xFF;
  if (k1_look_parse_k1lt(buf, n, &p)) {
    std::printf("bad_crc_accepted\n");
    return 1;
  }
  uint8_t idbuf[128];
  size_t idn = 0;
  if (k1_look_build_k1lt(0, 0, payload, 48, idbuf, sizeof(idbuf), &idn)) {
    std::printf("type0_built\n");
    return 1;
  }
  std::printf("ok\n");
  return 0;
}
"""


def test_k1lt_magic_is_locked_in_header():
    src = HEADER.read_text(encoding="utf-8")
    assert "0x4B314C54" in src
    assert "K1LT_VERSION 1U" in src
    assert "k1_look_slot_path" in src
    assert "/look/%02u.klut" in src


def test_host_parse_cube17_type_accepted():
    cxx = _find_compiler()
    assert cxx
    import subprocess
    import tempfile

    driver = r"""
#define K1_LOOK_LIB_V1 1
#include "k1_look_file.h"
#include <cstdio>
#include <cstring>
int main() {
  uint8_t payload[6] = {0, 1, 2, 3, 4, 5};
  uint8_t buf[64];
  size_t n = 0;
  if (!k1_look_build_k1lt(4, 17, payload, 6, buf, sizeof(buf), &n)) {
    std::printf("build_fail\n");
    return 1;
  }
  K1LookParsed p;
  if (!k1_look_parse_k1lt(buf, n, &p) || p.type != 4 || p.node_n != 17) {
    std::printf("parse_fail\n");
    return 1;
  }
  std::printf("ok\n");
  return 0;
}
"""
    with tempfile.TemporaryDirectory() as td:
        src = Path(td) / "drv.cpp"
        src.write_text('#include <cstdint>\n' + driver, encoding="utf-8")
        binp = Path(td) / "drv"
        cmd = [
            cxx,
            "-std=c++17",
            "-DK1_LOOK_LIB_V1=1",
            "-I",
            str(FW / "visual"),
            "-I",
            str(FW / "persistence"),
            str(src),
            "-o",
            str(binp),
        ]
        r = subprocess.run(cmd, text=True, capture_output=True)
        assert r.returncode == 0, r.stderr
        run = subprocess.run([str(binp)], text=True, capture_output=True)
        assert run.returncode == 0, run.stdout + run.stderr
        assert run.stdout.strip() == "ok"


def test_host_parse_good_file_bad_magic_bad_crc_type0():
    cxx = _find_compiler()
    assert cxx
    import subprocess
    import tempfile

    with tempfile.TemporaryDirectory() as td:
        src = Path(td) / "drv.cpp"
        src.write_text('#include <cstring>\n' + DRIVER, encoding="utf-8")
        binp = Path(td) / "drv"
        cmd = [
            cxx,
            "-std=c++17",
            "-DK1_LOOK_LIB_V1=1",
            "-I",
            str(FW / "visual"),
            "-I",
            str(FW / "persistence"),
            str(src),
            "-o",
            str(binp),
        ]
        r = subprocess.run(cmd, text=True, capture_output=True)
        assert r.returncode == 0, r.stderr
        run = subprocess.run([str(binp)], text=True, capture_output=True)
        assert run.returncode == 0, run.stdout + run.stderr
        assert run.stdout.strip() == "ok"
