#!/usr/bin/env python3
"""Lane 2: model a 32 kHz in-spec BCLK migration preserving 133 Hz AP frames.

Read-only planner — prints JSON migration model. No firmware edits.
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

CURRENT_SR = 12800
CURRENT_CHUNK = 96
TARGET_SR = 32000
AP_FRAME_HZ = CURRENT_SR / CURRENT_CHUNK  # 133.333...
NOVELTY_DECIMATION = 3
NYQUIST_CURRENT = CURRENT_SR / 2
NYQUIST_TARGET = TARGET_SR / 2

# SPH0645 BCLK: stereo 32-bit slot -> 64 bits per frame
BCLK_CURRENT = CURRENT_SR * 64
BCLK_TARGET = TARGET_SR * 64
BCLK_SPEC_MIN = 2_048_000

NOTES_TOP_BIN_79_HZ = 10548.08  # notes[91] with NOTE_OFFSET=12


def goertzel_block_size(sr: float, neighbour_hz: float) -> int:
    bs = int(sr / (neighbour_hz * 2.0))
    return min(bs, 2000)


def migration_model() -> dict:
    # Preserve 133.333 Hz AP: chunk = round(sr / ap_hz)
    target_chunk = round(TARGET_SR / AP_FRAME_HZ)
    actual_ap_hz = TARGET_SR / target_chunk
    novelty_hz = actual_ap_hz / NOVELTY_DECIMATION

    # Example semitone neighbour spacing mid-range ~15 Hz at 110 Hz bin
    block_12800 = goertzel_block_size(CURRENT_SR, 15.0)
    block_32000 = goertzel_block_size(TARGET_SR, 15.0)

    # Inner loop cost scales ~ NUM_FREQS * avg_block; avg_block scales ~ sr
    gdft_scale = TARGET_SR / CURRENT_SR

    dma_bytes_per_read = target_chunk * 4  # int32 stereo slot mono read

    touch_list = [
        "platformio.ini — DEFAULT_SAMPLE_RATE, DEFAULT_SAMPLES_PER_CHUNK, probe matrix envs",
        "SPECTRASYNQ_K1_FIRMWARE/system/config_types.h — DEFAULT_SAMPLE_RATE / CHUNK defaults",
        "SPECTRASYNQ_K1_FIRMWARE/system/system.h — precompute_goertzel_constants(), enforce_compiled_audio_timing_config()",
        "SPECTRASYNQ_K1_FIRMWARE/audio/i2s_audio.h — I2S_STD_CLK_DEFAULT_CONFIG(CONFIG.SAMPLE_RATE); verify slot_cfg unchanged",
        "SPECTRASYNQ_K1_FIRMWARE/audio/sb_tempo.cpp — SB_TEMPO_AP_FRAME_HZ must match TARGET_SR/CHUNK",
        "SPECTRASYNQ_K1_FIRMWARE/audio/sb_onset_beat.cpp — dt comments + refractory frame counts (optional retune)",
        "SPECTRASYNQ_K1_FIRMWARE/serial/serial_menu.h — sample_rate constrain min (currently 6400)",
        "scripts/regression-harness/novelty_from_wav.py — SAMPLE_RATE, re-decode entire HarmonixSet corpus",
        "scripts/regression-harness/tempo_accuracy.py — corpus path / resample policy",
        "scripts/regression-harness/* — all modules hardcoding 12800/96",
        "tests/test_rate_consistency.py, tests/test_semantic_state_replay.py — timing assertions",
        "docs/config-snapshots/* — persisted CONFIG defaults",
        "Lightwave-Ledstrip/.../audio_12k8 — new audio_32k corpus OR resample pipeline",
    ]

    risks = [
        {
            "id": "R1",
            "severity": "high",
            "title": "Full host corpus invalidation",
            "detail": "36 HarmonixSet WAVs + all replay tests assume 12.8 kHz. Must resample corpus and re-baseline tempo/onset metrics.",
        },
        {
            "id": "R2",
            "severity": "high",
            "title": "Goertzel block_size grows with SR",
            "detail": f"Mid-bin block_size ~{block_12800} -> ~{block_32000} samples (~{gdft_scale:.2f}x). Still under 2000 cap but CPU ~{gdft_scale:.2f}x per bin worst-case.",
        },
        {
            "id": "R3",
            "severity": "medium",
            "title": "sample_window shift cost",
            "detail": "i2s_audio.h hand-shifts 4096-sample history; 2.5x more samples per frame may increase shift work unless ring index used.",
        },
        {
            "id": "R4",
            "severity": "medium",
            "title": "DMA buffer / latency",
            "detail": f"Bytes per read {CURRENT_CHUNK*4} -> {dma_bytes_per_read} B; frame wall-clock stays ~{1000/AP_FRAME_HZ:.2f} ms if chunk scaled.",
        },
        {
            "id": "R5",
            "severity": "low",
            "title": "Extraction math unchanged",
            "detail": "SPH0645 slot_cfg + 0.000512 scaling is rate-independent; noise_cal must re-run on device.",
        },
        {
            "id": "R6",
            "severity": "low",
            "title": "NVS CONFIG drift",
            "detail": "enforce_compiled_audio_timing_config() resets persisted rate/chunk at boot — good. LittleFS snapshots with old values get repaired.",
        },
    ]

    alternatives = [
        {
            "name": "A — 32 kHz / 240 chunk (recommended in-spec)",
            "sample_rate": TARGET_SR,
            "samples_per_chunk": target_chunk,
            "ap_frame_hz": round(actual_ap_hz, 4),
            "novelty_hz": round(novelty_hz, 4),
            "bclk_hz": BCLK_TARGET,
            "bclk_in_spec": BCLK_TARGET >= BCLK_SPEC_MIN,
            "nyquist_hz": NYQUIST_TARGET,
            "bins_above_nyquist_at_79": NOTES_TOP_BIN_79_HZ > NYQUIST_TARGET,
        },
        {
            "name": "B — 16 kHz / 120 chunk (partial spec fix)",
            "sample_rate": 16000,
            "samples_per_chunk": 120,
            "ap_frame_hz": round(16000 / 120, 4),
            "novelty_hz": round(16000 / 120 / NOVELTY_DECIMATION, 4),
            "bclk_hz": 16000 * 64,
            "bclk_in_spec": False,
            "nyquist_hz": 8000,
            "bins_above_nyquist_at_79": NOTES_TOP_BIN_79_HZ > 8000,
        },
        {
            "name": "C — keep 12.8 kHz (status quo)",
            "sample_rate": CURRENT_SR,
            "samples_per_chunk": CURRENT_CHUNK,
            "ap_frame_hz": round(AP_FRAME_HZ, 4),
            "bclk_hz": BCLK_CURRENT,
            "bclk_in_spec": BCLK_CURRENT >= BCLK_SPEC_MIN,
            "nyquist_hz": NYQUIST_CURRENT,
        },
    ]

    verification = [
        "dump_raw=silence|tone after flash — verify SPH0645 hex pattern unchanged",
        "start_noise_cal after Captain silence confirm",
        "pytest tests/ full host gate",
        "pio run -e k1_hardware",
        "tempo_accuracy.py on resampled corpus — compare Acc1/Acc2 to 12.8k baseline ledger",
        "MabuTrace k1_hardware_trace_dev — GDFT us/frame budget if CPU concern",
        "eyes-on: cymbal-heavy vs bass-heavy track on device",
    ]

    return {
        "lane": 2,
        "title": "32 kHz in-spec BCLK migration model (preserve 133 Hz AP)",
        "current": {
            "sample_rate_hz": CURRENT_SR,
            "samples_per_chunk": CURRENT_CHUNK,
            "ap_frame_hz": round(AP_FRAME_HZ, 6),
            "novelty_hz": round(AP_FRAME_HZ / NOVELTY_DECIMATION, 6),
            "bclk_hz": BCLK_CURRENT,
            "bclk_in_spec": BCLK_CURRENT >= BCLK_SPEC_MIN,
            "nyquist_hz": NYQUIST_CURRENT,
        },
        "recommended_target": alternatives[0],
        "alternatives": alternatives,
        "gdft_cpu_scale_estimate": round(gdft_scale, 3),
        "block_size_example_mid_bin": {"at_12800": block_12800, "at_32000": block_32000},
        "files_to_touch": touch_list,
        "risks": risks,
        "verification_gate": verification,
        "decision_note": (
            "32 kHz hits SPH0645 BCLK minimum exactly (2.048 MHz) and raises Nyquist "
            "to 16 kHz so bins 70–79 (labelled 6.3–10.5 kHz) become physically meaningful. "
            "Cost is full timing-map + corpus + metrics re-baseline — not a mic-driver-only change."
        ),
    }


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "--out",
        type=Path,
        default=ROOT / "evidence/sample-rate-lanes/20260609-lane2-32k-migration-model.json",
    )
    args = p.parse_args()
    model = migration_model()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(model, indent=2) + "\n")
    print(json.dumps(model["recommended_target"], indent=2))
    print(json.dumps(model["current"], indent=2))
    print(f"wrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
