#!/usr/bin/env python3
"""TRINITY-FIX: one cold Trinity analysis of the Loreen track (or an excerpt), from source.

Every stage is Trinity's own code on branch fix/reproducible-contract:
  decode (ffmpeg, same arguments as M2A) -> analyze_track.py (Demucs htdemucs, shifts 0
  explicit, seed 0; Beat This! final0 CPU; allin1 harmonix-all CPU) -> stem_features
  (50 fps) -> export_contract (k1-lite).
Nothing is cached or reused: the work directory is created empty, and on success it is
moved to runs/<view>_<label>/. All runs execute in the same work path, so absolute paths
written into analysis.json/contract.json are identical across runs.

Usage: <env>/bin/python run_cold.py <full|excerpt> <label>
"""
from __future__ import annotations

import hashlib
import json
import os
import resource
import shutil
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
TRINITY = Path("/Users/spectrasynq/Workspace_Management/Software/Trinity")
ANALYSIS = TRINITY / "analysis"
ASSET = Path("/Users/spectrasynq/Downloads/Loreen-My-Heart-Is-Refusing-Me.mp3")
ASSET_SHA256 = "a62e1f095de9c3e06563b40d0842acf64ca1bf6fece341a15190cb1c11ab9b0f"
M2A_DECODE_SHA256 = None  # filled from the M2A cache COMPLETE.json at run time (read-only)
M2A_CACHE = Path("/Users/spectrasynq/SpectraSynq_K1_Firmware/_scratch/k1-fe-show-m2_20261110/m2-analysis/cache/trinity/"
                 "9876b2538cfc5697c89fa6e8043a70f9caf94f0c21d7509e4af80778c70311ca")
FFMPEG = "/opt/homebrew/bin/ffmpeg"
SR = 44100
EXCERPT_SEC = 45.0  # 0-45 s: the unsteady intro (0-30 s) plus the first steady verse
DECODE_ARGS = ["-nostdin", "-v", "error", "-i", "{src}", "-map", "0:a:0", "-vn",
               "-acodec", "pcm_s16le", "-ar", str(SR), "-ac", "2", "-f", "wav", "{dst}"]
ANALYZE_ARGS = ["--demix-source", "demucs", "--demucs-model", "htdemucs", "--demucs-shifts", "0",
                "--demucs-seed", "0", "--demucs-overlap", "0.25", "--rhythm-device", "cpu",
                "--structure-device", "cpu", "--model", "harmonix-all", "--keep-byproducts"]
FEATURE_CFG = {"fps": 50, "n_fft": 2048, "low_hz": 250.0, "mid_hz": 4000.0}
STEMS = ("vocals", "drums", "bass", "other")


def sha(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def git(*a: str) -> str:
    return subprocess.run(["/usr/bin/git", "-C", str(TRINITY), *a], capture_output=True, text=True, check=True).stdout.strip()


def main() -> int:
    view, label = sys.argv[1], sys.argv[2]
    assert view in ("full", "excerpt")
    if sha(ASSET) != ASSET_SHA256:
        raise SystemExit("asset sha256 mismatch")
    work = HERE / "work" / view
    dest = HERE / "runs" / f"{view}_{label}"
    if dest.exists():
        raise SystemExit(f"{dest} exists; labels are single-use")
    if work.exists():
        shutil.rmtree(work)  # never reuse anything from an earlier attempt
    (work / "audio").mkdir(parents=True)
    env = dict(os.environ, PYTHONPATH=f"{ANALYSIS / 'vendor' / 'allin1' / 'src'}:{ANALYSIS}",
               HF_HUB_OFFLINE="1", PYTHONHASHSEED="0")
    rec = {"view": view, "label": label, "python": sys.executable, "trinity_head": git("rev-parse", "HEAD"),
           "trinity_status_porcelain": git("status", "--porcelain"), "started_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
           "analyze_args": ANALYZE_ARGS, "feature_cfg": FEATURE_CFG, "stages": {}}
    t_all = time.time()

    # 1. decode (cold, every run)
    full = work / "audio" / "full.wav"
    t0 = time.time()
    subprocess.run([FFMPEG, *[a.format(src=ASSET, dst=full) for a in DECODE_ARGS]], check=True)
    rec["decode_sha256"] = sha(full)
    m2a = json.loads((M2A_CACHE / "COMPLETE.json").read_text())["artefact_sha256"]["audio/track.wav"]
    rec["decode_matches_m2a"] = rec["decode_sha256"] == m2a
    track = work / "audio" / "track.wav"
    if view == "full":
        full.rename(track)
    else:
        import soundfile as sf
        data, sr = sf.read(str(full), frames=int(EXCERPT_SEC * SR), dtype="int16", always_2d=True)
        sf.write(str(track), data, sr, subtype="PCM_16")
        full.unlink()
    rec["track_sha256"] = sha(track)
    rec["stages"]["decode_s"] = round(time.time() - t0, 3)

    # 2. analyze_track.py
    t0 = time.time()
    cmd = [sys.executable, str(ANALYSIS / "analyze_track.py"), str(track), "--out", str(work / "analysis.json"),
           "--demix-dir", str(work / "demix"), "--spec-dir", str(work / "spec"), *ANALYZE_ARGS, "--debug"]
    rec["analyze_cmd"] = cmd
    with open(work / "analyze_track.log", "w") as lf:
        r = subprocess.run(cmd, cwd=work, env=env, stdout=lf, stderr=subprocess.STDOUT)
    rec["stages"]["analyze_track_s"] = round(time.time() - t0, 3)
    if r.returncode != 0:
        raise SystemExit(f"analyze_track rc={r.returncode}; see {work / 'analyze_track.log'}")

    # 3. stem features + contract export
    t0 = time.time()
    stems_dir = work / "demix" / "htdemucs" / "track"
    code = ("import json;from pathlib import Path;from stem_features import FeatureConfig, write_stem_features;"
            "from export_contract import export_contract;"
            f"write_stem_features(Path({str(stems_dir)!r}), Path({str(work / 'stem_features.json')!r}), FeatureConfig(**{FEATURE_CFG!r}));"
            f"export_contract({str(work / 'analysis.json')!r}, {str(work / 'contract.json')!r}, tier='k1-lite', audio_path={str(track)!r})")
    with open(work / "features_export.log", "w") as lf:
        r = subprocess.run([sys.executable, "-c", code], cwd=work, env=env, stdout=lf, stderr=subprocess.STDOUT)
    rec["stages"]["features_export_s"] = round(time.time() - t0, 3)
    if r.returncode != 0:
        raise SystemExit(f"features/export rc={r.returncode}; see {work / 'features_export.log'}")

    rec["stages"]["total_s"] = round(time.time() - t_all, 3)
    rec["children_peak_rss_bytes"] = resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss
    rels = ["audio/track.wav", "analysis.json", "stem_features.json", "contract.json",
            *[f"demix/htdemucs/track/{s}.wav" for s in STEMS]]
    rec["sha256"] = {rel: sha(work / rel) for rel in rels}
    rec["completed_utc"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    (work / "run.json").write_text(json.dumps(rec, indent=2) + "\n")
    dest.parent.mkdir(exist_ok=True)
    shutil.move(str(work), str(dest))
    print(json.dumps({k: rec[k] for k in ("view", "label", "trinity_head", "decode_matches_m2a", "stages", "sha256")}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
