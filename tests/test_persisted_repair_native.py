"""Stage C (Modernes C++ next phase, 10 Nov 2026): saved CONFIG / show / slot
values that are CRC-valid but non-finite must not reach live consumers.

Drives the REAL production code on the host:

* writer process: the real save_config(), k1_show_state_save() and
  k1_preset_slot_save() write the files from a RAM state carrying NaN/Inf, as
  pre-e28dd927 setters could leave it. The on-disk formats are unchanged since
  then, so these are byte-compatible old-firmware files with correct CRCs;
* boot process (fresh globals): the real load_config() then k1_show_state_load()
  in init_fs() order, then the real preset-slot loader;
* second boot: from the files the first boot left, proving the one-time CONFIG
  re-save and no further boot writes.

Only the flash (stubs/LittleFS.h, in-memory) and three unrelated externals
(tempo read, persist-request push, reboot) are host stand-ins. Malformed /
truncated files are produced from the real writer's bytes, never by altering
firmware.
"""

from __future__ import annotations

import math
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts" / "regression-harness" / "golden"))

import oracle_serial_replay as osr  # noqa: E402  (compile recipe: stubs, defines, -I set)

FW = ROOT / "SPECTRASYNQ_K1_FIRMWARE"

DRIVER = r"""
#include <LittleFS.h>
#include "globals.h"
#include "serial_replay_host_stubs.h"
#include "bridge_fs.h"
#include "k1_show_state.h"
#include "k1_effect_queue.h"
#include "k1_tempo.h"
#include <dirent.h>
#include <stdio.h>
#include <stdlib.h>
#include <math.h>

// Unrelated externals of the linked TUs.
K1TempoEvent k1_tempo_read() { K1TempoEvent e = {}; return e; }
bool k1_persist_request_push(const K1PersistRequest&) { return true; }
void reboot() { printf("REBOOT\n"); }

static void dump_fs(const char* dir) {
  for (int i = 0; i < K1_HOST_FS_FILES; i++) {
    if (!k1_host_fs_table[i].used) continue;
    char p[512];
    snprintf(p, sizeof(p), "%s/%s", dir, k1_host_fs_table[i].path + 1);
    FILE* f = fopen(p, "wb");
    fwrite(k1_host_fs_table[i].data, 1, k1_host_fs_table[i].len, f);
    fclose(f);
  }
}
static void load_fs(const char* dir) {
  DIR* d = opendir(dir);
  struct dirent* de;
  while ((de = readdir(d)) != nullptr) {
    if (de->d_name[0] == '.') continue;
    char p[512];
    snprintf(p, sizeof(p), "%s/%s", dir, de->d_name);
    FILE* f = fopen(p, "rb");
    static uint8_t buf[K1_HOST_FS_BYTES];
    const size_t n = fread(buf, 1, sizeof(buf), f);
    fclose(f);
    char path[K1_HOST_FS_PATH];
    snprintf(path, sizeof(path), "/%s", de->d_name);
    k1_host_fs_put(path, buf, n);
  }
  closedir(d);
}
static void pf(const char* tag, const char* name, float v) {
  if (isnan(v)) printf("%s.%s=nan\n", tag, name);
  else if (isinf(v)) printf("%s.%s=%sinf\n", tag, name, v < 0 ? "-" : "");
  else printf("%s.%s=%.9g\n", tag, name, (double)v);
}
static void snap(const char* tag) {
  pf(tag, "PHOTONS", CONFIG.PHOTONS);       pf(tag, "CHROMA", CONFIG.CHROMA);
  pf(tag, "MOOD", CONFIG.MOOD);             pf(tag, "SQUARE_ITER", CONFIG.SQUARE_ITER);
  pf(tag, "SENSITIVITY", CONFIG.SENSITIVITY);
  pf(tag, "INCANDESCENT_FILTER", CONFIG.INCANDESCENT_FILTER);
  pf(tag, "BULB_OPACITY", CONFIG.BULB_OPACITY); pf(tag, "SATURATION", CONFIG.SATURATION);
  pf(tag, "PRISM_COUNT", CONFIG.PRISM_COUNT); pf(tag, "VU_LEVEL_FLOOR", CONFIG.VU_LEVEL_FLOOR);
  pf(tag, "BASE_COAT_INTENSITY", CONFIG.BASE_COAT_INTENSITY);
  printf("%s.PALETTE_INDEX=%u\n", tag, (unsigned)CONFIG.PALETTE_INDEX);
  printf("%s.MIRROR_ENABLED=%u\n", tag, (unsigned)CONFIG.MIRROR_ENABLED);
  printf("%s.MAX_CURRENT_MA=%lu\n", tag, (unsigned long)CONFIG.MAX_CURRENT_MA);
  pf(tag, "S_PHOTONS", SECONDARY_PHOTONS);   pf(tag, "S_CHROMA", SECONDARY_CHROMA);
  pf(tag, "S_MOOD", SECONDARY_MOOD);         pf(tag, "S_SATURATION", SECONDARY_SATURATION);
  pf(tag, "S_PRISM_COUNT", SECONDARY_PRISM_COUNT);
  pf(tag, "S_INCANDESCENT_FILTER", SECONDARY_INCANDESCENT_FILTER);
  pf(tag, "S_BASE_COAT_INTENSITY", SECONDARY_BASE_COAT_INTENSITY);
}
static void defaults_line() {
  pf("default", "PHOTONS", CONFIG_DEFAULTS.PHOTONS);   pf("default", "CHROMA", CONFIG_DEFAULTS.CHROMA);
  pf("default", "SQUARE_ITER", CONFIG_DEFAULTS.SQUARE_ITER);
  pf("default", "BULB_OPACITY", CONFIG_DEFAULTS.BULB_OPACITY);
  pf("default", "SATURATION", CONFIG_DEFAULTS.SATURATION);
  pf("default", "VU_LEVEL_FLOOR", CONFIG_DEFAULTS.VU_LEVEL_FLOOR);
  pf("default", "MOOD", CONFIG_DEFAULTS.MOOD);
}

int main(int argc, char** argv) {
  if (argc < 3) return 2;
  const char* mode = argv[1];
  update_config_filename(FIRMWARE_VERSION);
  defaults_line();
  const float qnan = NAN, pinf = INFINITY;
  if (strcmp(mode, "write") == 0) {
    memcpy(&CONFIG, &CONFIG_DEFAULTS, sizeof(CONFIG));
    CONFIG.PHOTONS = 0.7f; CONFIG.MOOD = 0.3f; CONFIG.SENSITIVITY = 3.0f;
    CONFIG.PALETTE_INDEX = 2; CONFIG.MIRROR_ENABLED = !CONFIG_DEFAULTS.MIRROR_ENABLED;
    CONFIG.BASE_COAT_INTENSITY = 0.25f; CONFIG.PRISM_COUNT = 2.0f; CONFIG.MAX_CURRENT_MA = 1234;
    CONFIG.CHROMA = qnan; CONFIG.SATURATION = pinf;          // carried by the show overlay
    SECONDARY_PHOTONS = qnan; SECONDARY_MOOD = 0.4f;
    SECONDARY_PRISM_COUNT = pinf; SECONDARY_SATURATION = 0.6f;
    if (!k1_show_state_save()) { printf("FAIL show_save\n"); return 3; }
    CONFIG.CHROMA = 0.5f;                                     // CONFIG file differs from the show
    CONFIG.BULB_OPACITY = -pinf; CONFIG.VU_LEVEL_FLOOR = qnan; CONFIG.SQUARE_ITER = qnan;
    save_config();
    if (!k1_preset_slot_save(0, false)) { printf("FAIL slot_save\n"); return 3; }
    dump_fs(argv[2]);
    printf("WROTE\n");
    return 0;
  }
  // boot: fresh process, files only.
  load_fs(argv[2]);
  k1_host_fs_writes = 0;
  load_config();
  snap("after_config");
  printf("show_loaded=%d\n", k1_show_state_load() ? 1 : 0);
  snap("after_show");
  K1ChannelPreset s0 = {};
  printf("slot0_valid=%d\n", k1_preset_slot_get(0, &s0) ? 1 : 0);
  pf("slot0", "photons", s0.photons); pf("slot0", "saturation", s0.saturation);
  pf("slot0", "chroma", s0.chroma);   pf("slot0", "prism_count", s0.prism_count);
  printf("boot_writes=%u\n", k1_host_fs_writes);
  if (argc > 3) dump_fs(argv[3]);
  return 0;
}
"""


