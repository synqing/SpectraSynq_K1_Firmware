#!/usr/bin/env python3
"""Run K1 APCAD captures against the P4 real local music corpus.

This is a live-device runner. It renders metadata-indexed P4 stems to temporary
mono WAV clips, then delegates each clip to `device_ap_cadence_capture.py`.
It never generates synthetic click/silence material and never sends calibration
commands.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import re
import subprocess
import sys
import time
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_P4_ROOT = Path(
    "/Users/spectrasynq/Workspace_Management/Software/P4-nano/"
    "I2S_Audio_Demo-Waveshare_ESP32-P4-NANO"
)
DEFAULT_OUT_PARENT = ROOT / "docs" / "forensics" / "runtime-evidence"
DEFAULT_RENDER_PARENT = ROOT / "build" / "k1-real-music-rendered"
DEFAULT_CAPTURE_SCRIPT = ROOT / "scripts" / "regression-harness" / "device_ap_cadence_capture.py"
DEFAULT_REFERENCE_IDS = [
    "eric-clapton-wonderful-tonight-95bpm",
    "tie-sto-thebusiness-120bpm",
    "fisher-losingit-125bpm",
    "avicii-levels-126bpm",
    "lavern-inmymind-130bpm",
    "charlottedewitte-sgadilimi-135bpm",
    "arminvanbuuren-sonicsamba-142bpm",
    "tntrecords-skyfire-151bpm",
    "subfocus-solarsystem-174bpm",
]
CRASH_MARKER_RE = re.compile(
    r"(Guru Meditation|Task watchdog|Backtrace:|panic|Brownout|abort\(|rst:0x[0-9a-fA-F]+)",
    re.IGNORECASE,
)
EXPECTED_USB_RESET_MARKER = "rst:0x15"


class RealCorpusCaptureError(RuntimeError):
    """Raised when the real-corpus capture runner cannot continue."""


def timestamp() -> str:
    return time.strftime("%Y%m%dT%H%M%S", time.localtime())


def load_p4_runner(p4_root: Path) -> Any:
    module_path = p4_root / "tools" / "run_local_music_corpus_matrix.py"
    if not module_path.exists():
        raise RealCorpusCaptureError(f"P4 runner not found: {module_path}")
    tools_dir = module_path.parent
    if str(tools_dir) not in sys.path:
        sys.path.insert(0, str(tools_dir))
    spec = importlib.util.spec_from_file_location("p4_local_music_matrix", module_path)
    if spec is None or spec.loader is None:
        raise RealCorpusCaptureError(f"cannot load P4 runner: {module_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def p4_manifest_path(p4_root: Path) -> Path:
    return p4_root / "docs" / "bench" / "audio-references" / "p4-local-music-corpus.json"


def load_corpus(p4_runner: Any, corpus_path: Path) -> dict[str, Any]:
    corpus = p4_runner.load_corpus(corpus_path)
    if corpus.get("source_policy") != "metadata_only_no_audio_bytes_committed":
        raise RealCorpusCaptureError("P4 corpus must remain metadata-only")
    if corpus.get("committed_audio_bytes") is not False:
        raise RealCorpusCaptureError("P4 corpus must not mark audio bytes as committed")
    return corpus


def select_reference_ids(corpus: dict[str, Any], requested: list[str] | None) -> list[str]:
    refs = {str(item["id"]) for item in corpus.get("references", [])}
    selected = requested or [ref_id for ref_id in DEFAULT_REFERENCE_IDS if ref_id in refs]
    unknown = [ref_id for ref_id in selected if ref_id not in refs]
    if unknown:
        raise RealCorpusCaptureError(f"unknown reference id(s): {', '.join(unknown)}")
    if not selected:
        raise RealCorpusCaptureError("no reference ids selected")
    return selected


def role_paths_for_capture(p4_runner: Any, reference: dict[str, Any], profile: dict[str, Any], mix_policy: str) -> tuple[list[Path], list[str]]:
    if mix_policy == "profile":
        roles = profile.get("mix_roles")
        if roles:
            return p4_runner.stems_for_roles(reference, include_roles=set(roles)), list(roles)
    return p4_runner.stems_for_roles(reference), ["all_musical_excluding_metronome"]


def rendered_clip_path(render_root: Path, ref_id: str, window_id: str, profile_id: str, mix_policy: str) -> Path:
    safe = re.sub(r"[^A-Za-z0-9_.-]+", "-", f"{ref_id}.{window_id}.{profile_id}.{mix_policy}")
    return render_root / ref_id / f"{safe}.k1-real-music.48k-mono-s16.wav"


def render_reference_clip(
    p4_runner: Any,
    reference: dict[str, Any],
    *,
    profile_id: str,
    mix_policy: str,
    render_duration_ms: int,
    render_root: Path,
) -> dict[str, Any]:
    ref_id = str(reference["id"])
    profile = p4_runner.resolve_profile(reference, profile_id)
    window = dict(profile["window"])
    start_s = float(window["start_s"])
    duration_s = min(float(render_duration_ms) / 1000.0, float(window["duration_s"]))
    stems, roles = role_paths_for_capture(p4_runner, reference, profile, mix_policy)
    output = rendered_clip_path(render_root, ref_id, str(window["id"]), profile_id, mix_policy)
    command = p4_runner.render_stems_to_mono_wav(
        stems,
        start_s=start_s,
        duration_s=duration_s,
        output_path=output,
    )
    return {
        "reference_id": ref_id,
        "title": reference.get("title"),
        "expected_bpm": reference.get("expected_bpm"),
        "corpus_role": reference.get("corpus_role"),
        "profile_id": profile_id,
        "mix_policy": mix_policy,
        "mix_roles": roles,
        "window": {
            **window,
            "capture_start_s": start_s,
            "capture_duration_s": duration_s,
        },
        "rendered_wav": str(output),
        "render_command": command,
        "source_policy": reference.get("source_policy"),
        "committed_audio_bytes": reference.get("committed_audio_bytes"),
    }


def build_capture_command(
    *,
    capture_script: Path,
    rendered_wav: Path,
    port: str,
    duration_ms: int,
    start_ms: int,
    post_wait_ms: int,
    out_dir: Path,
    label: str,
    expected_sample_rate: int,
    expected_samples_per_chunk: int,
    expected_novelty_decimation: int,
    player: str,
    playback_gain_db: float,
    compact_soak: bool = False,
) -> list[str]:
    command = [
        sys.executable,
        str(capture_script),
        "--track",
        str(rendered_wav),
        "--port",
        port,
        "--duration-ms",
        str(duration_ms),
        "--start-ms",
        str(start_ms),
        "--post-wait-ms",
        str(post_wait_ms),
        "--out-dir",
        str(out_dir),
        "--label",
        label,
        "--expected-sample-rate",
        str(expected_sample_rate),
        "--expected-samples-per-chunk",
        str(expected_samples_per_chunk),
        "--expected-novelty-decimation",
        str(expected_novelty_decimation),
        "--player",
        player,
        "--playback-gain-db",
        f"{playback_gain_db:.3f}",
    ]
    if compact_soak:
        command.append("--compact-soak")
    return command


def load_capture_summary(stdout: str) -> tuple[dict[str, Any], dict[str, Any] | None]:
    payload = json.loads(stdout)
    summary_path = payload.get("summary_json")
    if not summary_path:
        return payload, None
    path = Path(str(summary_path))
    if not path.exists():
        return payload, None
    return payload, json.loads(path.read_text(encoding="utf-8"))


def crash_marker_hits(raw_log: str | None) -> list[str]:
    if not raw_log:
        return []
    path = Path(raw_log)
    if not path.exists():
        return []
    hits: list[str] = []
    for line in path.read_text(errors="replace").splitlines():
        if EXPECTED_USB_RESET_MARKER in line:
            continue
        if CRASH_MARKER_RE.search(line):
            hits.append(line.strip())
    return hits[:20]


def hard_failures(summary: dict[str, Any] | None, expected_sample_rate: int, expected_samples_per_chunk: int, expected_novelty_decimation: int) -> list[str]:
    if summary is None:
        return ["missing_capture_summary"]
    failures: list[str] = []
    if int(summary.get("row_count") or 0) <= 0:
        failures.append("no_apcad_rows")
    if summary.get("active_sample_rate_mode") != expected_sample_rate:
        failures.append("sample_rate_mismatch")
    if summary.get("active_samples_per_chunk_mode") != expected_samples_per_chunk:
        failures.append("samples_per_chunk_mismatch")
    if summary.get("active_tempo_decimation_mode") != expected_novelty_decimation:
        failures.append("novelty_decimation_mismatch")
    for key in ("i2s_not_ok_count", "bytes_mismatch_count", "frame_gap_count", "timestamp_regression_count", "core_bad_count"):
        if int(summary.get(key) or 0) != 0:
            failures.append(key)
    for key in ("active_ap_work_over_7500_count", "emitted_active_ap_work_over_7500_count"):
        if int(summary.get(key) or 0) != 0:
            failures.append(key)
    raw_log = summary.get("raw_log")
    if isinstance(raw_log, str) and crash_marker_hits(raw_log):
        failures.append("crash_marker")
    return failures


def should_stop_after_failures(failures: list[str], continue_on_failure: bool) -> bool:
    if not failures:
        return False
    if not continue_on_failure:
        return True
    return any(failure in {"capture_command_failed", "crash_marker"} for failure in failures)


def compact_entry(render: dict[str, Any], capture_payload: dict[str, Any], capture_summary: dict[str, Any] | None, failures: list[str]) -> dict[str, Any]:
    timing = (capture_summary or {}).get("timing_us") or {}
    active = timing.get("active_ap_work_elapsed_us") or {}
    emitted = timing.get("emitted_active_ap_work_elapsed_us") or {}
    raw_log = (capture_summary or {}).get("raw_log")
    return {
        "reference_id": render["reference_id"],
        "expected_bpm": render["expected_bpm"],
        "corpus_role": render["corpus_role"],
        "profile_id": render["profile_id"],
        "mix_policy": render["mix_policy"],
        "mix_roles": render["mix_roles"],
        "window": render["window"],
        "rendered_wav": render["rendered_wav"],
        "capture": capture_payload,
        "hard_failures": failures,
        "passed_runtime_gate": not failures,
        "crash_marker_hits": crash_marker_hits(raw_log if isinstance(raw_log, str) else None),
        "summary_extract": {
            "row_count": (capture_summary or {}).get("row_count"),
            "classification": (capture_summary or {}).get("classification"),
            "classification_reason": (capture_summary or {}).get("classification_reason"),
            "active_sample_rate_mode": (capture_summary or {}).get("active_sample_rate_mode"),
            "active_samples_per_chunk_mode": (capture_summary or {}).get("active_samples_per_chunk_mode"),
            "active_tempo_decimation_mode": (capture_summary or {}).get("active_tempo_decimation_mode"),
            "measured_ap_frame_rate_hz": (capture_summary or {}).get("measured_ap_frame_rate_hz"),
            "measured_emitted_novelty_rate_hz": (capture_summary or {}).get("measured_emitted_novelty_rate_hz"),
            "i2s_not_ok_count": (capture_summary or {}).get("i2s_not_ok_count"),
            "bytes_mismatch_count": (capture_summary or {}).get("bytes_mismatch_count"),
            "core_bad_count": (capture_summary or {}).get("core_bad_count"),
            "frame_gap_count": (capture_summary or {}).get("frame_gap_count"),
            "timestamp_regression_count": (capture_summary or {}).get("timestamp_regression_count"),
            "active_ap_work_p95_us": active.get("p95"),
            "active_ap_work_max_us": active.get("max"),
            "emitted_active_ap_work_p95_us": emitted.get("p95"),
            "emitted_active_ap_work_max_us": emitted.get("max"),
            "active_ap_work_over_7500_count": (capture_summary or {}).get("active_ap_work_over_7500_count"),
            "emitted_active_ap_work_over_7500_count": (capture_summary or {}).get("emitted_active_ap_work_over_7500_count"),
            "compact_soak_mode": (capture_summary or {}).get("compact_soak_mode"),
            "raw_log": raw_log,
            "summary_json": (capture_summary or {}).get("summary_json") or capture_payload.get("summary_json"),
        },
    }


def aggregate_segment_entries(render: dict[str, Any], segments: list[dict[str, Any]]) -> dict[str, Any]:
    failures: list[str] = []
    crash_hits: list[str] = []
    extracts = [segment.get("summary_extract") or {} for segment in segments]
    for segment in segments:
        for failure in segment.get("hard_failures") or []:
            if failure not in failures:
                failures.append(str(failure))
        crash_hits.extend(segment.get("crash_marker_hits") or [])

    def sum_int(key: str) -> int:
        total = 0
        for extract in extracts:
            try:
                total += int(extract.get(key) or 0)
            except (TypeError, ValueError):
                pass
        return total

    def max_float(key: str) -> float | None:
        values: list[float] = []
        for extract in extracts:
            value = extract.get(key)
            if isinstance(value, (int, float)):
                values.append(float(value))
        return max(values) if values else None

    def mean_float(key: str) -> float | None:
        values: list[float] = []
        for extract in extracts:
            value = extract.get(key)
            if isinstance(value, (int, float)):
                values.append(float(value))
        return sum(values) / len(values) if values else None

    return {
        "reference_id": render["reference_id"],
        "expected_bpm": render["expected_bpm"],
        "corpus_role": render["corpus_role"],
        "profile_id": render["profile_id"],
        "mix_policy": render["mix_policy"],
        "mix_roles": render["mix_roles"],
        "window": render["window"],
        "rendered_wav": render["rendered_wav"],
        "segments": segments,
        "segment_count": len(segments),
        "capture": {"mode": "segmented"},
        "hard_failures": failures,
        "passed_runtime_gate": not failures,
        "crash_marker_hits": crash_hits[:20],
        "summary_extract": {
            "row_count": sum_int("row_count"),
            "classification": "segmented_aggregate",
            "classification_reason": "aggregate over repeated APCAD buffer-sized real-music capture windows",
            "active_sample_rate_mode": extracts[0].get("active_sample_rate_mode") if extracts else None,
            "active_samples_per_chunk_mode": extracts[0].get("active_samples_per_chunk_mode") if extracts else None,
            "active_tempo_decimation_mode": extracts[0].get("active_tempo_decimation_mode") if extracts else None,
            "measured_ap_frame_rate_hz": mean_float("measured_ap_frame_rate_hz"),
            "measured_emitted_novelty_rate_hz": mean_float("measured_emitted_novelty_rate_hz"),
            "i2s_not_ok_count": sum_int("i2s_not_ok_count"),
            "bytes_mismatch_count": sum_int("bytes_mismatch_count"),
            "core_bad_count": sum_int("core_bad_count"),
            "frame_gap_count": sum_int("frame_gap_count"),
            "timestamp_regression_count": sum_int("timestamp_regression_count"),
            "active_ap_work_p95_us": max_float("active_ap_work_p95_us"),
            "active_ap_work_max_us": max_float("active_ap_work_max_us"),
            "emitted_active_ap_work_p95_us": max_float("emitted_active_ap_work_p95_us"),
            "emitted_active_ap_work_max_us": max_float("emitted_active_ap_work_max_us"),
            "active_ap_work_over_7500_count": sum_int("active_ap_work_over_7500_count"),
            "emitted_active_ap_work_over_7500_count": sum_int("emitted_active_ap_work_over_7500_count"),
            "summary_json": [segment.get("summary_extract", {}).get("summary_json") for segment in segments],
        },
    }


def write_markdown(manifest: dict[str, Any], path: Path) -> None:
    lines = [
        "# K1 Real Music Corpus APCAD Capture",
        "",
        f"- Generated: `{manifest['generated_at']}`",
        f"- Status: `{manifest['status']}`",
        f"- Tuple: `{manifest['expected_tuple']}`",
        f"- Profile: `{manifest['profile_id']}`",
        f"- Mix policy: `{manifest['mix_policy']}`",
        f"- Source corpus: `{manifest['corpus_path']}`",
        "",
        "## Results",
        "",
        "| Reference | BPM | Role | AP Hz | NOV Hz | Active P95 us | Active Max us | Failures |",
        "|-----------|-----|------|-------|--------|---------------|---------------|----------|",
    ]
    for entry in manifest["results"]:
        extract = entry["summary_extract"]
        lines.append(
            f"| `{entry['reference_id']}` | "
            f"{float(entry['expected_bpm']):.3f} | "
            f"`{entry['corpus_role']}` | "
            f"{extract.get('measured_ap_frame_rate_hz') or 'n/a'} | "
            f"{extract.get('measured_emitted_novelty_rate_hz') or 'n/a'} | "
            f"{extract.get('active_ap_work_p95_us') or 'n/a'} | "
            f"{extract.get('active_ap_work_max_us') or 'n/a'} | "
            f"`{','.join(entry['hard_failures']) or 'none'}` |"
        )
    lines.extend(
        [
            "",
            "## Boundary",
            "",
            "- Real P4 musical stems are rendered locally; metronome stems are excluded unless `--mix-policy profile` explicitly selects otherwise.",
            "- This runner does not send calibration, erase, reset, upload, or tuning commands.",
            "- A pass here is a real-music runtime stress gate, not production promotion by itself.",
        ]
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--p4-root", type=Path, default=DEFAULT_P4_ROOT)
    parser.add_argument("--corpus", type=Path)
    parser.add_argument("--reference-id", action="append", dest="reference_ids")
    parser.add_argument("--profile", default="steady_phase")
    parser.add_argument("--mix-policy", choices=("all_musical", "profile"), default="all_musical")
    parser.add_argument("--port", default="/dev/cu.usbmodem12201")
    parser.add_argument("--duration-ms", type=int, default=17000)
    parser.add_argument(
        "--soak-duration-ms",
        type=int,
        help="Total real-music duration per reference; values above duration-ms use compact on-device APCAD soak.",
    )
    parser.add_argument("--post-wait-ms", type=int, default=1500)
    parser.add_argument("--expected-sample-rate", type=int, default=16000)
    parser.add_argument("--expected-samples-per-chunk", type=int, default=120)
    parser.add_argument("--expected-novelty-decimation", type=int, default=3)
    parser.add_argument("--player", choices=("afplay", "ffplay"), default="ffplay")
    parser.add_argument("--playback-gain-db", type=float, default=0.0)
    parser.add_argument("--capture-script", type=Path, default=DEFAULT_CAPTURE_SCRIPT)
    parser.add_argument("--out-dir", type=Path)
    parser.add_argument(
        "--render-dir",
        type=Path,
        help="Directory for temporary rendered WAVs; defaults to ignored build/ storage.",
    )
    parser.add_argument("--label", default="k1_real_music_corpus")
    parser.add_argument("--render-only", action="store_true")
    parser.add_argument(
        "--continue-on-failure",
        action="store_true",
        help="Continue the corpus after metric failures; still stop on capture command failures or crash markers.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.duration_ms <= 0 or args.duration_ms > 20000:
        raise RealCorpusCaptureError("duration-ms must be in (0, 20000]")
    soak_duration_ms = int(args.soak_duration_ms or args.duration_ms)
    if soak_duration_ms <= 0:
        raise RealCorpusCaptureError("soak-duration-ms must be > 0")
    if soak_duration_ms < args.duration_ms:
        raise RealCorpusCaptureError("soak-duration-ms must be >= duration-ms")
    compact_soak = soak_duration_ms > args.duration_ms
    p4_root = args.p4_root.expanduser().resolve()
    corpus_path = (args.corpus or p4_manifest_path(p4_root)).expanduser().resolve()
    out_dir = (
        args.out_dir or (DEFAULT_OUT_PARENT / f"{timestamp()}-k1-real-music-corpus")
    ).expanduser().resolve()
    captures_dir = out_dir / "captures"
    render_root = (
        args.render_dir or (DEFAULT_RENDER_PARENT / out_dir.name)
    ).expanduser().resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    captures_dir.mkdir(parents=True, exist_ok=True)
    render_root.mkdir(parents=True, exist_ok=True)

    p4_runner = load_p4_runner(p4_root)
    corpus = load_corpus(p4_runner, corpus_path)
    refs = p4_runner.references_by_id(corpus)
    selected_ids = select_reference_ids(corpus, args.reference_ids)

    manifest: dict[str, Any] = {
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "label": args.label,
        "p4_root": str(p4_root),
        "corpus_path": str(corpus_path),
        "source_policy": corpus.get("source_policy"),
        "committed_audio_bytes": corpus.get("committed_audio_bytes"),
        "reference_ids": selected_ids,
        "profile_id": args.profile,
        "mix_policy": args.mix_policy,
        "expected_tuple": f"{args.expected_sample_rate}/{args.expected_samples_per_chunk}/d{args.expected_novelty_decimation}",
        "port": args.port,
        "duration_ms": args.duration_ms,
        "soak_duration_ms": soak_duration_ms,
        "capture_mode": "compact_soak" if compact_soak else "buffered_apcad",
        "segments_per_reference": 1,
        "render_root": str(render_root),
        "post_wait_ms": args.post_wait_ms,
        "render_only": bool(args.render_only),
        "continue_on_failure": bool(args.continue_on_failure),
        "non_actions": ["no calibration", "no upload", "no reset", "no tuning", "no synthetic track generation"],
        "results": [],
    }

    for ref_id in selected_ids:
        print(f"[k1-real-corpus] render {ref_id} total_ms={soak_duration_ms}", flush=True)
        render = render_reference_clip(
            p4_runner,
            refs[ref_id],
            profile_id=args.profile,
            mix_policy=args.mix_policy,
            render_duration_ms=soak_duration_ms,
            render_root=render_root,
        )
        if args.render_only:
            manifest["results"].append(
                {
                    **render,
                    "capture": None,
                    "hard_failures": [],
                    "passed_runtime_gate": None,
                    "summary_extract": {},
                }
            )
            continue

        rendered_duration_ms = max(1, int(round(float(render["window"]["capture_duration_s"]) * 1000.0)))
        capture_duration_ms = (
            soak_duration_ms if compact_soak else min(soak_duration_ms, rendered_duration_ms)
        )
        capture_label = re.sub(
            r"[^A-Za-z0-9_.-]+",
            "-",
            f"{args.label}_{ref_id}_{capture_duration_ms}ms",
        )
        cmd = build_capture_command(
            capture_script=args.capture_script,
            rendered_wav=Path(render["rendered_wav"]),
            port=args.port,
            duration_ms=capture_duration_ms,
            start_ms=0,
            post_wait_ms=args.post_wait_ms,
            out_dir=captures_dir,
            label=capture_label,
            expected_sample_rate=args.expected_sample_rate,
            expected_samples_per_chunk=args.expected_samples_per_chunk,
            expected_novelty_decimation=args.expected_novelty_decimation,
            player=args.player,
            playback_gain_db=args.playback_gain_db,
            compact_soak=compact_soak,
        )
        print(
            f"[k1-real-corpus] capture {ref_id} mode={'compact_soak' if compact_soak else 'buffered'} "
            f"duration_ms={capture_duration_ms}",
            flush=True,
        )
        try:
            result = subprocess.run(cmd, cwd=ROOT, check=True, capture_output=True, text=True)
            capture_payload, capture_summary = load_capture_summary(result.stdout)
            capture_payload["command"] = cmd
            capture_payload["capture_duration_ms"] = capture_duration_ms
            capture_payload["compact_soak"] = compact_soak
            failures = hard_failures(
                capture_summary,
                args.expected_sample_rate,
                args.expected_samples_per_chunk,
                args.expected_novelty_decimation,
            )
            entry = compact_entry(render, capture_payload, capture_summary, failures)
            entry["capture_mode"] = "compact_soak" if compact_soak else "buffered_apcad"
            manifest["results"].append(entry)
            print(
                f"[k1-real-corpus] capture_done {ref_id} "
                f"failures={','.join(failures) or 'none'}",
                flush=True,
            )
        except (subprocess.CalledProcessError, OSError, json.JSONDecodeError) as exc:
            stdout = exc.stdout if isinstance(exc, subprocess.CalledProcessError) else ""
            stderr = exc.stderr if isinstance(exc, subprocess.CalledProcessError) else ""
            manifest["results"].append(
                {
                    **render,
                    "capture_mode": "compact_soak" if compact_soak else "buffered_apcad",
                    "capture": {"error": str(exc), "command": cmd, "stdout": stdout, "stderr": stderr},
                    "hard_failures": ["capture_command_failed"],
                    "passed_runtime_gate": False,
                    "summary_extract": {},
                }
            )
        if should_stop_after_failures(list(manifest["results"][-1].get("hard_failures") or []), bool(args.continue_on_failure)):
            break

    failures = [entry for entry in manifest["results"] if entry.get("hard_failures")]
    manifest["status"] = "rendered_only" if args.render_only else ("failed" if failures else "passed")
    manifest["failed_references"] = [entry["reference_id"] for entry in failures]
    manifest["summary_json"] = str(out_dir / "k1-real-music-corpus-summary.json")
    manifest["summary_md"] = str(out_dir / "k1-real-music-corpus-summary.md")
    Path(manifest["summary_json"]).write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    write_markdown(manifest, Path(manifest["summary_md"]))
    print(json.dumps({"status": manifest["status"], "summary_json": manifest["summary_json"], "summary_md": manifest["summary_md"]}, indent=2, sort_keys=True))
    return 0 if manifest["status"] in {"passed", "rendered_only"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
