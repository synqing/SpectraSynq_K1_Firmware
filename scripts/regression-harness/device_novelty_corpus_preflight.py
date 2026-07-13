#!/usr/bin/env python3
"""Fail-closed preflight for a ground-truthed device-novelty music corpus.

Catalogue BPM is the ground-truth authority. The decoded-audio autocorrelation
check is deliberately only an identity sanity check: it catches a wrong file,
remix, or grossly incorrect catalogue join without replacing cited GT with an
estimate from the detector under test.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import tempfile
from pathlib import Path

import numpy as np

import novelty_from_wav as novelty


TOLERANCE = 0.04
MIN_DEVICE_DURATION_S = 120.0
EDM_GENRES = ("house", "techno", "edm", "mainstage", "dance")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--out-json", type=Path, required=True)
    parser.add_argument("--analysis-seconds", type=float, default=120.0)
    return parser.parse_args()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def probe_duration(path: Path, ffprobe: str) -> float:
    result = subprocess.run(
        [
            ffprobe,
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            str(path),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    return float(result.stdout.strip())


def local_acf_peaks(values: np.ndarray) -> list[dict[str, float | int]]:
    centred = values - values.mean()
    acf = np.correlate(centred, centred, "full")[len(centred) - 1 :]
    fps = novelty.SAMPLE_RATE / novelty.HOP
    lo = max(2, int(round(fps * 60.0 / 155.0)))
    hi = min(len(acf) - 1, int(round(fps * 60.0 / 60.0)))
    peaks: list[tuple[float, float, int]] = []
    for lag in range(lo + 1, hi):
        if acf[lag] > acf[lag - 1] and acf[lag] >= acf[lag + 1]:
            peaks.append((float(acf[lag]), 60.0 * fps / lag, lag))
    return [
        {"acf": score, "bpm": bpm, "lag": lag}
        for score, bpm, lag in sorted(peaks, reverse=True)[:12]
    ]


def analyse_track(track: dict[str, object], ffmpeg: str, ffprobe: str, seconds: float) -> dict[str, object]:
    path = Path(str(track["track_file"])).expanduser()
    errors: list[str] = []
    if not path.is_absolute():
        errors.append("track_file is not absolute")
    if not path.is_file():
        return {"id": track.get("id"), "track_file": str(path), "verdict": "INVALID", "errors": [*errors, "track file missing"]}

    actual_sha = sha256(path)
    if actual_sha != str(track.get("track_sha256", "")):
        errors.append("SHA-256 mismatch")
    duration_s = probe_duration(path, ffprobe)
    if duration_s < MIN_DEVICE_DURATION_S:
        errors.append(f"duration {duration_s:.3f}s is shorter than the 120s capture contract")

    gt_bpm = float(track["gt_bpm"])
    if not 60.0 <= gt_bpm <= 155.0:
        errors.append(f"GT BPM {gt_bpm:.3f} is outside the detector range")
    gt_source = str(track.get("gt_source", ""))
    if not gt_source.startswith("https://"):
        errors.append("gt_source is not an HTTPS citation")

    peaks: list[dict[str, float | int]] = []
    matching_peak: dict[str, float | int] | None = None
    with tempfile.TemporaryDirectory(prefix="k1-corpus-preflight-") as temporary:
        wav = Path(temporary) / f"{track['id']}.wav"
        subprocess.run(
            [
                ffmpeg,
                "-hide_banner",
                "-loglevel",
                "error",
                "-y",
                "-t",
                f"{min(seconds, duration_s):.3f}",
                "-i",
                str(path),
                "-ac",
                "1",
                "-ar",
                str(novelty.SAMPLE_RATE),
                str(wav),
            ],
            check=True,
        )
        _, curve, _ = novelty.wav_to_novelty(wav)
        peaks = local_acf_peaks(curve)
        candidates = [peak for peak in peaks if abs(float(peak["bpm"]) - gt_bpm) / gt_bpm <= TOLERANCE]
        if candidates:
            matching_peak = max(candidates, key=lambda peak: float(peak["acf"]))
        else:
            errors.append(f"no local novelty ACF peak is within {TOLERANCE:.0%} of cited GT BPM")

    return {
        "id": track["id"],
        "title": track["title"],
        "genre": track["genre"],
        "track_file": str(path),
        "track_sha256": actual_sha,
        "duration_s": duration_s,
        "gt_bpm": gt_bpm,
        "gt_source": gt_source,
        "matching_acf_peak": matching_peak,
        "top_acf_peaks": peaks,
        "verdict": "PASS" if not errors else "INVALID",
        "errors": errors,
    }


def validate_manifest(manifest: dict[str, object]) -> list[str]:
    tracks = manifest.get("tracks")
    if not isinstance(tracks, list) or not tracks:
        return ["manifest has no tracks"]
    errors: list[str] = []
    ids = [str(track.get("id", "")) for track in tracks]
    if len(ids) != len(set(ids)) or any(not track_id for track_id in ids):
        errors.append("track IDs are empty or duplicated")
    critical = [
        track
        for track in tracks
        if 120.0 <= float(track.get("gt_bpm", 0.0)) <= 135.0
        and any(token in str(track.get("genre", "")).lower() for token in EDM_GENRES)
    ]
    if not critical:
        errors.append("no house/techno/EDM track exists in the required 120-135 BPM band")
    return errors


def main() -> int:
    args = parse_args()
    ffmpeg = shutil.which("ffmpeg")
    ffprobe = shutil.which("ffprobe")
    if not ffmpeg or not ffprobe:
        raise RuntimeError("ffmpeg and ffprobe must be installed and on PATH")
    if args.analysis_seconds <= 0.0:
        raise RuntimeError("analysis-seconds must be positive")

    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    errors = validate_manifest(manifest)
    rows = [analyse_track(track, ffmpeg, ffprobe, args.analysis_seconds) for track in manifest.get("tracks", [])]
    errors.extend(f"{row['id']}: {error}" for row in rows for error in row["errors"])
    report = {
        "verdict": "PASS" if not errors else "INVALID",
        "manifest": str(args.manifest.resolve()),
        "method": {
            "gt_authority": "cited catalogue BPM in the manifest",
            "audio_check": "decoded local file novelty has an ACF local maximum within 4% of cited BPM",
            "audio_check_role": "identity sanity check only; not replacement ground truth",
            "analysis_seconds": args.analysis_seconds,
        },
        "required_band": {"genre": "house/techno/EDM", "bpm_min": 120.0, "bpm_max": 135.0},
        "tracks": rows,
        "errors": errors,
    }
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"verdict": report["verdict"], "tracks": len(rows), "out_json": str(args.out_json)}, indent=2))
    return 0 if not errors else 2


if __name__ == "__main__":
    raise SystemExit(main())
