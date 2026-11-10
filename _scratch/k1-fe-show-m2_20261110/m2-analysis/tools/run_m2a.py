#!/usr/bin/env python3
"""M2 lane A: run locked Trinity (e271af39) once on one real recording, retain the result in a keyed cache.

Hop 1 of the K1-FE-SHOW M2 creator loop. Nothing here is home-made analysis: every musical value
comes from Trinity's own analyze_track.py (Beat This! rhythm, Demucs htdemucs stems, allin1-trinity
structure), Trinity's stem_features.write_stem_features (stem_features_v1, 50 fps) and Trinity's
export_contract.export_contract (k1-lite). This script only decodes, keys, times, hashes and publishes.

Usage:  conda-env/bin/python tools/run_m2a.py            (cold or warm; warm must be a cache hit)
Run from anywhere; all paths are absolute. Interpreter must be this lane's conda-env (pytorch-channel torch 2.2.2, natten 0.15.1, one OpenMP runtime).
"""
from __future__ import annotations

import hashlib
import json
import os
import platform
import resource
import shutil
import subprocess
import sys
import time
from pathlib import Path

LANE = Path(__file__).resolve().parents[1]
TRINITY = Path("/Users/spectrasynq/Workspace_Management/Software/Trinity")
TRINITY_ANALYSIS = TRINITY / "analysis"
ALLIN1_SRC = TRINITY_ANALYSIS / "vendor" / "allin1" / "src"
LOCKED_TRINITY_COMMIT = "e271af39229e31c82d387932561ba89a8dd513c5"
ENV_PREFIX = LANE / "conda-env"  # lane-local conda prefix (see M2A-receipt.md, environment section)

ASSET = Path("/Users/spectrasynq/Downloads/Loreen-My-Heart-Is-Refusing-Me.mp3")
ASSET_SHA256 = "a62e1f095de9c3e06563b40d0842acf64ca1bf6fece341a15190cb1c11ab9b0f"
ASSET_LABEL = "repo-approved regression fixture (emulator loreen_src); NOT a Captain show sign-off"
TRACK_ID = "loreen"
EXPECTED_FRAMES = 9_874_432
SR = 44_100
PASSAGE = (75.0, 155.0)  # M1 passage; designated transition at 137.0 s

HUB = Path.home() / ".cache" / "torch" / "hub" / "checkpoints"
HF = Path.home() / ".cache" / "huggingface" / "hub" / "models--taejunkim--allinone" / "snapshots"
MODEL_FILES = {
    "beat_this_final0": HUB / "beat_this-final0.ckpt",
    "demucs_htdemucs_955717e8": HUB / "955717e8-8726e21a.th",
}
ALLIN1_FOLDS = [f"harmonix-fold{i}" for i in range(8)]

DECODE_ARGS = ["-nostdin", "-v", "error", "-i", "{src}", "-map", "0:a:0", "-vn",
               "-acodec", "pcm_s16le", "-ar", str(SR), "-ac", "2", "-f", "wav", "{dst}"]
ANALYZE_ARGS = ["--demix-source", "demucs", "--demucs-model", "htdemucs", "--demucs-shifts", "0",
                "--demucs-overlap", "0.25", "--rhythm-device", "cpu", "--structure-device", "cpu",
                "--model", "harmonix-all", "--keep-byproducts"]
FEATURE_CFG = {"fps": 50, "n_fft": 2048, "low_hz": 250.0, "mid_hz": 4000.0}
EXPORT_TIER = "k1-lite"


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def canon(obj) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"))


def git(*args, cwd=TRINITY) -> str:
    return subprocess.run(["/usr/bin/git", *args], cwd=cwd, capture_output=True, text=True, check=True).stdout.strip()


def pkg_versions() -> dict:
    import importlib.metadata as md
    out = {}
    for name in ["torch", "torchaudio", "numpy", "librosa", "soundfile", "beat_this", "natten", "demucs", "huggingface_hub"]:
        try:
            out[name] = md.version(name)
        except Exception:
            out[name] = None
    return out


def child_env() -> dict:
    env = dict(os.environ)
    env["PYTHONPATH"] = f"{ALLIN1_SRC}:{TRINITY_ANALYSIS}"
    env["HF_HUB_OFFLINE"] = "1"          # use cached allin1 weights only; no network
    env["PYTHONHASHSEED"] = "0"
    return env


