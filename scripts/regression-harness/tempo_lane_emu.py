#!/usr/bin/env python3
"""Run tempo-lane cases through the real emulated firmware (lane R1, DEF-001 / DEF-002).

Each case is PCM through tools/esp_emulator/run.py:run_case on a named emulator build. The tool keeps
the raw uart and extracts the per-generation streams the lane gates read:
  N  gen, tempo input the tracker consumed, producer silence          (trace_novelty)
  K  gen, veto, internal lock, producer silence, published lock/tick/conf/bpm   (lane flags only)
  V  render-thread consumed tempo view for the captured frames
  G  probe envs only: loud-guard state + tracker stage timers
Captured streams are the shared fixtures (I7); host replay and scorers read them, never re-derive.

  tempo_lane_emu.py run --env ENV --suite p15|music --out DIR [--parallel N]
  tempo_lane_emu.py run --env ENV --manifest M --role dev|heldout --out DIR [--limit K] [--parallel N]

Synthetic generators are deterministic (fixed seeds) and normalised like run.py load_asset
(one gain to peak 4096) unless stated.
"""
from __future__ import annotations

import argparse
import array
import json
import math
import multiprocessing as mp
import random
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools/esp_emulator"))
RATE, HOP, PEAK = 12800, 96, 4096
SCORE_FROM_HOP = 1600


# ------------------------------------------------------------------ PCM sources
def _to_pcm(samples, normalise=True) -> bytes:
    peak = max((abs(s) for s in samples), default=0.0)
    g = (PEAK / peak) if (normalise and peak) else 1.0
    return array.array("h", (max(-32768, min(32767, int(round(s * g)))) for s in samples)).tobytes()


def gen_silence(seconds):
    return bytes(2 * int(seconds * RATE))


def gen_white_noise(seconds, seed=1234):
    r = random.Random(seed)
    return _to_pcm([r.gauss(0.0, 1.0) for _ in range(int(seconds * RATE))])


def gen_tone(seconds, hz=440.0):
    return _to_pcm([math.sin(2 * math.pi * hz * n / RATE) for n in range(int(seconds * RATE))])


def gen_pink_drone(seconds, seed=4321):
    # Voss-McCartney style pink noise (16 rows), deterministic.
    r = random.Random(seed)
    rows = [r.uniform(-1, 1) for _ in range(16)]
    out, total = [], sum(rows)
    for n in range(int(seconds * RATE)):
        k = (n & -n).bit_length() - 1 if n else 0
        k = min(k, 15)
        total -= rows[k]
        rows[k] = r.uniform(-1, 1)
        total += rows[k]
        out.append(total + r.uniform(-1, 1))
    return _to_pcm(out)


def gen_sweep(seconds, f0=200.0, f1=2000.0):
    n_total = int(seconds * RATE)
    k = math.log(f1 / f0) / seconds
    return _to_pcm([math.sin(2 * math.pi * f0 * (math.exp(k * n / RATE) - 1.0) / k) for n in range(n_total)])


def music_a_pcm(work: Path) -> tuple[bytes, dict]:
    import run
    sc = run.load_scenario(ROOT / "tools/esp_emulator/s3_music_regression.json")
    return run.load_asset(sc, sc["cases"]["music-a"]["pcm"], {}, work)


def decode_like_run(path: str, start_ms: int, duration_ms: int | None, work: Path) -> tuple[bytes, dict]:
    raw = work / f"decode_{abs(hash((path, start_ms, duration_ms)))}.s16le"
    cmd = ["ffmpeg", "-nostdin", "-v", "error", "-ss", f"{start_ms / 1000:.3f}"]
    if duration_ms:
        cmd += ["-t", f"{duration_ms / 1000:.3f}"]
    cmd += ["-i", path, "-map", "0:a:0", "-ac", "1", "-ar", str(RATE), "-af", "anull", "-f", "s16le",
            "-acodec", "pcm_s16le", str(raw)]
    subprocess.run(cmd, check=True)
    a = array.array("h"); a.frombytes(raw.read_bytes())
    raw.unlink()
    peak = max((abs(s) for s in a), default=0)
    g = (PEAK / peak) if peak else 1.0
    pcm = array.array("h", (max(-32768, min(32767, int(round(s * g)))) for s in a)).tobytes()
    return pcm, {"decoded_peak": peak, "applied_gain": g, "argv": cmd[1:]}


