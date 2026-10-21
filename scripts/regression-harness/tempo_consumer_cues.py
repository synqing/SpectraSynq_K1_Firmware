#!/usr/bin/env python3
"""Tempo-consumer beat cues read off the RENDERED output (lane R1, Captain supplement 2026-10-21, items 1-2).

Reads an emulator run of `tempo_lane_emu.py --suite consumer` (Tempo Comet on edge A, Tempo Comet Anticipate
on edge B, both centre-origin) built with K1_EMU_ONSET_TRACE, and finds every comet LAUNCH in the actual
captured frames.

  launch      a captured frame whose centre luminance (max over the spawn pixel +-WIN) rises by more than RISE
              over the previous captured frame. A new head stays near the centre for a few frames while its
              palette colour changes with distance travelled, so later rises within HEAD_GENS generations
              (60 ms) belong to the same head and are not new launches. A launch also needs the spawn pixel
              (80, mirror 79) to hold >= SPAWN_PEAK of the window's brightest point: a new head's core sits at
              the spawn pixel, whereas a broad colour shift of existing trails lifts the window off-centre
              (seen in the first repaired run: spawn pixel flat while the window max rose). Real launches cannot be that close in
              either mode: beat-grid launches are >= 387 ms apart (155 BPM) and bass onsets carry their own
              refractory (48 ms donor kick), so at worst two kicks 48-60 ms apart count as one launch.
  explained   a fresh BASS onset that the effects read (O line: event_id changed and bass_onset set) in the
              HEAD_GENS generations up to and including the launch frame.
  predicted   a launch while the render thread's consumed lock (V line c_locked) is 0 and nothing explains
              it: a beat drawn from the effect's own clock without a validated lock (the consumer gap).
Both biases of the 60 ms windows run towards UNDER-counting predicted cues. Applying the same rule to the
unrepaired and the repaired image does NOT make the miss rate equal: a repair that changes how a launch looks
can move launches into the blind spot (on R3 the rule sees 0 of Anticipate's eased launches). So a clean
result supports "zero DETECTED predicted cues", not "zero predicted cues". The stronger claim for the
lock-off image rests on the code instead (K1_TEMPO_CONSUMER_BANDS_V1): the beat grid learns a tempo only
while `locked`, which lock-off never sets, so the predicted-launch path cannot run. A lock-enabled image has
no such argument (the repair keeps an up-to-8-beat coast after a validated lock is lost) and needs its own
check.

  tempo_consumer_cues.py analyse --cases RUN/cases.json --out REPORT.json
  tempo_consumer_cues.py gate    --report REPORT.json [--expect gap|clean]
     clean: 0 predicted cues on every case and edge, AND launches still present on the R3 music case and the
            dev right-lock clips (reactive behaviour preserved). Exit 1 otherwise.
     gap:   the failure must be visible: >= 1 predicted cue on the R3 case and on the wrong-tempo clips.
            Exit 1 if the gap cannot be seen (the reproduction failed).
Exit: 0 rule met, 1 not met, 2 malformed input (e.g. a build without O lines).
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools/esp_emulator"))
import emu_capture as ec  # noqa: E402

CENTRE = ec.PX // 2                 # NATIVE_RESOLUTION / 2 = 80: the comet spawn pixel
WIN = 4                             # +-4 px around the spawn pixel
RISE = 0.10 * 3 * 65535             # centre luminance rise that counts as a new head (10 % of full white)
HEAD_GENS = 8                       # 60 ms at 7.5 ms per generation
EDGES = {"A": "tempo_comet", "B": "tempo_comet_anticipate"}


class InputError(Exception):
    pass


SPAWN_PEAK = 0.95                   # a new head's core is the brightest point at the spawn pixel


def centre_lum(wire: bytes) -> int:
    px = ec.wire_to_rgb16(wire)
    return max(sum(px[p]) for p in range(CENTRE - WIN, CENTRE + WIN + 1))


def spawn_lum(wire: bytes) -> int:
    """Brightness at the spawn pixel pair (80 and its mirror 79)."""
    px = ec.wire_to_rgb16(wire)
    return max(sum(px[CENTRE - 1]), sum(px[CENTRE]))


def onset_lines(uart: str) -> dict:
    """O,idx,event_id,bass_onset (K1_EMU_ONSET_TRACE builds): the onset event the effects read."""
    out = {}
    for ln in uart.splitlines():
        if ln.startswith("O,"):
            p = ln.strip().split(",")
            out[int(p[1])] = (int(p[2]), int(p[3]))
    return out


def suite_roles() -> dict:
    """Case id -> role, from the suite definition itself (dev-wrong-lock / dev-right-lock / the case id)."""
    sys.path.insert(0, str(ROOT / "scripts/regression-harness"))
    import tempo_lane_emu as tle
    return {c["id"]: c.get("role_note") or c["id"] for c in tle.suite("consumer")}


def analyse_case(case: dict, roles: dict) -> dict:
    run_dir = Path(case["streams"]).parent
    uart = (run_dir / "uart.txt").read_text(errors="replace")
    cap = ec.decode(uart)
    onsets = onset_lines(uart)
    frames = [f for f in sorted(cap.frames, key=lambda f: f.index) if f.index in cap.meanings]
    if not onsets or any(f.index not in onsets for f in frames):
        raise InputError(f"{case['id']}: no O lines for every captured frame (build without K1_EMU_ONSET_TRACE)")
    vm = cap.meanings
    gen = [vm[f.index].c_generation for f in frames]
    # Generations at which a fresh bass onset reached the effects.
    bass_gens = []
    for i in range(1, len(frames)):
        cur, prev = onsets[frames[i].index], onsets[frames[i - 1].index]
        if cur[0] != prev[0] and (cur[1] == 1 or gen[i] != gen[i - 1] + 1):
            bass_gens.append(gen[i])
    out = {"id": case["id"], "role": roles.get(case["id"], case["id"]), "frames": len(frames),
           "music_samples": case.get("music_samples"), "bass_onsets_seen": len(bass_gens)}
    locked = [vm[f.index].c_locked for f in frames]
    conf = [float(vm[f.index].c_confidence) for f in frames]
    out["locked_frac"] = round(sum(locked) / max(1, len(locked)), 4)
    out["tentative_frac"] = round(sum(1 for c in conf if 0.30 <= c < 0.60) / max(1, len(conf)), 4)
    for edge, name in EDGES.items():
        lum = [centre_lum(getattr(f, edge)) for f in frames]
        spawn = [spawn_lum(getattr(f, edge)) for f in frames]
        launches, unlocked, predicted, explained, last_launch_gen = [], 0, [], 0, -10 ** 9
        for i in range(1, len(frames)):
            if lum[i] - lum[i - 1] <= RISE or gen[i] - last_launch_gen <= HEAD_GENS:
                continue
            if spawn[i] < SPAWN_PEAK * lum[i]:
                continue                     # the new light is off-centre: a colour change, not a new head
            last_launch_gen = gen[i]
            launches.append(frames[i].ms)
            is_explained = any(gen[i] - HEAD_GENS <= g <= gen[i] for g in bass_gens)
            explained += is_explained
            if vm[frames[i].index].c_locked == 0:
                unlocked += 1
                if not is_explained:
                    predicted.append(frames[i].ms)
        out[name] = {"launches": len(launches), "launches_while_unlocked": unlocked,
                     "explained_by_bass_onset": explained, "predicted_cues_unlocked": len(predicted),
                     "alignment": round(explained / len(launches), 4) if launches else None,
                     "launch_ms": launches[:400], "predicted_ms": predicted[:200]}
    return out


def cmd_analyse(a) -> int:
    doc = json.loads(Path(a.cases).read_text())
    rows, roles = [], suite_roles()
    for c in doc["cases"]:
        if c["status"] != "PASS":
            print(f"INPUT: case {c['id']} emulator status {c['status']} {c.get('reasons')}")
            return 2
        try:
            rows.append(analyse_case(c, roles))
        except InputError as exc:
            print(f"INPUT: {exc}")
            return 2
    rep = {"cases_json": a.cases, "env": doc.get("env"), "git_head": doc.get("git_head"),
           "rule": {"centre_px": CENTRE, "window_px": WIN, "rise": RISE, "head_gens": HEAD_GENS,
                    "spawn_peak": SPAWN_PEAK}, "cases": rows}
    Path(a.out).write_text(json.dumps(rep, indent=1))
    for r in rows:
        print(r["id"], "lock", r["locked_frac"], "tent", r["tentative_frac"], "bass", r["bass_onsets_seen"],
              *[f"{n}: launches {r[n]['launches']} unlocked {r[n]['launches_while_unlocked']} "
                f"predicted {r[n]['predicted_cues_unlocked']} align {r[n]['alignment']}" for n in EDGES.values()],
              sep=" | ")
    return 0


def cmd_gate(a) -> int:
    rep = json.loads(Path(a.report).read_text())
    rows = {r["id"]: r for r in rep["cases"]}
    if "music-a" not in rows:
        print("INPUT: report lacks the R3 music-a case")
        return 2
    bad = []
    if a.expect == "clean":
        for r in rep["cases"]:
            for n in EDGES.values():
                if r[n]["predicted_cues_unlocked"]:
                    bad.append(f"{r['id']} {n}: {r[n]['predicted_cues_unlocked']} predicted cues without a lock")
        useful = [r for r in rep["cases"] if r["id"] == "music-a" or r["role"] == "dev-right-lock"]
        for r in useful:
            for n in EDGES.values():
                if r[n]["launches"] == 0:
                    bad.append(f"{r['id']} {n}: no launches at all (reactive behaviour lost)")
    else:
        wrong = [r for r in rep["cases"] if r["role"] == "dev-wrong-lock"]
        seen_r3 = any(rows["music-a"][n]["predicted_cues_unlocked"] for n in EDGES.values())
        seen_wrong = sum(1 for r in wrong if any(r[n]["predicted_cues_unlocked"] for n in EDGES.values()))
        if not seen_r3:
            bad.append("gap not visible on the R3 music case")
        if not wrong or seen_wrong == 0:
            bad.append("gap not visible on any wrong-tempo dev clip")
        print(f"gap visible: R3 {seen_r3}, wrong-tempo clips {seen_wrong}/{len(wrong)}")
    for b in bad:
        print("FAIL:", b)
    print(f"expect={a.expect} violations={len(bad)}")
    return 1 if bad else 0


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    an = sub.add_parser("analyse")
    an.add_argument("--cases", required=True)
    an.add_argument("--out", required=True)
    g = sub.add_parser("gate")
    g.add_argument("--report", required=True)
    g.add_argument("--expect", choices=("gap", "clean"), default="clean")
    a = p.parse_args(argv)
    return cmd_analyse(a) if a.cmd == "analyse" else cmd_gate(a)


if __name__ == "__main__":
    sys.exit(main())
