#!/usr/bin/env python3
"""Behavioural golden-master oracle for the N1 persisted-config blob CODEC.

THE PROBLEM. The structural oracle (oracle_bridge_fs_config.py) PINS the source
of load_config()/save_config(), but those functions drag LittleFS/FreeRTOS and
never host-compile, so the actual RECOVERY DECISION — does a given on-disk blob
LOAD, MIGRATE, or FALL BACK to defaults — was never executed and checked off-device.
N1 deliberately extracted that decision into a FS-FREE header
(persistence/bridge_fs_config_codec.h: ConfigBlobHeader, bridge_fs_crc32,
bridge_fs_classify_config) precisely so it CAN be host-compiled and run. This
oracle is that real proof: it compiles a tiny driver that #includes the codec
header, feeds it the five blob classes the field will produce, and freezes the
decision each one yields.

THE ARGUMENT. Unlike the structural oracle (which pins TEXT and cannot run), this
one OBSERVES BEHAVIOUR: a refactor of the codec internals (e.g. swapping the
table-less CRC for a table-driven one) that preserves the contract REPRODUCES the
golden decisions byte-for-byte; any change to the classify decision table — a
flipped magic/version/crc compare, a moved migrate threshold, a changed fallback
return — diverges at least one blob's recorded decision. That divergence is the
alarm.

THE FIVE BLOB CLASSES (the inputs the field actually produces):
  * valid            — real header + config payload + CORRECT crc        -> LOAD     (0)
  * bad_crc          — header present, payload corrupt so crc mismatches  -> FALLBACK (2)
  * version_skew     — header present, version = CONFIG_BLOB_VERSION+1    -> FALLBACK (2)
  * truncated        — header magic present, file shorter than header+cfg -> FALLBACK (2)
  * headerless_legacy— raw config_size bytes, NO header (pre-N1 image)    -> MIGRATE  (1)

FAULT-EVIDENCE (the Gate-Fα teeth, proven by harness_selftest.py): the MUTATIONS
list flips one decision-bearing line of bridge_fs_config_codec.h per branch —
magic compare, crc compare, version compare, the migrate length threshold, and
the CFG_FALLBACK return value — each MUST change at least one blob's recorded
decision. Every anchor matches EXACTLY ONCE across the firmware tree.

NON-SHIPPING. Host-only (compile + run the codec header against a driver; no
device, no firmware .cpp). Mirrors the oracle PUBLIC INTERFACE
(NAME / capture(firmware_root=None) / MUTATIONS), registered in
harness_selftest.ORACLE_MODULES, gated by test_golden_master.py.
"""

import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

# ---------------------------------------------------------------------------
# Repo layout (mirrors oracle_chord.py)
# ---------------------------------------------------------------------------
ROOT = Path(__file__).resolve().parents[3]          # SpectraSynq_K1_Firmware/
FW   = ROOT / "SPECTRASYNQ_K1_FIRMWARE"

# The codec header lives here; -I points at this dir so the driver's
# #include "bridge_fs_config_codec.h" resolves.
_CODEC_DIR_REL = ("persistence",)
_CODEC_HEADER  = "bridge_fs_config_codec.h"

NAME = "bridge_fs_codec"

# Compiler preference: the codec header is pure C (stdint/stddef/string), so any
# C++17 compiler works — clang++ first (matches oracle_chord.py), g++ fallback.
def _find_compiler():
    return shutil.which("clang++") or shutil.which("g++")


