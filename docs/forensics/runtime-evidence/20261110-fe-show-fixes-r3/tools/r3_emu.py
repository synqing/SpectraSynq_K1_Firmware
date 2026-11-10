#!/usr/bin/env python3
"""Emulator checks for K1-FE-SHOW change requests R3-1 and R3-2 (host only; opens no device).

  r3_emu.py run <firmware export> <out dir> [--suite r31,r32]
  r3_emu.py analyse <out dir>

R3-1 (frames lost on the way), Main RPL profile, modes 32 and 18, both edges:
  r31-cont-mNN       M1 stream 100.0-125.0 s, nothing dropped.
  r31-gaps-mNN       the same stream with runs of 4, 12 and 60 consecutive frames removed
                     (sequence and show time of the remaining frames untouched).
  r31-gapszero-m32   the gap stream again over all-zero microphone PCM.
  r31-seeks-m32      one backward jump, one forward jump whose show time does not match its
                     sequence step, one consistent forward jump longer than the hold window.
  Pass: the gap runs keep epoch 1; both edges equal the continuous run again after each gap
  within the declared interval R (gates.py G3_R_HOPS); the two gap runs are identical on every
  captured frame; the seek run's epoch rises exactly at the three jumps.

R3-2 (prepared-show level), Main RPL profile, modes 32 and 18, both edges:
  r32-stairs-mNN     a synthetic stream: pressure held at 0, 0.05, 0.1 ... 1.0 for 4 s each, over
                     all-zero microphone PCM. Reports edge brightness per step (last 2 s of a step).

Uses the K1-FE-SHOW lane's own helpers (gates.py schedule/compare/load_case, prim8_stream) so the
stream timing model is the one G1-G4 use. The firmware export is built by its own run.py.
"""
from __future__ import annotations

import json
import os
import re
import shutil
import struct
import subprocess
import sys
from pathlib import Path

REPO = Path("/Users/spectrasynq/SpectraSynq_K1_Firmware")
M2EMU = REPO / "_scratch/k1-fe-show-m2_20261110/m2-emu"
sys.path.insert(0, str(M2EMU))
import gates as g  # noqa: E402  (also puts lane-b on sys.path)
import prim8_stream as ps  # noqa: E402

HZ = 120
W0, W1 = 100.0, 125.0                       # musical window of the R3-1 runs
GAPS = [(102.0, 4), (108.0, 12), (114.0, 60)]   # (musical second of the first lost frame, frames lost)
CAP_FROM_S = 1.5                            # capture from 101.5 s
STEPS = [0.0, 0.05, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]
STEP_S = 4.0
MODES = (32, 18)


def hop_of(run_s: float) -> int:
    return int(round(run_s * 1e6)) // g.HOP_US


def gap_stream(m1: dict[int, bytes]):
    ts = sorted(t for t in m1 if g.us(W0) <= t < g.us(W1))
    lost, info = set(), []
    for at_s, n in GAPS:
        i = next(k for k, t in enumerate(ts) if t >= g.us(at_s))
        run = ts[i:i + n]
        lost.update(run)
        before, after = ts[i - 1], ts[i + n]
        info.append({"frames_lost": n, "first_lost_t_us": run[0], "last_lost_t_us": run[-1],
                     "last_before": ps.decode_frame(m1[before])["seq"], "first_after": ps.decode_frame(m1[after])["seq"],
                     "quiet_ms": round((after - before) / 1000, 3),
                     "resume_run_hop": g.arrival_hop(after - g.us(W0)),
                     "last_before_run_hop": g.arrival_hop(before - g.us(W0))})
    return {t: f for t, f in m1.items() if t not in lost}, info


