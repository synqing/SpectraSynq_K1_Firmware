"""E2 freeze: this slice must not retune hsv/palette/nscale8 effect files.

C1 (2026-08-22) retired ColorFromPalette on seven live modes via
palette_manual_colour. Those files are no longer in FORBIDDEN.
Waveform / bloom / framework stay frozen until a named rewrite.
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
# This slice vs this branch tip — not the live mainline, which keeps moving.

FORBIDDEN = [
    "SPECTRASYNQ_K1_FIRMWARE/effects/light_mode_waveform_fast.cpp",
    "SPECTRASYNQ_K1_FIRMWARE/effects/light_mode_waveform.cpp",
    "SPECTRASYNQ_K1_FIRMWARE/effects/light_mode_waveform_hybrid.cpp",
    "SPECTRASYNQ_K1_FIRMWARE/effects/light_mode_waveform_hybrid_k1.cpp",
    "SPECTRASYNQ_K1_FIRMWARE/effects/light_mode_waveform_tempo.cpp",
    "SPECTRASYNQ_K1_FIRMWARE/effects/light_mode_bloom.cpp",
    "SPECTRASYNQ_K1_FIRMWARE/effects/framework/effect_lgp_transient_lattice.cpp",
    "SPECTRASYNQ_K1_FIRMWARE/effects/framework/effect_lgp_flux_rift.cpp",
    "SPECTRASYNQ_K1_FIRMWARE/effects/framework/effect_beat_pulse_resonant.cpp",
    "SPECTRASYNQ_K1_FIRMWARE/effects/framework/effect_lgp_beat_prism.cpp",
    "SPECTRASYNQ_K1_FIRMWARE/effects/framework/effect_lgp_harmonic_tide.cpp",
    "SPECTRASYNQ_K1_FIRMWARE/effects/framework/RenderPrimitives.cpp",
    "SPECTRASYNQ_K1_FIRMWARE/effects/framework/ZoneComposer.cpp",
]

WAVEFORM_FAST = ROOT / "SPECTRASYNQ_K1_FIRMWARE" / "effects" / "light_mode_waveform_fast.cpp"
# Four live hsv() call sites (CRUSH_MAP §3a); one mention lives in a comment.
WAVEFORM_FAST_HSV_CALLS = 4


def test_waveform_fast_hsv_call_count_frozen():
    src = WAVEFORM_FAST.read_text(encoding="utf-8")
    calls = [
        line
        for line in src.splitlines()
        if re.search(r"\bhsv\s*\(", line) and not line.lstrip().startswith("//")
    ]
    assert len(calls) == WAVEFORM_FAST_HSV_CALLS, (
        f"waveform_fast hsv() call count changed: {len(calls)} "
        f"(frozen {WAVEFORM_FAST_HSV_CALLS})"
    )


def test_forbidden_effect_files_untouched():
    diff = subprocess.check_output(
        ["git", "diff", "--name-only", "HEAD", "--"] + FORBIDDEN,
        cwd=ROOT,
        text=True,
    ).strip()
    assert diff == "", f"E2 freeze violated; touched:\n{diff}"