# ---------------------------------------------------------------------------
# C++ driver — builds the five blob classes, classifies each, prints JSON lines.
#
# Output protocol: one JSON object per blob, in a FIXED order:
#   {"blob":"<id>","decision":<0|1|2>}
# decision is the raw ConfigLoadDecision int (CFG_LOAD=0, CFG_MIGRATE=1,
# CFG_FALLBACK=2). ints only — no float variance, fully cross-platform stable.
#
# A small fixed POD config payload (mirrors `struct conf` being trivially
# copyable; the codec is layout-agnostic, it only sees raw bytes + sizes). We use
# a deterministic 64-byte pattern so the CRC is reproducible and a bad-crc blob is
# trivially built by corrupting one payload byte AFTER the header is stamped.
# ---------------------------------------------------------------------------
DRIVER = r"""
#include "bridge_fs_config_codec.h"
#include <cstdio>
#include <cstring>

static const size_t CONFIG_SIZE = 64;  // stand-in for sizeof(conf); codec is size-agnostic

// Deterministic payload so the stamped CRC is reproducible across runs/hosts.
static void fill_payload(uint8_t* p, size_t n) {
    for (size_t i = 0; i < n; i++) p[i] = (uint8_t)((i * 31u + 7u) & 0xFFu);
}

static void emit(const char* id, ConfigLoadDecision d) {
    std::printf("{\"blob\":\"%s\",\"decision\":%d}\n", id, (int)d);
}

int main() {
    const size_t HDR = sizeof(ConfigBlobHeader);

    // ---- valid: header + payload + correct crc -> LOAD ----
    {
        uint8_t buf[HDR + CONFIG_SIZE];
        uint8_t payload[CONFIG_SIZE];
        fill_payload(payload, CONFIG_SIZE);
        ConfigBlobHeader h;
        bridge_fs_fill_header(&h, payload, CONFIG_SIZE);
        std::memcpy(buf, &h, HDR);
        std::memcpy(buf + HDR, payload, CONFIG_SIZE);
        emit("valid", bridge_fs_classify_config(buf, sizeof(buf), CONFIG_SIZE));
    }

    // ---- bad_crc: header valid except one payload byte flipped -> FALLBACK ----
    {
        uint8_t buf[HDR + CONFIG_SIZE];
        uint8_t payload[CONFIG_SIZE];
        fill_payload(payload, CONFIG_SIZE);
        ConfigBlobHeader h;
        bridge_fs_fill_header(&h, payload, CONFIG_SIZE);  // crc over CLEAN payload
        std::memcpy(buf, &h, HDR);
        std::memcpy(buf + HDR, payload, CONFIG_SIZE);
        buf[HDR + 5] ^= 0xFFu;                            // corrupt payload -> crc mismatch
        emit("bad_crc", bridge_fs_classify_config(buf, sizeof(buf), CONFIG_SIZE));
    }

    // ---- version_skew: header valid except version = VERSION+1 -> FALLBACK ----
    {
        uint8_t buf[HDR + CONFIG_SIZE];
        uint8_t payload[CONFIG_SIZE];
        fill_payload(payload, CONFIG_SIZE);
        ConfigBlobHeader h;
        bridge_fs_fill_header(&h, payload, CONFIG_SIZE);
        h.version = (uint16_t)(CONFIG_BLOB_VERSION + 1u);  // unknown future version
        std::memcpy(buf, &h, HDR);
        std::memcpy(buf + HDR, payload, CONFIG_SIZE);
        emit("version_skew", bridge_fs_classify_config(buf, sizeof(buf), CONFIG_SIZE));
    }

    // ---- truncated: magic present but file shorter than header+config -> FALLBACK ----
    {
        uint8_t buf[HDR + CONFIG_SIZE];
        uint8_t payload[CONFIG_SIZE];
        fill_payload(payload, CONFIG_SIZE);
        ConfigBlobHeader h;
        bridge_fs_fill_header(&h, payload, CONFIG_SIZE);
        std::memcpy(buf, &h, HDR);
        std::memcpy(buf + HDR, payload, CONFIG_SIZE);
        // Report a file_len that stops mid-payload: magic at offset 0 is intact,
        // but there are not enough bytes for header+config.
        size_t short_len = HDR + CONFIG_SIZE - 1;
        emit("truncated", bridge_fs_classify_config(buf, short_len, CONFIG_SIZE));
    }

    // ---- headerless_legacy: raw config_size bytes, no header -> MIGRATE ----
    {
        uint8_t buf[CONFIG_SIZE];
        fill_payload(buf, CONFIG_SIZE);            // first 4 bytes != MAGIC (pattern 0x07,0x26,...)
        emit("headerless_legacy", bridge_fs_classify_config(buf, sizeof(buf), CONFIG_SIZE));
    }

    // ---- headered_v1_legacy: valid v1 blob, same payload size -> MIGRATE ----
    // LOOK fields reused trailing pad so sizeof(conf) did not grow; version is
    // the migrate signal. CRC matches the stamped v1 payload.
    {
        uint8_t buf[HDR + CONFIG_SIZE];
        uint8_t payload[CONFIG_SIZE];
        fill_payload(payload, CONFIG_SIZE);
        ConfigBlobHeader h;
        bridge_fs_fill_header(&h, payload, CONFIG_SIZE);
        h.version = CONFIG_BLOB_PRE_LOOK_VERSION;
        std::memcpy(buf, &h, HDR);
        std::memcpy(buf + HDR, payload, CONFIG_SIZE);
        emit("headered_v1_legacy", bridge_fs_classify_config(buf, sizeof(buf), CONFIG_SIZE));
    }

    return 0;
}
"""

