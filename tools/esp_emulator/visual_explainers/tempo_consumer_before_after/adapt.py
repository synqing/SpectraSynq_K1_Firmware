#!/usr/bin/env python3
"""Bind the retained music-a tempo-consumer captures to one film clock.

Reads the existing before/after cases, cues and UART. Rebuilds music-a PCM
through tempo_lane_emu.music_a_pcm and refuses it unless both case hashes
match. Does not re-run the emulator, change cue thresholds, or overwrite the
historical artefacts.

  python3 adapt.py export --before <consumer-before> --after <consumer-after> --output <fresh-dir>
  python3 adapt.py export --before <consumer-before> --after <consumer-after> \\
      --output <fresh-dir> --reuse-from <earlier-verified-dir> --stills 4.55
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
HERE = Path(__file__).resolve().parent
ENGINE = ROOT / "_scratch/raw-motion-toolchain/raw-motion"
SKILL = ROOT / "_scratch/raw-motion-toolchain/raw-motion-skill"
sys.path.insert(0, str(ROOT / "tools/esp_emulator"))
sys.path.insert(0, str(ROOT / "scripts/regression-harness"))

import emu_capture as ec  # noqa: E402
import tempo_consumer_cues as cues  # noqa: E402
import tempo_lane_emu as lane  # noqa: E402

RATE, HOP, PX = 12800, 96, 160
WINDOW_START = 1600 * HOP          # sample 153600 = 12.000 s = original 68.000 s
WINDOW_END = 281600                # musical end; excludes the final partial-hop pad
DUR = (WINDOW_END - WINDOW_START) / RATE
BEFORE = ROOT / "_scratch/esp-emulator/tempo-lock-r1/consumer-before"
AFTER = ROOT / "_scratch/esp-emulator/tempo-lock-r1/consumer-after"
PCM_SHA = "36a2713c5d18a8ad78ff115d3da51d93ea23aac14aa949a9307f382533a3718a"
FONT = Path("/System/Library/Fonts/Supplemental/Arial.ttf")
FONT_BOLD = Path("/System/Library/Fonts/Supplemental/Arial Bold.ttf")
ENGINE_PIN = "2e96bc3e5b1a3d214578d32338a0c49f73c1311a"
SKILL_PIN = "30bd029e63b1e5173a97edff53400d224deaa16c"
WINDOW_SHA = "d5964a5128de2ef2f974418eabdc6b3bdc81ee8c0610f5665c1a1f6bdbdd58bc"


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def file_sha(path: Path) -> str:
    return sha256(path.read_bytes())


def proj(c16: int) -> int:
    return round(c16 * 255 / 65535)


def epoch_us(uart: str) -> int | None:
    for ln in uart.splitlines():
        if ln.startswith("EMU_EPOCH "):
            for part in ln.split():
                if part.startswith("epoch_us="):
                    return int(part.split("=", 1)[1])
    return None


def header_line(uart: str) -> str:
    for ln in uart.splitlines():
        if ln.startswith("[RTRACE-BEGIN"):
            return ln.strip()
    return ""


def load_side(case_path: Path, cue_path: Path) -> dict:
    doc = json.loads(case_path.read_text())
    row = next(c for c in doc["cases"] if c["id"] == "music-a")
    if row["pcm_sha256"] != PCM_SHA or row["samples"] != 281600:
        raise SystemExit(f"{case_path}: music-a PCM identity is not the retained pair")
    uart_path = Path(row["streams"]).parent / "uart.txt"
    if not uart_path.is_file():
        uart_path = case_path.parent / "runs/lane-music-a/uart.txt"
    uart = uart_path.read_text(errors="replace")
    cap = ec.decode(uart)
    roles = cues.suite_roles()
    fresh = cues.analyse_case(row, roles)
    stored = next(c for c in json.loads(cue_path.read_text())["cases"] if c["id"] == "music-a")
    for key in ("locked_frac", "bass_onsets_seen", "frames"):
        if fresh[key] != stored[key]:
            raise SystemExit(f"{cue_path}: re-analysis {key} {fresh[key]} != stored {stored[key]}")
    for name in cues.EDGES.values():
        for key in ("launches", "predicted_cues_unlocked", "explained_by_bass_onset"):
            if fresh[name][key] != stored[name][key]:
                raise SystemExit(f"{cue_path}: {name}.{key} drifted")
        if fresh[name]["predicted_ms"] != stored[name]["predicted_ms"]:
            raise SystemExit(f"{cue_path}: {name} predicted timestamps drifted")
        if fresh[name]["launch_ms"] != stored[name]["launch_ms"]:
            raise SystemExit(f"{cue_path}: {name} launch timestamps drifted")
    epoch = epoch_us(uart)
    frames = []
    by_ms = {}
    for f in sorted(cap.frames, key=lambda item: item.index):
        side = cap.sidecars.get(f.index)
        meaning = cap.meanings.get(f.index)
        if side is None or meaning is None:
            raise SystemExit(f"frame {f.index} missing sidecar or meaning")
        if side.processed % HOP != 0:
            raise SystemExit(f"frame {f.index} processed {side.processed} is not a hop boundary")
        hop = side.processed // HOP - 1
        audio_s = side.processed / RATE
        app_s = side.app_us / 1_000_000
        if epoch is not None and side.app_us != epoch + (side.processed * 1_000_000) // RATE:
            raise SystemExit(f"frame {f.index} app_us is not epoch + processed/rate")
        if f.ms != side.app_us // 1000:
            raise SystemExit(f"frame {f.index} F.ms {f.ms} != app_us//1000")
        if int(meaning.c_generation) != side.generation:
            raise SystemExit(f"frame {f.index} meaning generation disagrees with sidecar")
        rec = {
            "index": f.index,
            "hop": hop,
            "ms": f.ms,
            "audio_s": round(audio_s, 6),
            "rel_s": round(audio_s - WINDOW_START / RATE, 6),
            "locked": int(meaning.c_locked),
            "bpm": float(meaning.c_bpm),
            "conf": float(meaning.c_confidence),
            "gen": int(meaning.c_generation),
            "mode": f.mode,
        }
        frames.append(rec)
        by_ms[f.ms] = len(frames) - 1
    hops = [r["hop"] for r in frames]
    if hops != list(range(hops[0], hops[0] + len(hops))):
        raise SystemExit("captured hops are not one contiguous run")
    rgb = bytearray(len(frames) * 2 * PX * 3)
    for i, f in enumerate(sorted(cap.frames, key=lambda item: item.index)):
        for e, wire in enumerate((f.A, f.B)):
            pixels = ec.wire_to_rgb16(wire)
            if len(pixels) != PX:
                raise SystemExit(f"frame {f.index} edge {e} has {len(pixels)} pixels")
            base = (i * 2 + e) * PX
            for p, (r, g, b) in enumerate(pixels):
                k = (base + p) * 3
                rgb[k:k + 3] = bytes((proj(r), proj(g), proj(b)))
    def times(ms_list: list[int]) -> list[float]:
        out = []
        for ms in ms_list:
            if ms not in by_ms:
                raise SystemExit(f"cue ms {ms} is not a captured frame")
            out.append(frames[by_ms[ms]]["rel_s"])
        return out

    # Bass-onset frames, same rule as tempo_consumer_cues.analyse_case.
    onsets = cues.onset_lines(uart)
    ordered = [f for f in sorted(cap.frames, key=lambda item: item.index) if f.index in cap.meanings]
    gen = [cap.meanings[f.index].c_generation for f in ordered]
    bass_rel = []
    for i in range(1, len(ordered)):
        cur, prev = onsets[ordered[i].index], onsets[ordered[i - 1].index]
        if cur[0] != prev[0] and (cur[1] == 1 or gen[i] != gen[i - 1] + 1):
            bass_rel.append(frames[by_ms[ordered[i].ms]]["rel_s"])
    if len(bass_rel) != fresh["bass_onsets_seen"]:
        raise SystemExit("bass onset count drifted while resolving times")
    summary = {}
    for name in cues.EDGES.values():
        summary[name] = {
            "launches": fresh[name]["launches"],
            "predicted": fresh[name]["predicted_cues_unlocked"],
            "explained": fresh[name]["explained_by_bass_onset"],
            "launch_rel_s": times(fresh[name]["launch_ms"]),
            "predicted_rel_s": times(fresh[name]["predicted_ms"]),
            "recorded_launch_ms": fresh[name]["launch_ms"],
            "recorded_predicted_ms": fresh[name]["predicted_ms"],
        }
    return {
        "env": doc.get("env"),
        "git_head": doc.get("git_head"),
        "header": header_line(uart),
        "epoch_us": epoch,
        "uart_sha256": sha256(uart.encode("utf-8", "replace")),
        "cases_sha256": file_sha(case_path),
        "cues_sha256": file_sha(cue_path),
        "locked_frac": fresh["locked_frac"],
        "bass_onsets_seen": fresh["bass_onsets_seen"],
        "frames": frames,
        "bass_rel_s": bass_rel,
        "edges": summary,
        "rgb": bytes(rgb),
        "row_status": row["status"],
        "tempo_lane": row.get("tempo_lane"),
    }


def rebuild_pcm(dest: Path) -> dict:
    import run as runner
    with tempfile.TemporaryDirectory(prefix="tempo-pilot02-") as tmp:
        sc = runner.load_scenario(ROOT / "tools/esp_emulator/s3_music_regression.json")
        cache: dict = {}
        pcm, meta = runner.load_asset(sc, "music_chorus", cache, Path(tmp))
        loreen = cache["loreen_src"][1]
    got = sha256(pcm)
    if got != PCM_SHA or len(pcm) // 2 != 281600:
        raise SystemExit(f"rebuilt PCM {got} samples {len(pcm)//2} != retained music-a")
    excerpt = pcm[WINDOW_START * 2:WINDOW_END * 2]
    if len(excerpt) != (WINDOW_END - WINDOW_START) * 2:
        raise SystemExit("excerpt length is not the 10.000 s musical window")
    (dest / "music-a.s16le").write_bytes(pcm)
    (dest / "window.s16le").write_bytes(excerpt)
    conv = loreen.get("conversion") or {}
    return {
        "pcm_sha256": got,
        "samples": len(pcm) // 2,
        "excerpt_sha256": sha256(excerpt),
        "excerpt_samples": len(excerpt) // 2,
        "applied_gain": conv.get("applied_gain"),
        "decoded_peak": conv.get("decoded_peak"),
        "source_sha256": loreen.get("source_sha256"),
        "ffmpeg": conv.get("ffmpeg"),
        "concat_samples": meta.get("samples"),
    }


def write_evidence(dest: Path, before: dict, after: dict, pcm_meta: dict) -> None:
    def pub(side: dict) -> dict:
        return {k: v for k, v in side.items() if k != "rgb"}

    meta = {
        "schema": "k1-tempo-consumer-film/1",
        "rate_hz": RATE,
        "hop_samples": HOP,
        "px": PX,
        "projection": "round(c16 * 255 / 65535), linear, per channel",
        "clock": "audio_s = processed_samples / 12800; rel_s = audio_s - 12.0; F.ms is app_us//1000 = epoch + audio",
        "window": {
            "start_sample": WINDOW_START,
            "end_sample": WINDOW_END,
            "dur_s": DUR,
            "original_start_s": 68.0,
            "note": "Final partial hop past sample 281600 is excluded. It is zero pad, not musical duration.",
        },
        "pcm": pcm_meta,
        "before": pub(before),
        "after": pub(after),
        "whole_case": {
            "lock_fraction": [before["locked_frac"], after["locked_frac"]],
            "bass_onsets": [before["bass_onsets_seen"], after["bass_onsets_seen"]],
            "comet_launches": [before["edges"]["tempo_comet"]["launches"], after["edges"]["tempo_comet"]["launches"]],
            "comet_predicted": [before["edges"]["tempo_comet"]["predicted"], after["edges"]["tempo_comet"]["predicted"]],
            "anticipate_launches_detected": [
                before["edges"]["tempo_comet_anticipate"]["launches"],
                after["edges"]["tempo_comet_anticipate"]["launches"],
            ],
            "anticipate_predicted": [
                before["edges"]["tempo_comet_anticipate"]["predicted"],
                after["edges"]["tempo_comet_anticipate"]["predicted"],
            ],
        },
    }
    (dest / "timeline.json").write_text(json.dumps(meta, indent=1))
    (dest / "before.rgb").write_bytes(before["rgb"])
    (dest / "after.rgb").write_bytes(after["rgb"])
    payload = {
        "meta": meta,
        "beforeB64": base64.b64encode(before["rgb"]).decode("ascii"),
        "afterB64": base64.b64encode(after["rgb"]).decode("ascii"),
    }
    (dest / "evidence.js").write_text("window.EVIDENCE = " + json.dumps(payload, separators=(",", ":")) + ";\n")


def stage(run: Path) -> None:
    project = run / "project"
    if project.exists():
        shutil.rmtree(project)
    project.mkdir(parents=True)
    for name in ("index.html", "comp.js"):
        shutil.copy2(HERE / "scene" / name, project / name)
    shutil.copy2(ENGINE / "engine/motion.js", project / "motion.js")
    shutil.copy2(ENGINE / "LICENSE", project / "RAW-MOTION-LICENSE.txt")
    font_dir = project / "fonts"
    font_dir.mkdir()
    shutil.copyfile(FONT, font_dir / "Arial.ttf")
    shutil.copyfile(FONT_BOLD, font_dir / "ArialBold.ttf")
    ann = json.loads((HERE / "annotations.json").read_text())
    (project / "annotations.js").write_text("window.ANNOTATIONS = " + json.dumps(ann) + ";\n")
    for name in ("evidence.js",):
        shutil.copy2(run / name, project / name)


def resolve(path: Path) -> Path:
    return path if path.is_absolute() else ROOT / path


def require_engine() -> None:
    head = subprocess.check_output(
        ["/usr/bin/git", "-C", str(ENGINE), "rev-parse", "HEAD"], text=True
    ).strip()
    if head != ENGINE_PIN:
        raise SystemExit(f"raw-motion at {ENGINE} is {head}, pin is {ENGINE_PIN}")


def prepare_run(before_dir: Path, after_dir: Path, run: Path) -> None:
    before = load_side(before_dir / "cases.json", before_dir / "cues.json")
    after = load_side(after_dir / "cases.json", after_dir / "cues.json")
    if before["frames"][0]["hop"] != after["frames"][0]["hop"]:
        raise SystemExit("before/after do not start on the same hop")
    if [r["rel_s"] for r in before["frames"]] != [r["rel_s"] for r in after["frames"]]:
        raise SystemExit("before/after audio clocks differ")
    if any(r["locked"] for r in before["frames"] + after["frames"]):
        raise SystemExit("a captured frame has published lock set; the film's lock badge would be a lie")
    pcm_meta = rebuild_pcm(run)
    if pcm_meta["excerpt_sha256"] != WINDOW_SHA:
        raise SystemExit(f"window PCM {pcm_meta['excerpt_sha256']} != retained {WINDOW_SHA}")
    write_evidence(run, before, after, pcm_meta)


def reuse_evidence(src: Path, run: Path) -> None:
    window = src / "window.s16le"
    if file_sha(window) != WINDOW_SHA:
        raise SystemExit(f"{window} is not the retained 10 s window")
    run.mkdir(parents=True, exist_ok=True)
    for name in ("evidence.js", "timeline.json", "window.s16le", "music-a.s16le", "before.rgb", "after.rgb"):
        shutil.copyfile(src / name, run / name)


def render_project(project: Path, stills: str | None) -> None:
    require_engine()
    cmd = [
        "node", str(ENGINE / "engine/render.mjs"),
        "--project", str(project),
        "--w", "1920", "--h", "1080", "--fps", "60", "--dur", "10",
        "--sub", "1", "--shutter", "0", "--workers", "1",
    ]
    if stills:
        cmd.extend(["--stills", stills])
    print(" ".join(cmd), flush=True)
    subprocess.run(cmd, check=True, timeout=1200)


def mux_film(project: Path, run: Path, mp4: Path, copy_audio: Path | None) -> None:
    frames = project / "frames"
    pngs = sorted(frames.glob("*.png"))
    if len(pngs) != 600:
        raise SystemExit(f"{frames} has {len(pngs)} frames, expected 600")
    cmd = [
        "ffmpeg", "-y", "-loglevel", "error",
        "-framerate", "60", "-start_number", "0", "-i", str(frames / "%05d.png"),
    ]
    if copy_audio:
        cmd.extend(["-i", str(copy_audio), "-map", "0:v:0", "-map", "1:a:0", "-c:a", "copy"])
    else:
        cmd.extend([
            "-f", "s16le", "-ar", "12800", "-ac", "1", "-i", str(run / "window.s16le"),
            "-map", "0:v:0", "-map", "1:a:0",
            "-c:a", "aac", "-b:a", "192k", "-ar", "48000",
        ])
    cmd.extend([
        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-r", "60", "-crf", "18",
        "-muxpreload", "0", "-muxdelay", "0", "-movflags", "+faststart", str(mp4),
    ])
    print(" ".join(cmd), flush=True)
    subprocess.run(cmd, check=True, timeout=180)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest="cmd", required=True)

    prep = sub.add_parser("prepare", help="decode the two captures and rebuild the shared PCM")
    prep.add_argument("--before", type=Path, required=True)
    prep.add_argument("--after", type=Path, required=True)
    prep.add_argument("--output", type=Path, required=True)

    st = sub.add_parser("stage", help="copy the scene onto an output directory that already has evidence.js")
    st.add_argument("--output", type=Path, required=True)
    st.add_argument("--reuse-from", type=Path)

    rnd = sub.add_parser("render", help="render the staged project")
    rnd.add_argument("--output", type=Path, required=True)
    rnd.add_argument("--stills", default=None)

    mx = sub.add_parser("mux", help="mux 600 frames with the retained window, or copy an existing AAC stream")
    mx.add_argument("--output", type=Path, required=True)
    mx.add_argument("--mp4", type=Path, required=True)
    mx.add_argument("--copy-audio", type=Path)

    exp = sub.add_parser("export", help="prepare or reuse, stage, render, and mux one film")
    exp.add_argument("--before", type=Path, required=True)
    exp.add_argument("--after", type=Path, required=True)
    exp.add_argument("--output", type=Path, required=True)
    exp.add_argument("--reuse-from", type=Path)
    exp.add_argument("--copy-audio", type=Path)
    exp.add_argument("--stills", default=None)
    exp.add_argument("--mp4", type=Path)

    args = ap.parse_args()
    if args.cmd == "prepare":
        run = resolve(args.output)
        run.mkdir(parents=True, exist_ok=True)
        prepare_run(resolve(args.before), resolve(args.after), run)
        stage(run)
        print(f"staged {run / 'project'}")
        return 0
    if args.cmd == "stage":
        run = resolve(args.output)
        if args.reuse_from:
            reuse_evidence(resolve(args.reuse_from), run)
        if not (run / "evidence.js").is_file():
            raise SystemExit("evidence.js missing")
        stage(run)
        print(f"staged {run / 'project'}")
        return 0
    if args.cmd == "render":
        render_project(resolve(args.output) / "project", args.stills)
        return 0
    if args.cmd == "mux":
        run = resolve(args.output)
        mux_film(run / "project", run, resolve(args.mp4), resolve(args.copy_audio) if args.copy_audio else None)
        return 0
    run = resolve(args.output)
    run.mkdir(parents=True, exist_ok=True)
    if args.reuse_from:
        reuse_evidence(resolve(args.reuse_from), run)
    else:
        prepare_run(resolve(args.before), resolve(args.after), run)
    stage(run)
    render_project(run / "project", args.stills)
    if args.stills:
        print(f"stills {run / 'project' / 'stills'}")
        return 0
    mp4 = resolve(args.mp4) if args.mp4 else run / "why-lock-off-did-not-stop-false-beat-cues.mp4"
    mux_film(run / "project", run, mp4, resolve(args.copy_audio) if args.copy_audio else None)
    print(mp4)
    return 0


if __name__ == "__main__":
    sys.exit(main())
