#!/usr/bin/env python3
"""Repeat one scenario case under parallel host load and localise any divergence.

    python3 tools/esp_emulator/stress_repeat.py run --case music-a --runs 20 --parallel 4 \
        --output _scratch/esp-emulator/<fresh>
    python3 tools/esp_emulator/stress_repeat.py analyse <uart.txt> <uart.txt> ...

Why it exists (ESP-Emulator docs/LESSONS.md F14-F17): a single clean repeat, or a
clean batch on a quiet machine, does not prove determinism. esp-emu interleaves its
two cores differently under host load. The render path once depended on wall time,
startup ordering and esp_random() and diverged in about 1 run in 8, only when loaded.

`run` builds nothing. It uses the already built emulator env, forces trace_novelty
on so producer CRCs exist (--no-trace runs without it), and runs N copies through run.run_case (the same
acceptance as the suite) with P worker processes. It then groups the native
payloads and, for each run that differs from the majority, reports where it first
diverged:
  producer : per-hop CRC of the published snapshot, spectrogram and chromagram differs
  handoff  : producer equal, but the frame's audio meaning (V lines) differs
  render   : both equal; reports the first differing render-state field (R lines) and pixels
It prints the rule-of-three bound: with k = 0 divergences in N runs, the true
divergence rate is below about 3/N at 95% confidence.
"""

from __future__ import annotations

import argparse
import collections
import concurrent.futures as cf
import copy
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import emu_capture as ec  # noqa: E402

RENDER_FIELDS = ("hue_position", "hue_shifting_mix", "MASTER_BRIGHTNESS", "silent_scale", "LED_FPS",
                 "audio_vu_level", "waveform_peak_scaled")


def _one(args: tuple) -> dict:
    scenario, case, out, index = args[:4]
    trace = args[4] if len(args) > 4 else True
    import run as runner  # noqa: WPS433 - each worker process imports its own copy
    sc = runner.load_scenario(Path(scenario))
    name = f"{case}-r{index:02d}"
    sc["cases"][name] = copy.deepcopy(sc["cases"][case])
    sc["cases"][name]["trace_novelty"] = trace   # --no-trace: the run without the N-line diagnostic
    lock = json.loads((HERE / "tool-lock.json").read_text())
    emu, _ = runner.resolve_esp_emu(lock)
    build_dir = runner.REPO / ".pio/build" / sc["profile"]["env"]
    # Decode the case's PCM in a per-run folder first and hand it to run_case through its asset cache.
    # run_case decodes inventory_excerpt assets into its output folder; parallel workers sharing that folder
    # raced on the same ffmpeg target ("already exists") and the losers ran with no valid PCM (lane R1,
    # 2026-10-21: 20/20 FAIL scenario_invalid on music-a at --parallel 8).
    work = Path(out) / f"{name}.asset"
    work.mkdir(parents=True, exist_ok=True)
    cache: dict = {}
    runner.load_asset(sc, sc["cases"][name]["pcm"], cache, work)
    rec = runner.run_case(sc, name, Path(out), emu, build_dir, cache, {})
    return {"name": name, "status": rec["status"], "reasons": rec.get("reasons", [])[:3],
            "uart": str(Path(out) / name / "uart.txt")}


