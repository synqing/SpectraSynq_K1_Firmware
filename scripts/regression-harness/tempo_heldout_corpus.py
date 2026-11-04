#!/usr/bin/env python3
"""Held-out tempo corpus loader — K1 TEMPO LOCK R1, Phase 0.4.

Builds a held-out tempo-estimation evaluation corpus from two public datasets:
  - Ballroom (ISMIR 2004 contest, Gouyon et al.): 698 x ~30 s clips, BPM-annotated.
  - GiantSteps Tempo (Knees et al. ISMIR'15; corrected tempo per Schreiber & Mueller
    ISMIR'18 "annotations_v2"): 664 EDM clips.

This script does NOT run any tempo tracker, emulator, or firmware build. It only
downloads/locates source audio, decodes 30 s excerpts to PCM, and records rows +
hashes for later (separate) evaluation. See PROVENANCE.md in the same directory
as the rows file for exact URLs, retrieval times, checksums and licence notes.

Decode rule mirrors tools/esp_emulator/run.py:load_asset's "inventory_excerpt"
branch EXACTLY (reference-only; read, not modified):
    ffmpeg -nostdin -v error [-ss start -t dur] -i SRC -map 0:a:0 -ac 1 -ar 12800
           -af anull -f s16le -acodec pcm_s16le
    (ffmpeg default resampler = swr, NOT soxr, matching s3_music_regression.json's
    "loreen_src" asset: conversion.resampler == "ffmpeg default (swr)")
    then ONE uniform gain so the excerpt's peak |sample| == 4096 (-18 dBFS):
        gain = 4096 / peak  (or 1.0 if peak == 0)
        sample' = clamp(round(sample * gain), -32768, 32767)
    using Python's built-in round() (round-half-to-even), exactly as run.py does.

Subcommands:
  prepare                 Build rows from the raw downloads under raw/.
  decode <row-id>          Decode one row and print its peak/gain/sha256.
  verify --rows PATH       Re-hash every source file and every decoded PCM
                           against a rows file. Exit 0 only if ALL match; exit
                           non-zero and print the first mismatching row id otherwise.
"""
from __future__ import annotations

import argparse
import array
import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

# --------------------------------------------------------------------------
# Constants mirrored from tools/esp_emulator/run.py + s3_music_regression.json
# --------------------------------------------------------------------------
RATE_HZ = 12800
GAIN_TARGET_PEAK = 4096
FOLD_LO = 60.0
FOLD_HI = 155.0

HERE = Path(__file__).resolve()
REPO = HERE.parents[2]  # scripts/regression-harness/<this file> -> repo root
HELDOUT_DIR = REPO / "_scratch/esp-emulator/tempo-lock-r1/heldout"
RAW_DIR = HELDOUT_DIR / "raw"
DEFAULT_ROWS = HELDOUT_DIR / "heldout_rows.json"
DEFAULT_EXCLUDED = HELDOUT_DIR / "excluded.json"


# --------------------------------------------------------------------------
# Hashing helpers
# --------------------------------------------------------------------------
def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


# --------------------------------------------------------------------------
# Octave folding
# --------------------------------------------------------------------------
def fold_bpm(bpm: float) -> float:
    """Fold by octave (x2 / x0.5 repeatedly) into [FOLD_LO, FOLD_HI].

    Multiplying/dividing an IEEE-754 double by exactly 2 is exact (no rounding
    error), so this never perturbs the mantissa of the original annotation.
    """
    if bpm <= 0:
        return bpm
    v = float(bpm)
    while v < FOLD_LO:
        v *= 2.0
    while v > FOLD_HI:
        v /= 2.0
    return v


# --------------------------------------------------------------------------
# ffprobe / ffmpeg
# --------------------------------------------------------------------------
def ffprobe_duration_ms(path: Path) -> int:
    ffprobe = shutil.which("ffprobe")
    if ffprobe is None:
        raise FileNotFoundError("ffprobe is not on PATH")
    out = subprocess.run(
        [ffprobe, "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", str(path)],
        check=True, capture_output=True, text=True,
    ).stdout.strip()
    return int(round(float(out) * 1000))


def decode_row(row: dict) -> tuple[bytes, dict]:
    """Decode row['path'] per row['excerpt'] into mono 12800 Hz s16le PCM.

    Mirrors run.py:load_asset's inventory_excerpt branch exactly (see module
    docstring). Returns (pcm_bytes, meta) where meta carries decoded_peak,
    applied_gain, pcm_sha256, samples and the exact ffmpeg argv used.
    """
    ffmpeg = shutil.which("ffmpeg")
    if ffmpeg is None:
        raise FileNotFoundError("ffmpeg is not on PATH")
    src = Path(row["path"])
    if not src.is_file():
        raise FileNotFoundError(f"row {row.get('id')}: source {src} is not accessible")
    ex = row["excerpt"]
    with tempfile.TemporaryDirectory() as td:
        raw = Path(td) / "raw.s16le"
        cmd = [ffmpeg, "-nostdin", "-v", "error",
               "-ss", f"{ex['start_ms'] / 1000:.3f}",
               "-t", f"{ex['duration_ms'] / 1000:.3f}",
               "-i", str(src), "-map", "0:a:0", "-ac", "1", "-ar", str(RATE_HZ),
               "-af", "anull", "-f", "s16le", "-acodec", "pcm_s16le", str(raw)]
        subprocess.run(cmd, check=True)
        samples = array.array("h")
        samples.frombytes(raw.read_bytes())
    peak = max((abs(s) for s in samples), default=0)
    gain = (GAIN_TARGET_PEAK / peak) if peak else 1.0
    scaled = array.array("h", (max(-32768, min(32767, int(round(s * gain)))) for s in samples))
    pcm = scaled.tobytes()
    meta = {
        "decoded_peak": peak,
        "applied_gain": gain,
        "pcm_sha256": sha256_bytes(pcm),
        "samples": len(pcm) // 2,
        "argv": cmd[1:],
    }
    return pcm, meta