def seek_stream(m1: dict[int, bytes]):
    """Run-time layout (seconds from run start) and the frames sent in each part.
    part 1: 100.0-104.0 as recorded                                   -> epoch 1
    part 2: back to 101.0, 101.0-104.0 as recorded (backward)          -> epoch 2
    part 3: 106.0-109.0 with sequence numbers renumbered to follow part 2 without a step,
            so the show time jumps 2 s while the sequence says 1 frame -> epoch 3
    part 4: consistent forward jump of 2 s (240 frames > hold window)  -> epoch 4
            (renumbered the same way as part 3, so sequence and show time agree across it)"""
    def part(a, b):
        return sorted(t for t in m1 if g.us(a) <= t < g.us(b))
    p1, p2, p3, p4 = part(100.0, 104.0), part(101.0, 104.0), part(106.0, 109.0), part(111.0, 114.0)
    last_seq = ps.decode_frame(m1[p2[-1]])["seq"]
    first3 = ps.decode_frame(m1[p3[0]])["seq"]
    shift = first3 - (last_seq + 1)             # part 3 and 4 sequence numbers move down by this
    per_hop: dict[int, bytearray] = {}
    marks = []
    run0 = 0
    for label, ts, renumber in (("start", p1, 0), ("backward", p2, 0), ("forward, show time off", p3, shift),
                                ("forward, consistent, 2 s", p4, shift)):
        t_first = ts[0]
        for k, t in enumerate(ts):
            d = ps.decode_frame(m1[t])
            fr = ps.encode_frame(d["seq"] - renumber, d["t_us"], d["prim8"], d["hz"])
            h = g.arrival_hop(run0 + (t - t_first))
            buf = per_hop.setdefault(h, bytearray())
            if k == 0:
                buf += ps.RESYNC_PREAMBLE
                marks.append({"part": label, "first_run_hop": h, "first_seq": d["seq"] - renumber, "first_t_us": d["t_us"]})
            buf += ps.wire_packets(fr)[0]
        run0 += (ts[-1] - t_first) + 1_000_000 // HZ + 1
        run0 = -(-run0 // g.HOP_US) * g.HOP_US          # next part starts on a hop boundary
    raw = bytearray()
    for h in sorted(per_hop):
        b = bytes(per_hop[h])
        assert len(b) <= g.REC_DATA, (h, len(b))
        raw += struct.pack("<II", h, len(b)) + b + b"\0" * (g.REC_DATA - len(b))
    return bytes(raw), marks, run0 / 1e6


def stairs_stream():
    frames = {}
    n_per = int(STEP_S * HZ)
    for s, p in enumerate(STEPS):
        v = int(round(p * 65535))
        for k in range(n_per):
            i = s * n_per + k
            t = ps.tick_time_us(i, HZ)
            frames[t] = ps.encode_frame(i, t, [v, 0, v, v, 0, 0, v, 0], HZ)
    return frames


def build(tree: Path, out: Path, suites: list[str]):
    sc = json.loads((tree / "tools/esp_emulator/s3_music_regression.json").read_text())
    sc["name"] = "fe-show-fixes-r3"
    sc["description"] = "K1-FE-SHOW change requests R3-1 (lost frames) and R3-2 (prepared level); r3_emu.py"
    sched_dir = out / "schedules"
    sched_dir.mkdir(parents=True, exist_ok=True)
    m1 = g.read_frames(g.M1_STREAM)
    assert g.sha256_file(g.M1_STREAM) == g.M1_STREAM_SHA
    plan = {"cases": {}, "gaps": None, "seeks": None, "steps": STEPS, "step_s": STEP_S}
    cases = {}
    for mode in MODES:
        sc["compositions"][f"r3_m{mode}"] = {"commands": [f"set_mode={mode}", f"secondary_mode={mode}", "secondary_enabled=true"],
                                             "note": f"both edges mode {mode}"}

    def add(cid, purpose, pcm, rx_raw, capture, mode):
        p = sched_dir / f"{cid}.rx"
        p.write_bytes(rx_raw)
        cases[cid] = {"purpose": purpose, "pcm": pcm, "epoch": {"policy": "declared", "us": 1000000},
                      "partial_hop": "zero_pad", "composition": f"r3_m{mode}", "capture": capture,
                      "rx_stream": {"schedule": str(p), "sha256": g.sha256_bytes(rx_raw), "note": "r3_emu.py"}}
        plan["cases"][cid] = {"mode": mode, "rx_sha256": g.sha256_bytes(rx_raw)}

    if "r31" in suites:
        dur = W1 - W0
        th = g.total_hops_for(dur)
        sc["assets"]["r3_passage"] = {"kind": "concat", "qualification": "real_music",
                                      "segments": [g.loreen_seg(W0, W1, "original 100.0-125.0 s")], "origin": "R3-1"}
        sc["assets"]["r3_zero25"] = {"kind": "concat", "qualification": "diagnostic_composite",
                                     "segments": [{"zeros_ms": int(dur * 1000), "label": "all-zero PCM"}], "origin": "R3-1"}
        cap = {"start_hop": hop_of(CAP_FROM_S), "end_hop": None, "every": 2}
        seg = [(0, g.us(W0), g.us(dur))]
        cont_raw, cont_info = g.schedule(m1, seg, th)
        gapped, gap_info = gap_stream(m1)
        gap_raw, gap_sched = g.schedule(gapped, seg, th)
        plan["gaps"] = {"runs": gap_info, "continuous": cont_info, "gapped": gap_sched}
        for mode in MODES:
            add(f"r31-cont-m{mode}", "R3-1: continuous stream.", "r3_passage", cont_raw, cap, mode)
            add(f"r31-gaps-m{mode}", "R3-1: runs of 4, 12 and 60 frames lost.", "r3_passage", gap_raw, cap, mode)
        add("r31-gapszero-m32", "R3-1: the gap stream over all-zero microphone PCM.", "r3_zero25", gap_raw, cap, 32)
        seek_raw, marks, seek_len = seek_stream(m1)
        seek_len = float(int(seek_len) + 1)
        sc["assets"]["r3_seekpcm"] = {"kind": "concat", "qualification": "real_music",
                                      "segments": [g.loreen_seg(W0, W0 + seek_len, "microphone PCM for the seek run")], "origin": "R3-1"}
        plan["seeks"] = {"parts": marks, "run_s": seek_len}
        add("r31-seeks-m32", "R3-1: true seeks still start a new epoch.", "r3_seekpcm", seek_raw,
            {"start_hop": 0, "end_hop": None, "every": 6}, 32)
    if "r32" in suites:
        dur = STEP_S * len(STEPS)
        th = g.total_hops_for(dur)
        sc["assets"]["r3_zero_stairs"] = {"kind": "concat", "qualification": "diagnostic_composite",
                                          "segments": [{"zeros_ms": int(dur * 1000), "label": "all-zero PCM"}], "origin": "R3-2"}
        raw, _ = g.schedule(stairs_stream(), [(0, 0, g.us(dur))], th)
        for mode in MODES:
            add(f"r32-stairs-m{mode}", "R3-2: pressure staircase 0..1.", "r3_zero_stairs", raw,
                {"start_hop": 0, "end_hop": None, "every": 4}, mode)
    sc["cases"].update(cases)
    sc["suites"]["r3"] = list(cases)
    sc["host_checks"] = {"pytest": [], "builds": [], "requires_git": sc.get("host_checks", {}).get("requires_git", [])}
    scen = tree / "tools/esp_emulator/r3_scenario.json"
    scen.write_text(json.dumps(sc, indent=2) + "\n")
    shutil.copy(scen, out / "r3_scenario.json")
    plan["suite"] = list(cases)
    plan["tree"] = str(tree)
    (out / "plan.json").write_text(json.dumps(plan, indent=2) + "\n")
    return scen


def run(tree: Path, out: Path, suites: list[str]) -> int:
    tree, out = tree.resolve(), out.resolve()
    out.mkdir(parents=True, exist_ok=False)
    if not (tree / ".pio/libdeps").is_dir():
        (tree / ".pio").mkdir(exist_ok=True)
        shutil.copytree(M2EMU / "src-ed0aa984/.pio/libdeps", tree / ".pio/libdeps", symlinks=True)
    scen = build(tree, out, suites)
    env = dict(os.environ)
    env.setdefault("K1_ESP_EMU", g.ESP_EMU)
    cmd = [sys.executable, str(tree / "tools/esp_emulator/run.py"), "--profile", "scenario", "--scenario", str(scen),
           "--suite", "r3", "--output", str(out / "emu")]
    with open(out / "emu-run.log", "w") as f:
        rc = subprocess.run(cmd, cwd=tree, env=env, stdout=f, stderr=subprocess.STDOUT).returncode
    print("run.py exit", rc, "(its own release verdict covers the full default suite, not these cases)")
    return analyse(out)


def prep_lines(uart: str):
    ev = [dict(kv.split("=") for kv in m.group(1).split()) for m in re.finditer(r"EMU_PREP (after_hop=.*)", uart)]
    end = re.search(r"EMU_PREP_END (.*)", uart)
    return ([{k: int(v) for k, v in e.items()} for e in ev],
            {k: int(v) for k, v in (kv.split("=") for kv in end.group(1).split())} if end else None)


def analyse(out: Path) -> int:
    import numpy as np
    out = out.resolve()
    plan = json.loads((out / "plan.json").read_text())
    rj = json.loads((out / "emu/result.json").read_text())
    sys.path.insert(0, str(Path(plan["tree"]) / "tools" / "esp_emulator"))
    import emu_capture as ec  # noqa: E402
    res = {"source": rj.get("source"), "emu_build": rj.get("emu_build"), "cases": {}, "checks": {}}
    cases, uarts = {}, {}
    for cid in plan["suite"]:
        st = rj["cases"].get(cid, {})
        res["cases"][cid] = {"status": st.get("status", "MISSING"), "reasons": st.get("reasons")}
        if st.get("status") == "PASS":
            cases[cid] = g.load_case(ec, out / "emu", cid)
            uarts[cid] = (out / "emu" / cid / "uart.txt").read_text(errors="replace")
            ev, end = prep_lines(uarts[cid])
            res["cases"][cid].update({"epoch_changes": ev, "end": end, "auth": cases[cid]["auth"],
                                      "n_frames": cases[cid]["n_frames"], "edge_sha256": cases[cid]["edge_sha256"]})
    bad = 0

    def check(name, ok, detail):
        nonlocal bad
        res["checks"][name] = {"verdict": "PASS" if ok else "FAIL", **detail}
        bad += 0 if ok else 1
        print(("PASS " if ok else "FAIL ") + name + "  " + json.dumps(detail)[:400])

    if plan.get("gaps"):
        runs = plan["gaps"]["runs"]
        for mode in MODES:
            a, b = f"r31-cont-m{mode}", f"r31-gaps-m{mode}"
            if a not in cases or b not in cases:
                check(f"R3-1 m{mode} runs accepted", False, {"cont": res["cases"].get(a), "gaps": res["cases"].get(b)})
                continue
            end = res["cases"][b]["end"]
            lost = sum(r["frames_lost"] for r in runs)
            check(f"R3-1 m{mode} one epoch across lost runs of 4, 12, 60",
                  end is not None and end["epoch"] == 1 and end["seq_gaps"] == lost,
                  {"end": end, "epoch_changes": res["cases"][b]["epoch_changes"], "continuous_end": res["cases"][a]["end"],
                   "auth_transitions": res["cases"][b]["auth"]})
            fa, fb = cases[a]["frames"], cases[b]["frames"]
            hops = sorted(set(fa) & set(fb))
            per_gap = []
            ok_all = True
            for k, r in enumerate(runs):
                lo = r["last_before_run_hop"]
                hi = runs[k + 1]["last_before_run_hop"] if k + 1 < len(runs) else hops[-1] + 1
                seg = [h for h in hops if lo <= h < hi]
                row = {"frames_lost": r["frames_lost"], "quiet_ms": r["quiet_ms"], "resume_run_hop": r["resume_run_hop"],
                       "compared_frames": len(seg)}
                for e, idx in (("A", 0), ("B", 1)):
                    d = [h for h in seg if fa[h][idx] != fb[h][idx]]
                    last = d[-1] if d else None
                    agrees_from = None if last is None else next((h for h in seg if h > last), None)
                    row[e] = {"differing_frames": len(d), "first_diff_hop": d[0] if d else None, "last_diff_hop": last,
                              "agrees_from_hop": agrees_from if d else seg[0],
                              "s_after_resume": None if not d or agrees_from is None else
                              round((agrees_from - r["resume_run_hop"]) * g.HOP_US / 1e6, 3)}
                    if d:
                        row[e]["max_mean_abs_diff_16bit"] = round(max(float(np.abs(
                            np.frombuffer(fa[h][idx], ">u2").astype(int) - np.frombuffer(fb[h][idx], ">u2").astype(int)).mean())
                            for h in d), 2)
                    conv = (not d) or (agrees_from is not None and agrees_from - r["resume_run_hop"] <= g.G3_R_HOPS)
                    ok_all = ok_all and conv
                per_gap.append(row)
            before = [h for h in hops if h < runs[0]["last_before_run_hop"]]
            pre_equal = all(fa[h] == fb[h] for h in before)
            check(f"R3-1 m{mode} both edges equal continuous play again after each gap (within R = {g.G3_R_HOPS} hops)",
                  ok_all and pre_equal, {"identical_before_first_gap": pre_equal, "frames_before_first_gap": len(before),
                                         "per_gap": per_gap})
        if "r31-gapszero-m32" in cases and "r31-gaps-m32" in cases:
            c = g.compare(cases["r31-gaps-m32"], cases["r31-gapszero-m32"])
            check("R3-1 m32 gap run is the same over music PCM and all-zero PCM (the hold keeps the microphone out)",
                  c["identical_both_edges"], {"compare": c})
        else:
            check("R3-1 m32 gap run over zero PCM accepted", False, {"case": res["cases"].get("r31-gapszero-m32")})
        cid = "r31-seeks-m32"
        if cid in cases:
            ev = res["cases"][cid]["epoch_changes"]
            parts = plan["seeks"]["parts"]
            near = len(ev) == len(parts) and all(
                e["epoch"] == k + 1 and abs(e["after_hop"] - p["first_run_hop"]) <= 1 and e["applied_seq"] == p["first_seq"]
                for k, (e, p) in enumerate(zip(ev, parts)))
            check("R3-1 true seeks still start a new epoch (backward; show time off; forward longer than the hold)",
                  near and res["cases"][cid]["end"]["epoch"] == len(parts),
                  {"expected_parts": parts, "epoch_changes": ev, "end": res["cases"][cid]["end"]})
        else:
            check("R3-1 seek run accepted", False, {"case": res["cases"].get(cid)})

    if any(c.startswith("r32") for c in plan["suite"]):
        table = {}
        for mode in MODES:
            cid = f"r32-stairs-m{mode}"
            if cid not in cases:
                check(f"R3-2 m{mode} staircase accepted", False, {"case": res["cases"].get(cid)})
                continue
            fr = cases[cid]["frames"]
            rows = []
            for s, p in enumerate(plan["steps"]):
                lo, hi = hop_of(s * plan["step_s"] + 2.0), hop_of((s + 1) * plan["step_s"])
                hs = [h for h in sorted(fr) if lo <= h < hi]
                row = {"pressure": p, "frames": len(hs)}
                for e, idx in (("A", 0), ("B", 1)):
                    arr = np.stack([np.frombuffer(fr[h][idx], ">u2").astype(np.int64) for h in hs])   # frames x 480
                    px = arr.reshape(len(hs), 160, 3)
                    lit = (px.max(axis=2) > 0).sum(axis=1)
                    row[e] = {"mean": round(float(arr.mean()), 1), "max": int(arr.max()),
                              "brightest_pixel_mean": round(float(px.max(axis=2).max(axis=1).mean()), 1),
                              "lit_pixels_mean": round(float(lit.mean()), 1)}
                rows.append(row)
            table[f"m{mode}"] = rows
            top = rows[-1]
            check(f"R3-2 m{mode} staircase rendered and lit at full pressure", top["A"]["max"] > 0 and top["B"]["max"] > 0,
                  {"full_pressure": top})
        res["r32_mapping"] = table
        lines = ["| mode | pressure | edge A mean | edge A brightest pixel | edge A lit px | edge B mean | edge B brightest pixel | edge B lit px |",
                 "|---|---|---|---|---|---|---|---|"]
        for m, rows in table.items():
            for r in rows:
                lines.append(f"| {m[1:]} | {r['pressure']:.2f} | {r['A']['mean']} | {r['A']['brightest_pixel_mean']} | {r['A']['lit_pixels_mean']} "
                             f"| {r['B']['mean']} | {r['B']['brightest_pixel_mean']} | {r['B']['lit_pixels_mean']} |")
        (out / "r32-mapping.md").write_text("\n".join(lines) + "\n")
        print("\n".join(lines))
    (out / "r3.json").write_text(json.dumps(res, indent=2) + "\n")
    (out / "exit_code.txt").write_text(f"{bad}\n")
    print(f"r3.json {out / 'r3.json'}\nfailing checks: {bad}")
    return bad


if __name__ == "__main__":
    if len(sys.argv) >= 4 and sys.argv[1] == "run":
        suites = sys.argv[5].split(",") if len(sys.argv) > 5 and sys.argv[4] == "--suite" else ["r31", "r32"]
        raise SystemExit(run(Path(sys.argv[2]), Path(sys.argv[3]), suites))
    if len(sys.argv) == 3 and sys.argv[1] == "analyse":
        raise SystemExit(analyse(Path(sys.argv[2])))
    raise SystemExit(__doc__)