def localise(base: ec.Capture, other: ec.Capture, hop_samples: int = 96) -> dict:
    """Where `other` first departs from `base`."""
    out: dict = {"side": None}
    pixel = next(((f.index, ec.frame_hop(base, f, hop_samples)) for f, g in zip(base.frames, other.frames)
                  if (f.A, f.B) != (g.A, g.B)), None)
    if len(base.frames) != len(other.frames):
        out["frame_count"] = (len(base.frames), len(other.frames))
    out["first_pixel_frame"], out["first_pixel_hop"] = pixel if pixel else (None, None)
    if pixel:
        f, g = base.frames[pixel[0]], other.frames[pixel[0]]
        for edge, (x, y) in (("A", (f.A, g.A)), ("B", (f.B, g.B))):
            px = [i for i, (p, q) in enumerate(zip(ec.wire_to_rgb16(x), ec.wire_to_rgb16(y))) if p != q]
            out[f"pixels_{edge}"] = px[:8] + (["..."] if len(px) > 8 else [])
    prod = next((g for g in sorted(base.novelty) if base.novelty[g] != other.novelty.get(g)), None)
    out["first_producer_divergence_hop"] = None if prod is None else prod - 1
    meaning = next((f.index for f in base.frames
                    if f.index in base.meanings and base.meanings[f.index] != other.meanings.get(f.index)), None)
    out["first_meaning_divergence_frame"] = meaning
    render = next((i for i in sorted(base.render_state) if base.render_state[i] != other.render_state.get(i)), None)
    out["first_render_state_frame"] = render
    if render is not None:
        a, b = base.render_state[render], other.render_state.get(render, ())
        out["render_state_fields"] = [RENDER_FIELDS[j] for j in range(min(len(a), len(b))) if a[j] != b[j]]
    if not base.novelty:
        out["note"] = "no N lines: run with trace_novelty to split producer from render side"
    if prod is not None:
        out["side"] = "producer"
    elif meaning is not None:
        out["side"] = "handoff"
    elif pixel is not None or render is not None:
        out["side"] = "render"
    return out


def analyse(paths: list[str]) -> dict:
    caps = {}
    for p in paths:
        try:
            caps[p] = ec.decode(Path(p).read_text(errors="replace"))
        except ec.CaptureError as exc:
            caps[p] = exc
    good = {p: c for p, c in caps.items() if isinstance(c, ec.Capture)}
    groups = collections.Counter(ec.payload_sha256(c) for c in good.values())
    report = {"runs": len(paths), "decoded": len(good), "undecodable": [p for p in caps if p not in good],
              "groups": {k[:12]: v for k, v in groups.most_common()}, "divergent": []}
    if not good:
        return report
    majority = groups.most_common(1)[0][0]
    base = next(c for c in good.values() if ec.payload_sha256(c) == majority)
    for p, c in good.items():
        if ec.payload_sha256(c) != majority:
            report["divergent"].append({"uart": p, "sha": ec.payload_sha256(c)[:12], **localise(base, c)})
    k, n = len(report["divergent"]) + len(report["undecodable"]), len(paths)
    report["divergence_count"] = k
    report["bound"] = (f"0 of {n} diverged: true rate below about {3 / n:.3f} at 95% confidence (rule of three)"
                       if k == 0 else f"{k} of {n} diverged ({k / n:.3f}); NOT deterministic")
    return report


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run")
    r.add_argument("--scenario", default=str(HERE / "s3_music_regression.json"))
    r.add_argument("--case", required=True)
    r.add_argument("--runs", type=int, default=20)
    r.add_argument("--parallel", type=int, default=4)
    r.add_argument("--output", required=True)
    r.add_argument("--no-trace", action="store_true",
                   help="run without the trace_novelty diagnostic (localisation then stops at handoff/render)")
    a = sub.add_parser("analyse")
    a.add_argument("uart", nargs="+")
    args = ap.parse_args()
    if args.cmd == "analyse":
        report = analyse(args.uart)
    else:
        out = Path(args.output).resolve()
        if out.exists():
            raise SystemExit(f"output already exists: {out}")
        out.mkdir(parents=True)
        jobs = [(str(Path(args.scenario).resolve()), args.case, str(out), i, not args.no_trace)
                for i in range(args.runs)]
        with cf.ProcessPoolExecutor(max_workers=args.parallel) as pool:
            runs = list(pool.map(_one, jobs))
        report = analyse([x["uart"] for x in runs])
        report["accepted"] = sum(1 for x in runs if x["status"] == "PASS")
        report["rejected"] = [x for x in runs if x["status"] != "PASS"]
        (out / "stress-report.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))
    return 0 if report.get("divergence_count", 1) == 0 and not report.get("rejected") else 1


if __name__ == "__main__":
    raise SystemExit(main())
