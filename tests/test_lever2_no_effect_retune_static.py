"""E2 freeze: this slice must not retune hsv/palette/nscale8 effect files.

C1 (2026-08-22) retired ColorFromPalette on seven live modes via
palette_manual_colour. Those files are no longer in FORBIDDEN.
Waveform / bloom / framework stay frozen until a named rewrite.
light_mode_waveform_hybrid_k1.cpp was unfrozen by the Captain on 2026-11-04
("Unfreeze waveform hybrid").
light_mode_waveform_tempo.cpp carries two exact prepared-show edits approved by
the Captain on 2026-11-10 ("All fixes now"); see PREPARED_SOURCE_EDITS.
"""

from __future__ import annotations

import re
import subprocess
import hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
# This slice vs this branch tip — not the live mainline, which keeps moving.

FORBIDDEN = [
    "SPECTRASYNQ_K1_FIRMWARE/effects/light_mode_waveform_fast.cpp",
    "SPECTRASYNQ_K1_FIRMWARE/effects/light_mode_waveform.cpp",
    "SPECTRASYNQ_K1_FIRMWARE/effects/light_mode_waveform_hybrid.cpp",
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

# Captain's 5 November end-to-end S3 qualification authorises the measured quiet
# mirror restoration. Keep this effect's colour/motion freeze: permit only the
# exact reviewed three-line repair from the original source, not arbitrary edits.
QUIET_MIRROR_PATH = "SPECTRASYNQ_K1_FIRMWARE/effects/light_mode_waveform_tempo.cpp"
QUIET_MIRROR_BEFORE = "88b9e82f4cd862c04a97be3d90cfc5fdfad9c4ab16eab52770796e366e0581e8"
QUIET_MIRROR_AFTER = "dce8c6b2a92e5d3f09e624657ab31797f97a5ccefd3c37c2c7c54e89a5d1edd5"


def _approved_quiet_mirror_repair(path, before, after):
    return (path == QUIET_MIRROR_PATH
            and hashlib.sha256(before).hexdigest() == QUIET_MIRROR_BEFORE
            and hashlib.sha256(after).hexdigest() == QUIET_MIRROR_AFTER)


# Captain, 10 November 2026 ("All fixes now", K1-FE-SHOW change requests rev 2):
# prepared-show playback must not depend on the live microphone or on the
# device's own tempo estimate. Exactly two edits to this effect are permitted on
# top of the quiet-mirror file, both inert unless k1_vp_prepared_active():
# the live peak is not OR-ed in, and the scroll runs its unlocked branch.
# Colour and live motion stay frozen: any other byte change fails.
PREPARED_SOURCE_AFTER = "15940ebaade9ce1e69c045cac87d6d0dfdbf6338375c080df86fd78fa0d1b4b7"
PREPARED_SOURCE_EDITS = (
    (b"  // Not during prepared-show playback: there the snapshot is the only source.\n"
     b"  const float live_peak = k1_vp_prepared_active() ? 0.0f : (float)waveform_peak_scaled;\n"
     b"  const float peak = tempo_clamp01(fmaxf(snap.peak_scaled, live_peak));\n",
     b"  const float peak =\n"
     b"      tempo_clamp01(fmaxf(snap.peak_scaled, (float)waveform_peak_scaled));\n"),
    (b"    a = k1_vp_audio_snapshot_read();\n"
     b"    if (k1_vp_prepared_active()) {\n"
     b"      // Prepared show: the stream carries no beat clock, and the device's own\n"
     b"      // tempo estimate depends on everything it has heard since it locked, so\n"
     b"      // the same show position would not always render the same. Run this\n"
     b"      // mode's unlocked branch (steady scroll, halted in prepared silence).\n"
     b"      t.confidence = 0.0f;\n"
     b"      t.locked = false;\n"
     b"    }\n",
     b"    a = k1_vp_audio_snapshot_read();\n"),
)


def _without_prepared_source_edits(after):
    """The file with the two permitted prepared-source edits taken back out."""
    for new, old in PREPARED_SOURCE_EDITS:
        assert after.count(new) == 1
        after = after.replace(new, old, 1)
    return after


def _approved_prepared_source_isolation(path, before, after):
    return (path == QUIET_MIRROR_PATH
            and hashlib.sha256(before).hexdigest() == QUIET_MIRROR_AFTER
            and hashlib.sha256(after).hexdigest() == PREPARED_SOURCE_AFTER)


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
    violations = []
    for path in diff.splitlines():
        before = subprocess.check_output(["git", "show", f"HEAD:{path}"], cwd=ROOT)
        after = (ROOT / path).read_bytes()
        if not (_approved_quiet_mirror_repair(path, before, after)
                or _approved_prepared_source_isolation(path, before, after)):
            violations.append(path)
    assert not violations, f"E2 freeze violated; touched:\n{chr(10).join(violations)}"


def test_quiet_mirror_allowance_rejects_other_edits_and_reversal():
    current = (ROOT / QUIET_MIRROR_PATH).read_bytes()
    assert hashlib.sha256(current).hexdigest() == PREPARED_SOURCE_AFTER
    after = _without_prepared_source_edits(current)
    assert _approved_prepared_source_isolation(QUIET_MIRROR_PATH, after, current)
    assert not _approved_prepared_source_isolation(QUIET_MIRROR_PATH, after,
                                                  current + b"\n// another edit\n")
    repair = (b"    // Scrolling can move the two halves apart even while draining. Preserve\n"
              b"    // the requested centre mirror before returning without a new colour seed.\n"
              b"    if (rp->MIRROR_ENABLED) mirror_image_downwards(leds_16);\n")
    assert after.count(repair) == 1
    before = after.replace(repair, b"", 1)
    assert _approved_quiet_mirror_repair(QUIET_MIRROR_PATH, before, after)
    assert not _approved_quiet_mirror_repair(QUIET_MIRROR_PATH, before,
                                            after + b"\n// another edit\n")
    assert not _approved_quiet_mirror_repair(QUIET_MIRROR_PATH, after, before)
    assert not _approved_quiet_mirror_repair("other.cpp", before, after)