def _compile(tmp: Path) -> Path:
    cc = osr._detect_compiler()
    drv = tmp / "persist_drv.cpp"
    drv.write_text(DRIVER, encoding="utf-8")
    exe = tmp / "persist_drv"
    srcs = [FW / s for s in osr.COMMON_SOURCES] + [osr.HOST_GLOBALS] + [
        FW / "control" / "k1_show_state.cpp",
        FW / "control" / "k1_effect_queue.cpp",
        FW / "director" / "k1_edgemixer.cpp",
    ]
    cmd = [cc, "-std=c++17", "-O0", "-fno-fast-math", "-w",
           *[f"-D{d}" for d in osr.DEFINES if d != "K1_SERIAL_REPLAY_HOST"],
           "-I", str(osr.STUBS), "-I", str(ROOT / "scripts" / "regression-harness" / "golden"),
           "-I", str(osr.FIXEDPOINTS), "-I", str(FW),
           *[a for d in osr.FW_SUBDIRS for a in ("-I", str(FW / d))],
           str(drv), *map(str, srcs), "-o", str(exe)]
    r = subprocess.run(cmd, text=True, capture_output=True)
    assert r.returncode == 0, r.stderr[-6000:]
    return exe


def _run(exe: Path, *args: str) -> dict:
    r = subprocess.run([str(exe), *args], text=True, capture_output=True, timeout=120)
    assert r.returncode == 0, r.stdout[-3000:] + r.stderr[-3000:]
    out = {}
    for line in r.stdout.splitlines():
        if "=" in line:
            k, v = line.split("=", 1)
            out[k.strip()] = v.strip()
    out["_stdout"] = r.stdout
    return out


