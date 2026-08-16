"""Gate-7A persistence request boundary (no filesystem)."""

from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PERSIST = ROOT / "SPECTRASYNQ_K1_FIRMWARE" / "persistence"

DRIVER = r'''
#include "k1_persistence_request.h"
#include <stdio.h>
int main() {
  k1_persist_reset();
  K1PersistRequest a{1, K1_PERSIST_OP_SAVE_CONFIG, 1, 0};
  K1PersistRequest b{2, K1_PERSIST_OP_SAVE_CONFIG, 1, 1};
  K1PersistRequest c{3, K1_PERSIST_OP_SAVE_PRESET, 0, 0};
  if (!k1_persist_request_push(a)) return 1;
  if (!k1_persist_request_push(b)) return 2; // coalesces
  if (!k1_persist_request_push(c)) return 3;
  K1PersistStats st; k1_persist_stats(&st);
  if (st.coalesced != 1) return 4;
  // Fill queue with non-idempotent to force full reject.
  k1_persist_reset();
  for (uint32_t i = 0; i < K1_PERSIST_QUEUE_CAPACITY; i++) {
    K1PersistRequest r{i+1, K1_PERSIST_OP_SAVE_PRESET, 0, (uint16_t)i};
    if (!k1_persist_request_push(r)) return 5;
  }
  K1PersistRequest extra{99, K1_PERSIST_OP_SAVE_PRESET, 0, 9};
  if (k1_persist_request_push(extra)) return 6;
  k1_persist_stats(&st);
  if (st.rejected_full != 1) return 7;
  if (!k1_persist_service_stub_once()) return 8;
  K1PersistResult res;
  if (!k1_persist_result_acquire(&res) || !res.ok) return 9;
  // No filesystem symbols in this TU path: stub only.
  puts("PASS");
  return 0;
}
'''


def test_persistence_boundary_saturation_and_coalesce():
    with tempfile.TemporaryDirectory(prefix="k1_persist_") as td:
        work = Path(td)
        driver = work / "driver.cpp"
        driver.write_text(DRIVER, encoding="utf-8")
        binary = work / "persist"
        subprocess.run(
            [
                "c++",
                "-std=c++17",
                f"-I{PERSIST}",
                str(driver),
                str(PERSIST / "k1_persistence_request.cpp"),
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


def test_persistence_sources_contain_no_filesystem_calls():
    text = (PERSIST / "k1_persistence_request.cpp").read_text(encoding="utf-8")
    for banned in ("LittleFS", "fopen", "SPIFFS", "nvs_set", "EEPROM"):
        assert banned not in text