def model_hashes() -> dict:
    out = {k: {"path": str(p), "sha256": sha256_file(p), "bytes": p.stat().st_size} for k, p in MODEL_FILES.items()}
    snaps = sorted(HF.iterdir())
    if len(snaps) != 1:
        raise SystemExit(f"expected one allinone snapshot, found {snaps}")
    for fold in ALLIN1_FOLDS:
        p = next(snaps[0].glob(f"{fold}-*.pth")).resolve()
        out[f"allin1_{fold}"] = {"path": str(p), "sha256": sha256_file(p), "bytes": p.stat().st_size}
    return out


def binary_hashes() -> dict:
    sp = Path(sys.prefix) / "lib" / "python3.11" / "site-packages"
    files = {"libtorch_cpu": sp / "torch" / "lib" / "libtorch_cpu.dylib",
             "natten_lib": next((sp / "natten").glob("libnatten*.so")),
             "libomp": Path(sys.prefix) / "lib" / "libomp.dylib"}
    return {k: sha256_file(v) for k, v in files.items()}


def ffmpeg_version() -> str:
    return subprocess.run(["ffmpeg", "-version"], capture_output=True, text=True, check=True).stdout.splitlines()[0]


def main() -> int:
    t_start = time.time()
    if Path(sys.prefix).resolve() != ENV_PREFIX.resolve():
        raise SystemExit(f"run with {ENV_PREFIX}/bin/python (got {sys.prefix})")
    raw = LANE / "raw"
    raw.mkdir(exist_ok=True)

    # ---- identity inputs (always computed; cheap) ----
    src_sha = sha256_file(ASSET)
    if src_sha != ASSET_SHA256:
        raise SystemExit(f"ASSET sha256 mismatch: {src_sha}")
    trinity_head = git("rev-parse", "HEAD")
    trinity_dirty = git("status", "--porcelain")
    models = model_hashes()
    versions = pkg_versions()
    natten_file = __import__("importlib.util").util.find_spec("natten").origin
    key_material = {
        "asset_sha256": src_sha,
        "decoder": {"tool": ffmpeg_version(), "args": DECODE_ARGS},
        "trinity_commit": trinity_head,
        "trinity_worktree_clean": trinity_dirty == "",
        "models": {k: v["sha256"] for k, v in models.items()},
        "packages": versions,
        "binaries": binary_hashes(),
        "analyze_args": ANALYZE_ARGS,
        "stem_feature_cfg": FEATURE_CFG,
        "export_tier": EXPORT_TIER,
    }
    cache_key = hashlib.sha256(canon(key_material).encode()).hexdigest()
    cdir = LANE / "cache" / "trinity" / cache_key
    marker = cdir / "COMPLETE.json"

    run_log = {"started_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(t_start)), "cache_key": cache_key}
    if marker.exists():
        run_log["cache"] = "HIT"
        print(f"cache HIT {cache_key}", file=sys.stderr)
        complete = json.loads(marker.read_text())
        # integrity: every retained artefact must still match its recorded hash
        for rel, h in complete["artefact_sha256"].items():
            if sha256_file(cdir / rel) != h:
                raise SystemExit(f"cache corrupt: {rel}")
        stages = complete["stages"]
    else:
        run_log["cache"] = "MISS"
        print(f"cache MISS {cache_key}; running Trinity", file=sys.stderr)
        if cdir.exists():
            shutil.rmtree(cdir)  # incomplete previous attempt (no marker) is discarded, never reused
        (cdir / "audio").mkdir(parents=True)
        (cdir / "logs").mkdir()
        (cdir / "key.json").write_text(json.dumps(key_material, indent=2, sort_keys=True) + "\n")
        stages = {}

        # Stage 1: decode (no trim, no resample: source is 44.1 kHz; no normalisation)
        track = cdir / "audio" / "track.wav"
        t0 = time.time()
        subprocess.run(["ffmpeg", *[a.format(src=ASSET, dst=track) for a in DECODE_ARGS]], check=True)
        stages["decode_s"] = round(time.time() - t0, 3)

        # Stage 2: Trinity analyze_track.py (Beat This! + Demucs htdemucs + allin1-trinity)
        analysis = cdir / "analysis.json"
        cmd = [sys.executable, str(TRINITY_ANALYSIS / "analyze_track.py"), str(track), "--out", str(analysis),
               "--demix-dir", str(cdir / "demix"), "--spec-dir", str(cdir / "spec"), *ANALYZE_ARGS, "--debug"]
        t0 = time.time()
        with open(cdir / "logs" / "analyze_track.log", "w") as lf:
            lf.write("cmd: " + " ".join(cmd) + "\n")
            lf.flush()
            r = subprocess.run(cmd, cwd=cdir, env=child_env(), stdout=lf, stderr=subprocess.STDOUT)
        stages["analyze_track_s"] = round(time.time() - t0, 3)
        if r.returncode != 0:
            raise SystemExit(f"analyze_track failed rc={r.returncode}; see {cdir/'logs'/'analyze_track.log'}")
        # analyze_track.py main() writes the JSON; check
        if not analysis.exists():
            raise SystemExit("analyze_track produced no analysis.json")

        # Stage 3: Trinity stem_features_v1 + k1-lite contract export (Trinity code, in a child for clean imports)
        stems_dir = cdir / "demix" / "htdemucs" / "track"
        code = (
            "import sys,json;from pathlib import Path;"
            "from stem_features import FeatureConfig, write_stem_features;"
            "from export_contract import export_contract;"
            f"cfg=FeatureConfig(**json.loads({json.dumps(canon(FEATURE_CFG))}));"
            f"write_stem_features(Path({str(stems_dir)!r}), Path({str(cdir/'stem_features.json')!r}), cfg);"
            f"export_contract({str(analysis)!r}, {str(cdir/'contract.json')!r}, tier={EXPORT_TIER!r}, audio_path={str(track)!r})"
        )
        t0 = time.time()
        with open(cdir / "logs" / "features_export.log", "w") as lf:
            r = subprocess.run([sys.executable, "-c", code], cwd=cdir, env=child_env(), stdout=lf, stderr=subprocess.STDOUT)
        stages["stem_features_and_export_s"] = round(time.time() - t0, 3)
        if r.returncode != 0:
            raise SystemExit("stem_features/export failed; see features_export.log")

        # peak RSS of children (macOS reports bytes)
        stages["children_peak_rss_bytes"] = resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss
        rels = ["audio/track.wav", "analysis.json", "stem_features.json", "contract.json",
                *[f"demix/htdemucs/track/{s}.wav" for s in ("vocals", "drums", "bass", "other")]]
        complete = {
            "cache_key": cache_key,
            "stages": stages,
            "artefact_sha256": {rel: sha256_file(cdir / rel) for rel in rels},
            "disk_bytes": sum(p.stat().st_size for p in cdir.rglob("*") if p.is_file()),
            "completed_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        }
        tmp = cdir / "COMPLETE.json.tmp"
        tmp.write_text(json.dumps(complete, indent=2, sort_keys=True) + "\n")
        os.replace(tmp, marker)  # atomic publication: the marker is the only "done" signal

    # ---- publish views (deterministic functions of the cache) ----
    out = LANE / "out" / TRACK_ID
    out.mkdir(parents=True, exist_ok=True)
    for name in ("contract.json", "stem_features.json", "analysis.json"):
        shutil.copyfile(cdir / name, out / name)

    import soundfile as sf
    info = sf.info(str(cdir / "audio" / "track.wav"))
    contract = json.loads((cdir / "contract.json").read_text())
    feats = json.loads((cdir / "stem_features.json").read_text())

    identity = {
        "schema": "m2a-identity/0",
        "label": ASSET_LABEL,
        "source": {"path": str(ASSET), "sha256": src_sha, "container": "mp3", "bytes": ASSET.stat().st_size},
        "decode": {
            "tool": key_material["decoder"]["tool"],
            "command": ["ffmpeg", *DECODE_ARGS],
            "output": "cache audio/track.wav (contract track.path)",
            "output_sha256": complete["artefact_sha256"]["audio/track.wav"],
            "sample_rate": info.samplerate, "frames": info.frames, "channels": info.channels,
            "subtype": info.subtype,
            "expected_frames_from_brief": EXPECTED_FRAMES,
            "frame_delta_vs_brief": info.frames - EXPECTED_FRAMES,
            "resample": "none (source 44100 Hz)",
            "trim_pad": "none requested; ffmpeg mp3 decoder applies the file's own encoder-delay/padding (gapless) info if present; frame_delta_vs_brief records the net effect",
            "normalisation": "none",
            "quantisation": "decoder float -> PCM s16 (Trinity README's documented WAV conversion), no dither",
            "sample_axis": "asset sample n at 44100 Hz, n=0 is first sample of track.wav; seconds = n/44100 (B5 rule)",
        },
        "trinity": {
            "checkout": str(TRINITY), "head": trinity_head, "locked": LOCKED_TRINITY_COMMIT,
            "matches_lock": trinity_head == LOCKED_TRINITY_COMMIT, "worktree_clean": trinity_dirty == "",
            "allin1_import_root": str(ALLIN1_SRC),
        },
        "runtime": {
            "python": sys.version.split()[0], "interpreter": sys.executable,
            "env_prefix": str(ENV_PREFIX),
            "env_recipe": "conda create --clone ~/miniforge3/envs/trinity-music-intent-v0_1; pip leftovers removed; "
                          "pytorch=2.2.2=py3.11_0 + torchaudio=2.2.2=py311_cpu force-reinstalled from the pytorch channel "
                          "(no bundled OpenMP); natten 0.21.7 removed, natten 0.15.1 built from source + Trinity patch_natten_cpu.py; "
                          "allin1 imported from the locked checkout via PYTHONPATH (base env's editable install points at an old tree)",
            "natten_path": natten_file,
            "binaries": key_material["binaries"],
            "openmp_runtimes_loaded": "one (conda-env/lib/libomp.dylib), see raw/env_openmp_check.log",
            "packages": versions, "platform": platform.platform(), "machine": platform.machine(),
            "HF_HUB_OFFLINE": "1",
        },
        "analysers": {
            "rhythm": "Beat This! final0, dbn=False (minimal postprocessing), device cpu (torch 2.2.2 MPS lacks aten::_fft_r2c)",
            "separation": "Demucs htdemucs (955717e8), overlap 0.25, int16 WAV, demucs default clip-mode rescale. NOTE: --demucs-shifts 0 is DROPPED by Trinity analyze_track.py:312 (flag only passed when >0), so Demucs runs its default shifts=1 = one unseeded random time offset of 0-0.5 s (demucs/apply.py:214). Stems and every stem feature therefore differ between cold runs (raw/cold_vs_cold_stems.log); the retained cache is the only reproducible copy.",
            "structure": "allin1-trinity harmonix-all (8-fold ensemble), device cpu",
            "stem_features": f"Trinity stem_features_v1 {FEATURE_CFG}",
            "contract": f"Trinity export_contract tier {EXPORT_TIER}",
            "models": models,
        },
        "parameters": {"analyze_track": ANALYZE_ARGS, "stem_features": FEATURE_CFG, "export_tier": EXPORT_TIER},
        "cache": {"key": cache_key, "key_material_file": f"cache/trinity/{cache_key}/key.json", "dir": str(cdir)},
        "timing": {
            "stages_s": dict(sorted(stages.items())),
            "cold_total_s": round(sum(v for k, v in stages.items() if k.endswith("_s")), 3),
            "audio_duration_s": info.frames / info.samplerate,
            "real_time_factor_cold": round(sum(v for k, v in stages.items() if k.endswith("_s")) / (info.frames / info.samplerate), 4),
            "A13_cap": "<= 2.0 x real time",
            "disk_bytes": complete["disk_bytes"],
        },
        "contract_summary": {
            "duration_sec": contract["track"]["duration_sec"], "bpm": contract["rhythm"]["bpm"],
            "beats": len(contract["rhythm"]["beats"]), "downbeats": len(contract["rhythm"]["downbeats"]),
            "segments": [(s["start"], s["end"], s["label"]) for s in contract["structure"]["segments"]],
            "stem_feature_frames": {k: len(v["rms"]) for k, v in feats["stems"].items()},
        },
    }
    (out / "identity.json").write_text(json.dumps(identity, indent=2) + "\n")

    run_log["finished_utc"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    run_log["wall_s"] = round(time.time() - t_start, 3)
    run_log["published_sha256"] = {p.name: sha256_file(p) for p in sorted(out.glob("*.json"))}
    stamp = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime(t_start))
    (raw / f"run_{stamp}_{run_log['cache']}.json").write_text(json.dumps(run_log, indent=2) + "\n")
    print(json.dumps(run_log, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
