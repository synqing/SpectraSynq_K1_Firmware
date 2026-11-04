"""Host classification for the PCM1808 PCNT clock gate."""

from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HDR = ROOT / "SPECTRASYNQ_K1_FIRMWARE" / "audio" / "k1_pcm1808_clock_gate.h"


def _run(src: str) -> str:
    with tempfile.TemporaryDirectory() as td:
        cpp = Path(td) / "t.cpp"
        exe = Path(td) / "t"
        cpp.write_text(src, encoding="utf-8")
        subprocess.check_call(
            [
                "c++",
                "-std=c++17",
                "-I",
                str(HDR.parent),
                str(cpp),
                "-o",
                str(exe),
            ]
        )
        return subprocess.check_output([str(exe)], text=True)


def test_classify_48k_pass():
    src = r"""
#include "k1_pcm1808_clock_gate.h"
#include <stdio.h>
int main() {
  auto r = k1_pcmclk_classify(48000.0f, 3072000.0f);
  printf("%s %s %s %.3f\n", r.gate, r.reason, r.mode, r.ratio);
  return r.code == K1_PCMCLK_OK ? 0 : 1;
}
"""
    out = _run(src)
    assert out.startswith("PASS OK 48K_MASTER_I2S24")


def test_classify_96k_fail():
    src = r"""
#include "k1_pcm1808_clock_gate.h"
#include <stdio.h>
int main() {
  auto r = k1_pcmclk_classify(96000.0f, 6144000.0f);
  printf("%s %s\n", r.gate, r.reason);
  return r.code == K1_PCMCLK_STILL_96K ? 0 : 1;
}
"""
    out = _run(src)
    assert "FAIL PCM_STILL_IN_96K_MASTER_MODE" in out


def test_classify_no_clock():
    src = r"""
#include "k1_pcm1808_clock_gate.h"
int main() {
  auto r = k1_pcmclk_classify(0.0f, 0.0f);
  return r.code == K1_PCMCLK_NO_CLOCK ? 0 : 1;
}
"""
    _run(src)


def test_classify_wrong_ratio():
    src = r"""
#include "k1_pcm1808_clock_gate.h"
int main() {
  auto r = k1_pcmclk_classify(48000.0f, 1500000.0f);
  return r.code == K1_PCMCLK_BCLK_RATIO_NOT_64 ? 0 : 1;
}
"""
    _run(src)


def test_hz_from_actual_elapsed():
    src = r"""
#include "k1_pcm1808_clock_gate.h"
#include <stdio.h>
int main() {
  float hz = k1_pcmclk_hz(4800, 100000);
  printf("%.1f\n", hz);
  return (hz > 47999.0f && hz < 48001.0f) ? 0 : 1;
}
"""
    out = _run(src)
    assert out.strip() == "48000.0"