# --------------------------------------------------------------------------
# prepare: build rows from raw downloads
# --------------------------------------------------------------------------
def _find_ballroom_audio_root(raw_dir: Path) -> Path:
    ballroom_dir = raw_dir / "ballroom"
    hits = list(ballroom_dir.glob("BallroomData")) + list(ballroom_dir.rglob("BallroomData"))
    if not hits:
        raise FileNotFoundError(
            f"BallroomData not found under {ballroom_dir}; extract data1_full.tar.gz first"
        )
    return hits[0]


def prepare_ballroom(raw_dir: Path) -> tuple[list[dict], list[dict]]:
    rows: list[dict] = []
    excluded: list[dict] = []
    audio_root = _find_ballroom_audio_root(raw_dir)
    gt_dir = raw_dir / "ballroom/data2_extracted/BallroomAnnotations/ballroomGroundTruth"
    if not gt_dir.is_dir():
        raise FileNotFoundError(f"ballroomGroundTruth not found under {gt_dir}; extract data2_full.tar.gz first")
    audio_by_stem = {p.stem: p for p in audio_root.rglob("*.wav")}
    for bpm_file in sorted(gt_dir.glob("*.bpm")):
        stem = bpm_file.stem
        row_id = f"ballroom:{stem}"
        audio_path = audio_by_stem.get(stem)
        if audio_path is None:
            excluded.append({"id": row_id, "reason": "no matching audio file in BallroomData"})
            continue
        raw_bpm = float(bpm_file.read_text().strip())
        if raw_bpm <= 0:
            excluded.append({"id": row_id, "reason": "non-positive/missing tempo annotation"})
            continue
        folded = fold_bpm(raw_bpm)
        if not (FOLD_LO <= folded <= FOLD_HI):
            excluded.append({"id": row_id, "reason": f"folded gold {folded} still outside [{FOLD_LO},{FOLD_HI}]"})
            continue
        dur_ms = ffprobe_duration_ms(audio_path)
        row = {
            "id": row_id,
            "path": str(audio_path.resolve()),
            "sha256": sha256_file(audio_path),
            "gold_bpm": folded,
            "gold_bpm_raw": raw_bpm,
            "role": "heldout",
            "source": ("Ballroom ISMIR2004 contest (Gouyon et al.), audio data1.tar.gz + tempo "
                       "ground truth data2.tar.gz, https://mtg.upf.edu/ismir2004/contest/tempoContest/ "
                       "(md5 verified against mir-dataset-loaders/mirdata REMOTES)"),
            "excerpt": {"start_ms": 0, "duration_ms": dur_ms},
            "genre": audio_path.parent.name,
        }
        _, meta = decode_row(row)
        row["pcm_sha256"] = meta["pcm_sha256"]
        row["decode"] = {"decoded_peak": meta["decoded_peak"], "applied_gain": meta["applied_gain"]}
        rows.append(row)
    return rows, excluded