def case_pcm(case: dict, work: Path) -> tuple[bytes, dict]:
    s = case["source"]
    if s["kind"] == "music_a":
        pcm, meta = music_a_pcm(work)
        return pcm, {"source": "s3 music-a (loreen_127, 22 s)", "sha256": meta["sha256"]}
    if s["kind"] == "music_then_silence":
        pcm, meta = music_a_pcm(work)
        return pcm + gen_silence(s["silence_s"]), {"source": f"music-a + {s['silence_s']} s digital silence",
                                                   "music_samples": len(pcm) // 2}
    if s["kind"] == "synthetic":
        fn = {"silence": gen_silence, "white_noise": gen_white_noise, "tone": gen_tone,
              "pink_drone": gen_pink_drone, "sweep": gen_sweep}[s["gen"]]
        return fn(s["seconds"]), {"source": f"synthetic {s['gen']} {s['seconds']} s"}
    if s["kind"] == "wav":
        return decode_like_run(s["path"], s.get("start_ms", 0), s.get("duration_ms"), work)
    raise SystemExit(f"unknown source {s}")


# ------------------------------------------------------------------ suites
def suite(name: str) -> list[dict]:
    full = {"start_hop": 0, "end_hop": None, "every": 2}
    if name == "music":
        return [{"id": "music-a", "source": {"kind": "music_a"},
                 "capture": {"start_hop": 1600, "end_hop": 2934, "every": 1}, "expected_bpm": 127}]
    if name == "p15":
        return [
            {"id": "music-a", "source": {"kind": "music_a"},
             "capture": {"start_hop": 1600, "end_hop": 2934, "every": 1}, "expected_bpm": 127},
            {"id": "silence-30s", "source": {"kind": "synthetic", "gen": "silence", "seconds": 30}, "capture": full},
            {"id": "white-noise-30s", "source": {"kind": "synthetic", "gen": "white_noise", "seconds": 30}, "capture": full},
            {"id": "tone440-30s", "source": {"kind": "synthetic", "gen": "tone", "seconds": 30}, "capture": full},
            {"id": "pink-drone-30s", "source": {"kind": "synthetic", "gen": "pink_drone", "seconds": 30}, "capture": full},
            {"id": "sweep-30s", "source": {"kind": "synthetic", "gen": "sweep", "seconds": 30}, "capture": full},
            {"id": "music-then-silence", "source": {"kind": "music_then_silence", "silence_s": 15},
             "capture": {"start_hop": 0, "end_hop": None, "every": 3}},
        ]
    raise SystemExit(f"unknown suite {name}")


def manifest_cases(manifest: Path, role: str, limit: int | None) -> list[dict]:
    rows = json.loads(manifest.read_text())["rows"]
    out = []
    for r in rows:
        if role != "all" and r["role"] != role:
            continue
        ex = r.get("excerpt") or {}
        out.append({"id": r["id"], "source": {"kind": "wav", "path": r["path"], "start_ms": ex.get("start_ms") or 0,
                                              "duration_ms": ex.get("duration_ms")},
                    "capture": {"start_hop": SCORE_FROM_HOP, "end_hop": SCORE_FROM_HOP + 2000, "every": 1},
                    "gold_bpm": r["gold_bpm"]})
    return out[:limit] if limit else out


# ------------------------------------------------------------------ streams
def extract(uart: str) -> dict:
    N, K, V, G = [], [], [], []
    for ln in uart.splitlines():
        p = ln.split(",")
        if ln.startswith("N,"):
            N.append([int(p[1]), p[2], int(p[4])])
        elif ln.startswith("K,"):
            K.append([int(p[1]), int(p[2]), int(p[3]), int(p[4]), int(p[5]), int(p[6]), float(p[7]), float(p[8])])
        elif ln.startswith("V,"):
            V.append([int(p[2]), float(p[15]), float(p[17]), int(p[18])])
        elif ln.startswith("G,"):
            G.append([int(x) if i not in (1, 2, 8) else float(x) for i, x in enumerate(p[1:])])
    return {"N": N, "K": K, "V": V, "G": G}


def _run_one(args) -> dict:
    case, env, out = args
    import run
    out = Path(out)
    work = out / "work" / case["id"].replace(":", "_")
    work.mkdir(parents=True, exist_ok=True)
    sc = run.load_scenario(ROOT / "tools/esp_emulator/s3_music_regression.json")
    pcm, meta = case_pcm(case, work)
    hops = -(-(len(pcm) // 2) // HOP)
    cap = dict(case["capture"])
    if cap.get("end_hop") is None:
        cap["end_hop"] = hops
    cap["end_hop"] = min(cap["end_hop"], hops)
    if len(range(cap["start_hop"], cap["end_hop"], cap["every"])) > 2000:
        cap["every"] = -(-(cap["end_hop"] - cap["start_hop"]) // 2000)
    cid = "lane-" + case["id"].replace(":", "_")
    aid = "pcm_" + cid
    sc["assets"][aid] = {"kind": "c_array_inc", "qualification": "lane_r1", "path": "-"}
    sc["cases"][cid] = {"purpose": f"tempo lane R1: {case['id']}", "pcm": aid,
                        "epoch": {"policy": "declared", "us": 1000000}, "capture": cap,
                        "partial_hop": "zero_pad", "trace_novelty": True}
    assets = {aid: (pcm, {"id": aid, "samples": len(pcm) // 2, "sha256": run.sha256_bytes(pcm), **meta})}
    lock = json.loads((run.HERE / "tool-lock.json").read_text())
    emu, _ = run.resolve_esp_emu(lock)
    runs = out / "runs"
    runs.mkdir(parents=True, exist_ok=True)
    rec = run.run_case(sc, cid, runs, emu, ROOT / ".pio/build" / env, assets, {})
    res = {"id": case["id"], "cid": cid, "status": rec["status"], "reasons": rec.get("reasons", [])[:4],
           "wall_seconds": rec.get("wall_seconds"), "pcm_sha256": assets[aid][1]["sha256"],
           "samples": len(pcm) // 2, "music_samples": meta.get("music_samples"), "env": env,
           "gold_bpm": case.get("gold_bpm"), "expected_bpm": case.get("expected_bpm")}
    if rec.get("_capture") is not None and case.get("expected_bpm"):
        comp = {"id": "tempo", "kind": "tempo_lane", "a": cid, "criterion": "lane",
                "expect": {"expected_bpm": case["expected_bpm"], "fixture_type": "known_real_music",
                           "accept": ["PASS_timing_and_tempo"]}}
        ev = run.evaluate_comparison(comp, {cid: rec}, HOP)
        res["tempo_lane"] = {k: ev.get(k) for k in ("status", "classification", "detail")}
    streams = extract(rec.get("_uart", ""))
    (runs / cid / "streams.json").write_text(json.dumps(streams, separators=(",", ":")))
    res["streams"] = str(runs / cid / "streams.json")
    res["counts"] = {k: len(v) for k, v in streams.items()}
    shutil.rmtree(work, ignore_errors=True)
    return res


def cmd_run(a) -> int:
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=False)
    cases = suite(a.suite) if a.suite else manifest_cases(Path(a.manifest), a.role, a.limit)
    build = ROOT / ".pio/build" / a.env / "firmware.bin"
    if not build.is_file():
        raise SystemExit(f"no build for {a.env}")
    git = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True).stdout.strip()
    with mp.Pool(a.parallel) as pool:
        results = pool.map(_run_one, [(c, a.env, str(out)) for c in cases], chunksize=1)
    doc = {"env": a.env, "git_head": git, "suite": a.suite, "manifest": a.manifest, "role": a.role,
           "cases": results}
    (out / "cases.json").write_text(json.dumps(doc, indent=1))
    bad = [r["id"] for r in results if r["status"] != "PASS"]
    print(f"cases={len(results)} emulator_not_pass={len(bad)} {bad[:8]}")
    for r in results:
        if "tempo_lane" in r:
            print(r["id"], r["tempo_lane"]["classification"], "|", (r["tempo_lane"]["detail"] or "")[:160])
    return 0 if not bad else 1


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run")
    r.add_argument("--env", required=True)
    r.add_argument("--suite")
    r.add_argument("--manifest")
    r.add_argument("--role", default="dev")
    r.add_argument("--limit", type=int)
    r.add_argument("--parallel", type=int, default=6)
    r.add_argument("--out", required=True)
    a = p.parse_args(argv)
    return cmd_run(a)


if __name__ == "__main__":
    sys.exit(main())