# Expected golden decisions, for the __main__ self-check assertion.
EXPECTED = {
    "valid": 0,             # CFG_LOAD
    "bad_crc": 2,           # CFG_FALLBACK
    "version_skew": 2,      # CFG_FALLBACK
    "truncated": 2,         # CFG_FALLBACK
    "headerless_legacy": 1, # CFG_MIGRATE
    "headered_v1_legacy": 1, # CFG_MIGRATE (LOOK layout; do not FALLBACK)
}


# ---------------------------------------------------------------------------
# Compile + run
# ---------------------------------------------------------------------------
def _compile(workdir: Path, firmware_root=None) -> Path:
    fw = Path(firmware_root) if firmware_root else FW
    codec_dir = fw.joinpath(*_CODEC_DIR_REL)
    main_cpp = workdir / "driver.cpp"
    main_cpp.write_text(DRIVER, encoding="utf-8")
    binary = workdir / "oracle_bridge_fs_codec_bin"

    cxx = _find_compiler()
    if not cxx:
        raise RuntimeError("no C++ compiler (clang++/g++) found on PATH")

    cmd = [
        cxx, "-std=c++17",
        "-O0",                       # strict determinism; codec is integer-only anyway
        "-I", str(codec_dir),        # resolves #include "bridge_fs_config_codec.h"
        str(main_cpp),
        "-o", str(binary),
    ]
    r = subprocess.run(cmd, text=True, capture_output=True)
    if r.returncode != 0:
        raise RuntimeError(f"oracle_bridge_fs_codec compile failed:\n{r.stderr}")
    return binary


def _run(binary: Path) -> str:
    r = subprocess.run([str(binary)], text=True, capture_output=True)
    if r.returncode != 0:
        raise RuntimeError(f"oracle_bridge_fs_codec run failed:\n{r.stderr}")
    return r.stdout


def capture(firmware_root=None) -> str:
    """Compile + run the codec driver; return deterministic JSON-lines golden."""
    with tempfile.TemporaryDirectory(prefix="oracle_bridge_fs_codec_") as td:
        binary = _compile(Path(td), firmware_root=firmware_root)
        return _run(binary)


