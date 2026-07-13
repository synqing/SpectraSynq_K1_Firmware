import hashlib
import json
import math
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / "scripts/regression-harness/device_novelty_corpus_run.py"
BASELINE = ROOT / "docs/measurements/tempo-octave-baseline.tracks.csv"


def test_resumed_capture_replays_scores_and_embeds_exact_command(tmp_path):
    captures = tmp_path / "captures"
    captures.mkdir()
    audio = tmp_path / "fixture.mp3"
    audio.write_bytes(b"k1 dry-run immutable audio fixture")
    track_sha = hashlib.sha256(audio.read_bytes()).hexdigest()
    track = {
        "id": "synthetic-128",
        "title": "Synthetic 128",
        "genre": "Techno",
        "gt_bpm": 128.0,
        "gt_source": "https://example.test/gt",
        "track_file": str(audio),
        "track_sha256": track_sha,
    }
    manifest = tmp_path / "manifest.json"
    manifest.write_text(json.dumps({"corpus_id": "dry-run", "tracks": [track]}))
    preflight = tmp_path / "preflight.json"
    preflight.write_text(
        json.dumps(
            {
                "verdict": "PASS",
                "manifest": str(manifest.resolve()),
                "manifest_sha256": hashlib.sha256(manifest.read_bytes()).hexdigest(),
                "tracks": [{"id": track["id"], "verdict": "PASS", "track_sha256": track_sha}],
            }
        )
    )

    novelty = captures / "synthetic-128_nov_buffered_20260714__nov_dump.log"
    count = 5333
    rows = [f"NOV_CAPTURE_BEGIN,count={count},capacity=6144,dropped=0,start_ms=0,end_ms=120000"]
    for index in range(count):
        timestamp = round(index * 22.5)
        phase = (timestamp / 1000.0) * (128.0 / 60.0)
        value = max(0.0, math.cos(2.0 * math.pi * phase))
        rows.append(f"NOV,t={timestamp},emit={index},nov={value:.6f},src=buf")
    rows.append(f"NOV_CAPTURE_DONE,count={count},dropped=0")
    novelty.write_text("\n".join(rows) + "\n")

    trajectory = captures / "trajectory.log"
    summary = captures / "synthetic-128_nov_buffered_20260714__summary.json"
    summary.write_text(
        json.dumps(
            {
                "validation": {"verdict": "PASS"},
                "track_sha256": track_sha,
                "expected_chip_id": "B489A500",
                "expected_build_env": "k1_bench_ap_frontend_probe",
                "port": "/dev/cu.usbmodem1401",
                "duration_ms_requested": 120000,
                "nov_dump_log": str(novelty),
                "replay_summary": str(captures / "replay.json"),
                "trajectory": str(trajectory),
                "replay_input": str(captures / "input.txt"),
            }
        )
    )
    result_json = tmp_path / "result.json"
    result_md = tmp_path / "result.md"
    commands = tmp_path / "commands.json"
    command = [
        sys.executable,
        str(RUNNER),
        str(manifest),
        "--preflight-report",
        str(preflight),
        "--port",
        "/dev/cu.usbmodem1401",
        "--expected-chip-id",
        "B489A500",
        "--expected-build-env",
        "k1_bench_ap_frontend_probe",
        "--duration-ms",
        "120000",
        "--out-dir",
        str(captures),
        "--score-manifest",
        str(tmp_path / "score-manifest.json"),
        "--commands-out",
        str(commands),
        "--out-json",
        str(result_json),
        "--out-md",
        str(result_md),
        "--baseline-csv",
        str(BASELINE),
        "--resume",
    ]
    subprocess.run(command, cwd=ROOT, check=True, capture_output=True, text=True)

    result = json.loads(result_json.read_text())
    ledger = json.loads(commands.read_text())
    markdown = result_md.read_text()
    assert result["verdict"] == "MEASURED"
    assert len(result["tracks"]) == 1
    assert result["tracks"][0]["det_bpm"] == 128.0
    assert ledger["verdict"] == "COMPLETE"
    assert result["rerun_command"]
    assert "## Exact Re-run" in markdown
    assert "/dev/cu.usbmodem1401" in markdown