def prepare_giantsteps(raw_dir: Path) -> tuple[list[dict], list[dict]]:
    rows: list[dict] = []
    excluded: list[dict] = []
    gs_dir = raw_dir / "giantsteps"
    repo_dir = gs_dir / "repo"
    audio_dir = gs_dir / "audio"
    tempo_dir = repo_dir / "annotations_v2/tempo"
    genre_dir = repo_dir / "annotations/genre"
    if not tempo_dir.is_dir():
        raise FileNotFoundError(f"annotations_v2/tempo not found under {tempo_dir}; clone giantsteps-tempo-dataset first")
    for bpm_file in sorted(tempo_dir.glob("*.bpm")):
        stem = bpm_file.stem  # e.g. 1030011.LOFI
        row_id = f"giantsteps:{stem}"
        audio_path = audio_dir / f"{stem}.mp3"
        raw_bpm = float(bpm_file.read_text().strip())
        if not audio_path.is_file():
            excluded.append({"id": row_id, "reason": "audio file not downloaded"})
            continue
        if raw_bpm <= 0:
            excluded.append({"id": row_id, "reason": "annotations_v2 tempo is 0.0 (no annotation, per repo README)"})
            continue
        folded = fold_bpm(raw_bpm)
        if not (FOLD_LO <= folded <= FOLD_HI):
            excluded.append({"id": row_id, "reason": f"folded gold {folded} still outside [{FOLD_LO},{FOLD_HI}]"})
            continue
        dur_ms = ffprobe_duration_ms(audio_path)
        if dur_ms < 60000:
            start_ms, duration_ms = 0, min(30000, dur_ms)
        else:
            start_ms, duration_ms = 30000, 30000
        genre_file = genre_dir / f"{stem}.genre"
        genre = genre_file.read_text().strip() if genre_file.is_file() else None
        row = {
            "id": row_id,
            "path": str(audio_path.resolve()),
            "sha256": sha256_file(audio_path),
            "gold_bpm": folded,
            "gold_bpm_raw": raw_bpm,
            "role": "heldout",
            "source": ("GiantSteps Tempo dataset (Knees et al. ISMIR'15), annotations_v2 tempo "
                       "= Schreiber & Mueller ISMIR'18 corrected annotation; audio previews via "
                       "https://www.cp.jku.at/datasets/giantsteps/backup/ (md5 verified against repo md5/)"),
            "excerpt": {"start_ms": start_ms, "duration_ms": duration_ms},
            "genre": genre,
        }
        _, meta = decode_row(row)
        row["pcm_sha256"] = meta["pcm_sha256"]
        row["decode"] = {"decoded_peak": meta["decoded_peak"], "applied_gain": meta["applied_gain"]}
        rows.append(row)
    return rows, excluded


def cmd_prepare(args: argparse.Namespace) -> int:
    raw_dir = Path(args.raw_dir)
    rows_b, excl_b = prepare_ballroom(raw_dir)
    rows_g, excl_g = prepare_giantsteps(raw_dir)
    rows = rows_b + rows_g
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(rows, indent=2) + "\n")
    excl_path = Path(args.excluded_out)
    excl_path.write_text(json.dumps(excl_b + excl_g, indent=2) + "\n")
    print(f"ballroom:   rows={len(rows_b)} excluded={len(excl_b)}")
    print(f"giantsteps: rows={len(rows_g)} excluded={len(excl_g)}")
    print(f"total rows={len(rows)} -> {out_path}")
    print(f"excluded -> {excl_path}")
    return 0


# --------------------------------------------------------------------------
# decode / verify
# --------------------------------------------------------------------------
def _load_rows(rows_path: Path) -> list[dict]:
    return json.loads(rows_path.read_text())


def cmd_decode(args: argparse.Namespace) -> int:
    rows = _load_rows(Path(args.rows))
    row = next((r for r in rows if r["id"] == args.row_id), None)
    if row is None:
        print(f"row id not found: {args.row_id}", file=sys.stderr)
        return 2
    _, meta = decode_row(row)
    print(json.dumps({"id": row["id"], **meta}, indent=2))
    return 0


def cmd_verify(args: argparse.Namespace) -> int:
    rows_path = Path(args.rows)
    rows = _load_rows(rows_path)
    if not rows:
        print("MISMATCH <none>: rows file is empty")
        return 1
    for row in rows:
        rid = row.get("id", "<unknown>")
        src = Path(row["path"])
        if not src.is_file():
            print(f"MISMATCH {rid}: source file missing: {src}")
            return 1
        actual_src_sha = sha256_file(src)
        if actual_src_sha != row["sha256"]:
            print(f"MISMATCH {rid}: source sha256 {actual_src_sha} != recorded {row['sha256']}")
            return 1
        try:
            _, meta = decode_row(row)
        except subprocess.CalledProcessError as exc:
            print(f"MISMATCH {rid}: decode failed: {exc}")
            return 1
        if meta["pcm_sha256"] != row["pcm_sha256"]:
            print(f"MISMATCH {rid}: pcm sha256 {meta['pcm_sha256']} != recorded {row['pcm_sha256']}")
            return 1
        if meta["decoded_peak"] != row["decode"]["decoded_peak"]:
            print(f"MISMATCH {rid}: decoded_peak {meta['decoded_peak']} != recorded {row['decode']['decoded_peak']}")
            return 1
    print(f"OK: {len(rows)} rows verified against {rows_path}")
    return 0


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------
def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="command", required=True)

    p_prepare = sub.add_parser("prepare", help="build rows from raw downloads")
    p_prepare.add_argument("--raw-dir", default=str(RAW_DIR))
    p_prepare.add_argument("--out", default=str(DEFAULT_ROWS))
    p_prepare.add_argument("--excluded-out", default=str(DEFAULT_EXCLUDED))
    p_prepare.set_defaults(func=cmd_prepare)

    p_decode = sub.add_parser("decode", help="decode a single row and print its metadata")
    p_decode.add_argument("row_id")
    p_decode.add_argument("--rows", default=str(DEFAULT_ROWS))
    p_decode.set_defaults(func=cmd_decode)

    p_verify = sub.add_parser("verify", help="re-hash every source + decoded PCM against a rows file")
    p_verify.add_argument("--rows", default=str(DEFAULT_ROWS))
    p_verify.set_defaults(func=cmd_verify)

    args = p.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
