#!/usr/bin/env python3
"""Host replay of captured tempo input through the REAL k1_tempo.cpp (lane R1, DEF-001/DEF-002).

Invariant I7: the tempo input is captured once from the production chain (emulator `N` lines,
`trace_novelty`) and shared; this tool never re-derives it. `extract` projects N lines into a
fixture set with hashes; `replay` feeds a fixture set through a host build of the unmodified
k1_tempo.cpp compiled with a named define set and writes per-generation trajectories for
tempo_lane_scorer.py.

  tempo_lane_replay.py extract --uart-dir DIR --glob 'hx_*.uart.txt' --id-prefix hx: --out-dir FIX
  tempo_lane_replay.py replay  --fixtures FIX/index.json --variant shipped --out traj.json
                               [--define X=Y ...] [--transform scale:0.5|pow:2] [--debug]

Clock: the emulator stamps hop g at millis() = 1000 + floor(g * 7.5) (declared 1.0 s epoch,
hop-end convention); the replay uses the same frame_ms.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
FIRMWARE = ROOT / "SPECTRASYNQ_K1_FIRMWARE"
sys.path.insert(0, str(HERE))
import tempo_replay as trp  # noqa: E402  (ARDUINO_STUB only)

# Product tempo defines of k1_main_rpl_im69d (tests/test_tempo_behavioural_equivalence_v1.PROD).
PROD = ["K1_TEMPO_CONF_V2", "K1_TEMPO_FLYWHEEL_V2", "K1_TEMPO_ACF_SPREAD_V1=1",
        "DEFAULT_SAMPLE_RATE=12800", "DEFAULT_SAMPLES_PER_CHUNK=96", "K1_TEMPO_NOVELTY_DECIMATION=3U"]
# Lane flag sets (all default OFF in source; listed explicitly so every trajectory names its build).
VARIANTS = {
    "shipped": [],
    "linear": ["K1_TEMPO_NOVELTY_LINEAR_V1"],
    "l1": ["K1_TEMPO_NOVELTY_LINEAR_V1", "K1_TEMPO_SILENCE_FROM_PRODUCER_V1"],
    "silence_only": ["K1_TEMPO_SILENCE_FROM_PRODUCER_V1"],
}

DRIVER = r"""
#include "k1_tempo.h"
#include <cstdio>
int main() {
  k1_tempo_init();
  char line[256];
  while (std::fgets(line, sizeof(line), stdin)) {
    unsigned gen = 0, ms = 0; float nov = 0.0f; int sil = 0;
    if (std::sscanf(line, "%u %u %f %d", &gen, &ms, &nov, &sil) < 4) continue;
    K1AudioSnapshot a = {};
    a.frame_ms = ms;
    a.novelty = nov;
#ifdef K1_TEMPO_NOVELTY_LINEAR_V1
    a.tempo_novelty = nov;
#endif
    a.silence = sil != 0;
    k1_tempo_update(a);
    const K1TempoEvent e = k1_tempo_read();
    std::printf("F %u %.1f %.5f %d %d %.5f", gen, e.bpm, e.confidence, e.locked ? 1 : 0, e.beat_tick ? 1 : 0, e.phase01);
#if ENABLE_TEMPO_STREAM
    const K1TempoDebugSnapshot s = k1_tempo_debug_read();
    std::printf(" %d %d %.5f %u", s.v2_locked ? 1 : 0, s.silence_detected ? 1 : 0, s.v2_conf_ema, (unsigned)s.emit_count);
#ifdef K1_TEMPO_SILENCE_FROM_PRODUCER_V1
    std::printf(" %u", (unsigned)s.veto);
#else
    std::printf(" -1");
#endif
#endif
    std::printf("\n");
  }
  return 0;
}
"""


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def frame_ms(gen: int) -> int:
    return 1000 + (gen * 7500) // 1000


def build(workdir: Path, defines: list[str], debug: bool, extra: list[str] | None = None) -> Path:
    stub = workdir / "stub"
    stub.mkdir(parents=True, exist_ok=True)
    (stub / "Arduino.h").write_text(trp.ARDUINO_STUB)
    main = workdir / "lane_driver.cpp"
    main.write_text(DRIVER)
    binary = workdir / "lane_driver"
    cmd = ["clang++", "-std=c++17", "-O2", "-ffp-contract=off", "-DK1_TEMPO_HOST_TEST"]
    cmd += ["-D" + d for d in PROD + defines]
    if debug:
        cmd.append("-DENABLE_TEMPO_STREAM=1")
    cmd += list(extra or [])
    cmd += ["-I", str(stub), "-I", str(FIRMWARE), "-I", str(FIRMWARE / "audio"), "-I", str(FIRMWARE / "system"),
            str(FIRMWARE / "audio/k1_tempo.cpp"), str(main), "-o", str(binary)]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        raise SystemExit(f"host build failed ({' '.join(cmd)}):\n{r.stderr[-2000:]}")
    (workdir / "build_cmd.txt").write_text(" ".join(cmd) + "\n")
    return binary


def parse_n_lines(text: str) -> list[tuple[int, str, int]]:
    rows = []
    for ln in text.splitlines():
        if ln.startswith("N,"):
            p = ln.split(",")
            rows.append((int(p[1]), p[2], int(p[4])))
    return rows


def cmd_extract(a) -> int:
    out = Path(a.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    index = {"schema": "k1-tempo-fixture-set/1", "source_dir": str(Path(a.uart_dir).resolve()),
             "note": a.note or "", "clips": {}}
    for u in sorted(Path(a.uart_dir).glob(a.glob)):
        raw = u.read_bytes()
        rows = parse_n_lines(raw.decode(errors="replace"))
        if not rows:
            print(f"no N lines in {u}", file=sys.stderr)
            return 2
        stem = u.name.split(".")[0]
        if a.strip_prefix and stem.startswith(a.strip_prefix):
            stem = stem[len(a.strip_prefix):]
        cid = f"{a.id_prefix}{stem}"
        body = "".join(f"{g} {nov} {sil}\n" for g, nov, sil in rows).encode()
        f = out / f"{cid.replace(':', '_')}.tsv"
        f.write_bytes(body)
        index["clips"][cid] = {"file": f.name, "sha256": sha256_bytes(body), "gens": len(rows),
                               "source_uart": str(u.resolve()), "source_uart_sha256": sha256_bytes(raw)}
    (out / "index.json").write_text(json.dumps(index, indent=1, sort_keys=True) + "\n")
    print(f"extracted {len(index['clips'])} clips -> {out / 'index.json'}")
    return 0


def transform(value: float, spec: str | None) -> float:
    if not spec:
        return value
    kind, arg = spec.split(":")
    x = float(arg)
    if kind == "scale":
        return value * x
    if kind == "pow":
        return value ** x if value > 0.0 else 0.0
    raise SystemExit(f"unknown transform {spec}")


def load_fixture(index_path: Path, cid: str, meta: dict) -> list[tuple[int, float, int]]:
    body = (index_path.parent / meta["file"]).read_bytes()
    if sha256_bytes(body) != meta["sha256"]:
        raise SystemExit(f"fixture {cid} sha256 mismatch")
    rows = []
    for ln in body.decode().splitlines():
        g, nov, sil = ln.split()
        rows.append((int(g), float(nov), int(sil)))
    return rows


def replay_rows(binary: Path, rows, spec: str | None, debug: bool) -> dict:
    feed = "".join(f"{g} {frame_ms(g)} {transform(nov, spec):.9g} {sil}\n" for g, nov, sil in rows)
    r = subprocess.run([str(binary)], input=feed, capture_output=True, text=True)
    if r.returncode != 0:
        raise SystemExit(f"replay failed: {r.stderr[-500:]}")
    keys = ["gen", "bpm", "conf", "lock", "tick", "phase"]
    if debug:
        keys += ["int_lock", "int_silence", "conf_ema", "emit_count", "veto"]
    c = {k: [] for k in keys}
    c["producer_silence"] = []
    for (g, _nov, sil), ln in zip(rows, (x for x in r.stdout.splitlines() if x.startswith("F "))):
        p = ln.split()[1:]
        for k, v in zip(keys, p):
            c[k].append(float(v) if k in ("bpm", "conf", "phase", "conf_ema") else int(v))
        c["producer_silence"].append(sil)
    if len(c["gen"]) != len(rows):
        raise SystemExit("replay produced a different number of frames than it was fed")
    return c


def cmd_replay(a) -> int:
    index_path = Path(a.fixtures)
    index = json.loads(index_path.read_text())
    defines = VARIANTS[a.variant] + list(a.define or [])
    with tempfile.TemporaryDirectory() as td:
        binary = build(Path(td), defines, a.debug)
        build_cmd = (Path(td) / "build_cmd.txt").read_text().strip()
        clips = {}
        for cid, meta in sorted(index["clips"].items()):
            if a.only and cid not in a.only:
                continue
            clips[cid] = replay_rows(binary, load_fixture(index_path, cid, meta), a.transform, a.debug)
    git = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True).stdout.strip()
    tempo_sha = sha256_bytes((FIRMWARE / "audio/k1_tempo.cpp").read_bytes())
    doc = {"variant": a.variant + (f"+{a.transform}" if a.transform else ""),
           "producer": {"tool": "tempo_lane_replay.py", "defines": PROD + defines, "transform": a.transform,
                        "debug": a.debug, "build_cmd": build_cmd, "git_head": git,
                        "k1_tempo_cpp_sha256": tempo_sha, "fixtures": str(index_path.resolve()),
                        "fixtures_sha256": sha256_bytes(index_path.read_bytes())},
           "clips": clips}
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.out).write_text(json.dumps(doc, separators=(",", ":")) + "\n")
    print(f"replayed {len(clips)} clips variant={doc['variant']} -> {a.out}")
    return 0


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    e = sub.add_parser("extract")
    e.add_argument("--uart-dir", required=True)
    e.add_argument("--glob", default="*.uart.txt")
    e.add_argument("--id-prefix", default="")
    e.add_argument("--strip-prefix", default="")
    e.add_argument("--out-dir", required=True)
    e.add_argument("--note")
    r = sub.add_parser("replay")
    r.add_argument("--fixtures", required=True)
    r.add_argument("--variant", default="shipped", choices=sorted(VARIANTS))
    r.add_argument("--define", action="append")
    r.add_argument("--transform")
    r.add_argument("--only", nargs="*")
    r.add_argument("--debug", action="store_true")
    r.add_argument("--out", required=True)
    a = p.parse_args(argv)
    return cmd_extract(a) if a.cmd == "extract" else cmd_replay(a)


if __name__ == "__main__":
    sys.exit(main())
