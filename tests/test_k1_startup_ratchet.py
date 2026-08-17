"""Gate-5 startup ratchet host proof."""

from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SYS = ROOT / "SPECTRASYNQ_K1_FIRMWARE" / "system"
SRC = SYS / "k1_startup_ratchet.cpp"
HDR = SYS / "k1_startup_ratchet.h"

DRIVER = r'''
#include "k1_startup_ratchet.h"
#include <stdio.h>
#include <string.h>
int main() {
  k1_startup_ratchet_reset();
  k1_startup_ratchet_require(K1_STARTUP_TASK_LED);
  k1_startup_ratchet_note_created(K1_STARTUP_TASK_LED, 0);
  if (!k1_startup_ratchet_is_degraded()) return 1;
  if (strcmp(k1_startup_ratchet_missing_name(), "led_task") != 0) return 2;
  K1StartupRatchetState st;
  k1_startup_ratchet_snapshot(&st);
  if (!st.restart_requested || !st.fault_mask) return 3;
  k1_startup_ratchet_reset();
  k1_startup_ratchet_require(K1_STARTUP_TASK_LED);
  k1_startup_ratchet_note_created(K1_STARTUP_TASK_LED, 1);
  k1_startup_ratchet_validate_handle(K1_STARTUP_TASK_LED, (void*)0x1);
  if (k1_startup_ratchet_is_degraded()) return 4;
  puts("PASS");
  return 0;
}
'''


def test_forced_task_creation_failure_reaches_degraded_state():
    with tempfile.TemporaryDirectory(prefix="k1_startup_") as td:
        work = Path(td)
        driver = work / "driver.cpp"
        driver.write_text(DRIVER, encoding="utf-8")
        binary = work / "ratchet"
        subprocess.run(
            [
                "c++",
                "-std=c++17",
                f"-I{SYS}",
                str(driver),
                str(SRC),
                "-o",
                str(binary),
            ],
            check=True,
            capture_output=True,
            text=True,
        )
        result = subprocess.run([str(binary)], capture_output=True, text=True, check=False)
        assert result.returncode == 0, result.stdout + result.stderr
        assert "PASS" in result.stdout


def test_startup_ratchet_sources_exist():
    assert HDR.is_file()
    assert SRC.is_file()
    text = SRC.read_text(encoding="utf-8")
    assert "restart_requested" in text
    assert "led_task" in text