def _f(d: dict, k: str) -> float:
    return float(d[k])


FLOATS = ["PHOTONS", "CHROMA", "MOOD", "SQUARE_ITER", "SENSITIVITY", "INCANDESCENT_FILTER",
          "BULB_OPACITY", "SATURATION", "PRISM_COUNT", "VU_LEVEL_FLOOR", "BASE_COAT_INTENSITY",
          "S_PHOTONS", "S_CHROMA", "S_MOOD", "S_SATURATION", "S_PRISM_COUNT",
          "S_INCANDESCENT_FILTER", "S_BASE_COAT_INTENSITY"]


@pytest.fixture(scope="module")
def exe(tmp_path_factory):
    return _compile(tmp_path_factory.mktemp("persist_build"))


@pytest.fixture(scope="module")
def written(exe, tmp_path_factory):
    d = tmp_path_factory.mktemp("persist_files")
    w = _run(exe, "write", str(d))
    assert "WROTE" in w["_stdout"]
    return d


def test_legacy_nonfinite_values_never_reach_live_state(exe, written, tmp_path):
    after = tmp_path / "after_boot1"
    after.mkdir()
    b = _run(exe, "boot", str(written), str(after))
    # Every live float is finite after the whole restoration order.
    for tag in ("after_config", "after_show"):
        for k in FLOATS:
            assert math.isfinite(_f(b, f"{tag}.{k}")), (tag, k, b[f"{tag}.{k}"])
    assert b["show_loaded"] == "1"
    # CONFIG: non-finite saved fields -> CONFIG_DEFAULTS; healthy values kept.
    assert _f(b, "after_config.BULB_OPACITY") == _f(b, "default.BULB_OPACITY")
    assert _f(b, "after_config.VU_LEVEL_FLOOR") == _f(b, "default.VU_LEVEL_FLOOR")
    assert _f(b, "after_config.SQUARE_ITER") == _f(b, "default.SQUARE_ITER")
    assert _f(b, "after_config.SATURATION") == _f(b, "default.SATURATION")
    assert _f(b, "after_config.CHROMA") == pytest.approx(0.5)
    assert _f(b, "after_config.PHOTONS") == pytest.approx(0.7)
    # Show overlay after CONFIG: a NaN field keeps the repaired CONFIG value
    # instead of undoing it; healthy overlay fields still apply.
    assert _f(b, "after_show.CHROMA") == pytest.approx(0.5)
    assert _f(b, "after_show.SATURATION") == _f(b, "default.SATURATION")
    assert _f(b, "after_show.PRISM_COUNT") == pytest.approx(2.0)
    assert _f(b, "after_show.MOOD") == pytest.approx(0.3)
    assert _f(b, "after_show.BASE_COAT_INTENSITY") == pytest.approx(0.25)
    # Secondary channel: NaN/Inf keep the boot value; healthy ones restore.
    assert _f(b, "after_show.S_PHOTONS") == pytest.approx(1.0)
    assert _f(b, "after_show.S_PRISM_COUNT") == pytest.approx(1.0)
    assert _f(b, "after_show.S_MOOD") == pytest.approx(0.4)
    assert _f(b, "after_show.S_SATURATION") == pytest.approx(0.6)
    # Unrelated settings untouched.
    assert _f(b, "after_show.SENSITIVITY") == pytest.approx(3.0)
    assert b["after_show.PALETTE_INDEX"] == "2"
    assert b["after_show.MAX_CURRENT_MA"] == "1234"
    # Preset slot: Inf saturation -> compiled default; healthy photons kept.
    assert b["slot0_valid"] == "1"
    assert _f(b, "slot0.saturation") == _f(b, "default.SATURATION")
    assert _f(b, "slot0.photons") == pytest.approx(0.7)
    # One clean re-save of CONFIG on the repairing boot, no reboot.
    assert int(b["boot_writes"]) >= 1
    assert "REBOOT" not in b["_stdout"]
    # Second boot from what the first left: CONFIG clean, no further writes,
    # same live result (show still repaired in RAM; it is rewritten only by an
    # explicit save).
    b2 = _run(exe, "boot", str(after))
    assert b2["boot_writes"] == "0"
    for k in FLOATS:
        assert b2[f"after_show.{k}"] == b[f"after_show.{k}"], k