# ---------------------------------------------------------------------------
# Mutations — the Gate-Fα teeth. One per decision branch, each anchoring a line
# IN bridge_fs_config_codec.h and each flipping at least one blob's decision.
# Every anchor matches EXACTLY ONCE across the firmware tree (the codec header is
# the only place these lines exist).
# ---------------------------------------------------------------------------
MUTATIONS = [
    # 1. (magic) FLIP THE MAGIC COMPARE in bridge_fs_classify_config(): require the
    #    header magic to NOT equal MAGIC. The "valid" blob (correct magic) then fails
    #    the headered-validate path; with magic still == MAGIC at offset 0 it falls to
    #    CFG_FALLBACK. valid: LOAD(0) -> FALLBACK(2).
    (
        r'header\.magic == CONFIG_BLOB_MAGIC &&',
        r'header.magic != CONFIG_BLOB_MAGIC &&',
        "classify_magic_compare_inverted (valid->fallback decision divergence)",
    ),
    # 2. (crc) FLIP THE CRC COMPARE: accept a blob whose payload CRC does NOT match
    #    the header. The "bad_crc" blob (corrupt payload) then passes validation and
    #    is trusted. bad_crc: FALLBACK(2) -> LOAD(0).
    (
        r'== header\.crc32\) \{',
        r'!= header.crc32) {',
        "classify_crc_compare_inverted (bad_crc->load decision divergence)",
    ),
    # 3. (version) FLIP THE VERSION COMPARE: accept any version EXCEPT the current one.
    #    The "version_skew" blob (version = VERSION+1) then validates, while the "valid"
    #    blob (current version) is rejected. version_skew: FALLBACK(2) -> LOAD(0)
    #    (and valid: LOAD(0) -> FALLBACK(2)).
    (
        r'header\.version == CONFIG_BLOB_VERSION &&',
        r'header.version != CONFIG_BLOB_VERSION &&',
        "classify_version_compare_inverted (version_skew->load decision divergence)",
    ),
    # 4. (migrate threshold) BREAK THE LEGACY-MIGRATE LENGTH GATE: require MORE than a
    #    full config image to migrate. The "headerless_legacy" blob (exactly config_size
    #    bytes) then no longer migrates and falls through to CFG_FALLBACK.
    #    headerless_legacy: MIGRATE(1) -> FALLBACK(2).
    (
        r'if \(file_len >= config_size\) \{\n    return CFG_MIGRATE;',
        r'if (file_len > config_size) {\n    return CFG_MIGRATE;',
        "classify_migrate_threshold_strict (headerless_legacy->fallback decision divergence)",
    ),
    # 5. (fallback return) CHANGE THE CFG_FALLBACK RECOVERY RETURN to CFG_MIGRATE: a
    #    corrupt headered blob (bad_crc / version_skew / truncated) would then be
    #    MIGRATED — i.e. the raw corrupt bytes adopted as config — instead of recovered
    #    to defaults. bad_crc: FALLBACK(2) -> MIGRATE(1).
    (
        r'if \(leading_magic == \(uint32_t\)CONFIG_BLOB_MAGIC\) \{\n      return CFG_FALLBACK;',
        r'if (leading_magic == (uint32_t)CONFIG_BLOB_MAGIC) {\n      return CFG_MIGRATE;',
        "classify_fallback_return_to_migrate (bad_crc->migrate decision divergence)",
    ),
]


# ---------------------------------------------------------------------------
# Standalone regen / self-check (mirrors oracle_chord.py __main__).
#   python3 oracle_bridge_fs_codec.py > tests/golden/bridge_fs_codec.golden.jsonl
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Behavioural oracle for the N1 persisted-config blob codec."
    )
    parser.add_argument("--verify-mutations", action="store_true")
    args = parser.parse_args()

    baseline = capture()
    print(baseline, end="")

    baseline2 = capture()
    if baseline != baseline2:
        print("DETERMINISM FAILURE: two runs produced different output.", file=sys.stderr)
        sys.exit(1)

    # Assert the recorded decisions match the documented expectations.
    recs = {json.loads(l)["blob"]: json.loads(l)["decision"]
            for l in baseline.strip().splitlines()}
    if recs != EXPECTED:
        print(f"DECISION MISMATCH: got {recs}, expected {EXPECTED}", file=sys.stderr)
        sys.exit(1)

    print(f"\n# golden_record_count={len(baseline.strip().splitlines())}", file=sys.stderr)
    print("# determinism=OK (two runs byte-identical)", file=sys.stderr)
    print(f"# decisions match expected: {EXPECTED}", file=sys.stderr)

    if args.verify_mutations:
        print("\n# --- Mutation verification ---", file=sys.stderr)
        all_caught = True
        for pattern, replacement, desc in MUTATIONS:
            with tempfile.TemporaryDirectory() as td:
                dst = Path(td) / "SPECTRASYNQ_K1_FIRMWARE"
                shutil.copytree(FW, dst)
                target = None
                for f in dst.rglob("*"):
                    if f.suffix in (".cpp", ".h") and f.is_file():
                        txt = f.read_text(encoding="utf-8", errors="ignore")
                        if re.search(pattern, txt):
                            f.write_text(re.sub(pattern, replacement, txt, count=1), encoding="utf-8")
                            target = f
                            break
                try:
                    caught = target is not None and capture(firmware_root=dst) != baseline
                except RuntimeError as exc:
                    # A mutation that breaks compilation is also a divergence (the
                    # decision can no longer be produced) — count it as caught.
                    caught = target is not None
                    print(f"#    (compile diverged: {str(exc)[:80]})", file=sys.stderr)
                all_caught = all_caught and caught
                print(f"#  [{'CAUGHT' if caught else 'MISSED'}] {desc}", file=sys.stderr)
        print("# all mutations caught." if all_caught
              else "# WARNING: a mutation was not caught.", file=sys.stderr)
        sys.exit(0 if all_caught else 1)
