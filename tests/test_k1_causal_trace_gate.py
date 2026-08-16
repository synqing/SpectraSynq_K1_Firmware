"""Gate-5 causal trace field gate against gate0/contract.json."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = (
    ROOT
    / "docs"
    / "forensics"
    / "2026-08-15-freertos-scheduling-audit"
    / "gate0"
    / "contract.json"
)
TRACE_HINTS = ROOT / "SPECTRASYNQ_K1_FIRMWARE" / "audio" / "k1_audio_frame.h"


def test_required_trace_fields_are_enumerated_in_contract():
    contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
    fields = contract["required_trace_fields"]
    required = {
        "boot_epoch",
        "capture_sequence",
        "i2s_read_return_us",
        "newest_sample_estimate_us",
        "oldest_sample_estimate_us",
        "sample_time_assumption_id",
        "ap_generation",
        "ap_publish_us",
        "onset_epoch",
        "onset_sequence",
        "beat_epoch",
        "beat_sequence",
        "vp_frame_sequence",
        "vp_acquire_us",
        "render_start_us",
        "rmt_submit_us",
        "rmt_complete_us",
        "primary_final_bytes_crc",
        "secondary_final_bytes_crc",
        "rmt_completion_confirmed",
        "rmt_completion_source",
        "mixed_generation_count",
        "trace_drop_count",
        "trace_crc",
    }
    assert required.issubset(set(fields))
    assert "rmt_completion_confirmed" in fields
    assert "rmt_completion_source" in fields


def test_audio_frame_carries_identity_prefix_of_the_chain():
    text = TRACE_HINTS.read_text(encoding="utf-8")
    for name in (
        "boot_epoch",
        "ap_generation",
        "capture_sequence",
        "ap_publish_us",
        "onset_sequence_total",
        "beat_sequence_total",
    ):
        assert name in text
