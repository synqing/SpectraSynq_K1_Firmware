"""Physical slot map is named, not silently swapped."""

from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HDR = ROOT / "SPECTRASYNQ_K1_FIRMWARE" / "audio" / "k1_pcm1808_map.h"
CPP = (ROOT / "SPECTRASYNQ_K1_FIRMWARE" / "audio" / "k1_pcm1808_input.cpp").read_text(
    encoding="utf-8"
)


def test_map_header_does_not_swap_dma_unpack():
    text = HDR.read_text(encoding="utf-8")
    assert "K1_PCM_SLOT0_PHYSICAL_RIGHT" in text
    assert "K1_PCM_SLOT1_PHYSICAL_LEFT" in text
    assert "k1_pcm_physical_left" in text
    assert "k1_pcm_physical_right" in text
    assert "k1_pcm_physical_mid" in text


def test_capture_path_does_not_reorder_slots():
    assert "k1_pcm1808_unpack_le24(fr)" in CPP
    assert "k1_pcm1808_unpack_le24(fr + 3)" in CPP
    # Slot bytes stay 0..2 then 3..5.
    assert "fr + 3" in CPP


def test_mid_saturates():
    src = r"""
#include "k1_pcm1808_map.h"
#include <stdio.h>
int main() {
  if (k1_pcm_physical_right(1, 9) != 1) return 1;
  if (k1_pcm_physical_left(1, 9) != 9) return 1;
  if (k1_pcm_physical_mid(10, 20) != 15) return 1;
  if (k1_pcm_physical_mid(8388607, 8388607) != 8388607) return 1;
  if (k1_pcm_physical_mid(-8388608, -8388608) != -8388608) return 1;
  return 0;
}
"""
    with tempfile.TemporaryDirectory() as td:
        cpp = Path(td) / "t.cpp"
        exe = Path(td) / "t"
        cpp.write_text(src, encoding="utf-8")
        subprocess.check_call(["c++", "-std=c++17", "-I", str(HDR.parent), str(cpp), "-o", str(exe)])
        subprocess.check_call([str(exe)])