def test_malformed_files_keep_existing_policy(exe, written, tmp_path):
    # Truncated CONFIG (real writer's bytes, cut short): unchanged N1 policy —
    # compiled defaults in RAM, one re-save, no reboot/delete.
    trunc = tmp_path / "trunc"
    trunc.mkdir()
    for f in written.iterdir():
        data = f.read_bytes()
        if f.name.startswith("CONFIG_"):
            data = data[:100]
        (trunc / f.name).write_bytes(data)
    t = _run(exe, "boot", str(trunc))
    for k in ("PHOTONS", "CHROMA", "MOOD"):
        assert _f(t, f"after_config.{k}") == _f(t, f"default.{k}")
    assert int(t["boot_writes"]) >= 1 and "REBOOT" not in t["_stdout"]
    # Corrupt show CRC (one payload byte flipped): soft no-op, CONFIG stands.
    bad = tmp_path / "badshow"
    bad.mkdir()
    for f in written.iterdir():
        data = bytearray(f.read_bytes())
        if f.name.startswith("SHOW_STATE"):
            data[20] ^= 0x40
        (bad / f.name).write_bytes(bytes(data))
    s = _run(exe, "boot", str(bad))
    assert s["show_loaded"] == "0"
    for k in FLOATS:
        assert s[f"after_show.{k}"] == s[f"after_config.{k}"], k
