# SPDX-License-Identifier: Apache-2.0
# Copyright 2025-2026 SpectraSynq
"""Static ratchet against the 2026-08-06 config-coupling defect class.

Canon: docs/agent/SESSION_CANON_2026-08-06_audio_config_coupling.md

Three mechanical gates, each tied to a real defect that cost a full session and that
NO existing host test could see (they are semantic mismatches between a value and its
hardware context; the suite has no hardware):

  1. -ffast-math implies -ffinite-math-only, under which GCC folds isfinite()/isnan()/
     isinf() to a constant. Measured on this toolchain: `return !isfinite(x)` compiled to
     `movi.n a2,0; retw.n`. 93 guard sites across 42 files were silently deleted from the
     binary, including PDM cold-boot 0/0->NaN guards. -fno-finite-math-only must follow it.

  2. Per-mic constant overrides must be SYMMETRIC. IM69D silently inherited SPH0645
     calibration-admission gates because the IM73D widening sits behind a mutually
     exclusive flag. Those gates are what refuse a music-contaminated noise calibration.

  3. A #if/#elif chain over mic flags must have a terminal #else. The STM loudness gate
     had none, so on the SPH0645 path the value stayed 0.0 and EdgeMixer modes 7/8
     modulated by nothing -- reproducing the exact bug the block was written to fix.

RATCHET, not a cleanup mandate: today's known gaps are listed explicitly so the suite is
green, and NEW asymmetry fails. Closing a listed gap means deleting its entry.
"""
from __future__ import annotations

import re
from pathlib import Path

ROOT = next(p for p in Path(__file__).resolve().parents if (p / "platformio.ini").is_file())
CONSTANTS = ROOT / "SPECTRASYNQ_K1_FIRMWARE" / "system" / "constants.h"
AUDIO_DIR = ROOT / "SPECTRASYNQ_K1_FIRMWARE" / "audio"

MIC_FLAGS = ("K1_MIC_IM73D_PDM_V1", "K1_MIC_IM69D_PDM_V1")

# Known, dated asymmetries. Each entry is technical debt with a reason; closing one
# means removing it here. Do NOT add to this list to make a new change pass.
KNOWN_ASYMMETRIC: dict[str, str] = {
    "WAVEFORM_REACTIVE_RAW_MARGIN": (
        "2026-08-06: IM73D-only override; IM69D still inherits the SPH0645 base. "
        "Flagged in the session canon, not yet measured for IM69D."
    ),
    # The following two are INTENTIONAL hardware differences, not debt.
    "K1_PDM_LR_PIN": (
        "IM73D drives SELECT/LR low for the LEFT slot. IM69D has no equivalent: on PCB3 "
        "SELECT is hard-strapped and must NEVER be driven."
    ),
    "K1_IM69_PDM_SEL_PIN": (
        "IM69D-only. Documents the hard-strapped, do-not-drive SELECT pin so nobody wires "
        "it as an LR output. Deliberately has no IM73D peer."
    ),
}

# Known #elif chains still missing a terminal #else. Same ratchet rule.
KNOWN_MISSING_ELSE: dict[str, str] = {
    "raw_rms_for_stm": (
        "DEBT, 2026-08-06: K1_STM loudness gate. On k1_hardware_stm (SPH0645, neither PDM "
        "flag) the value stays 0.0 -> agc_loudness_norm == 0 -> EdgeMixer modes 7/8 modulate "
        "by nothing. Fix is an explicit loud bypass mirroring k1_mic_auto_sense's "
        "BYPASSED / RAW_UNAVAILABLE shape, NOT a fabricated SPH RMS."
    ),
    "raw_i16_abs_peak": (
        "BENIGN, not debt: optional per-mic telemetry appended to the [AP] line. The SPH "
        "path simply prints nothing extra; no value is left silently unset."
    ),
}


def _normalise(name: str) -> str:
    """Collapse the mic token so IM73D/IM69D peers compare equal."""
    return name.replace("IM73D", "*").replace("IM69D", "*")


def _block_bodies(text: str, flag: str) -> list[str]:
    """Return the source of every `#ifdef <flag>` block, by preprocessor depth."""
    lines = text.splitlines()
    bodies, depth, buf = [], None, []
    for line in lines:
        s = line.strip()
        if depth is None:
            if re.match(rf"#\s*ifdef\s+{re.escape(flag)}\b", s):
                depth, buf = 1, []
            continue
        if re.match(r"#\s*if(def|ndef)?\b", s):
            depth += 1
        elif re.match(r"#\s*endif\b", s):
            depth -= 1
            if depth == 0:
                bodies.append("\n".join(buf))
                depth = None
                continue
        buf.append(line)
    return bodies


def _defined_names(body: str) -> set[str]:
    return {m.group(1) for m in re.finditer(r"^\s*#\s*define\s+([A-Za-z_]\w*)", body, re.M)}


def test_fast_math_keeps_nan_awareness():
    """-fno-finite-math-only must follow -ffast-math, or every isfinite() guard is deleted."""
    ini = (ROOT / "platformio.ini").read_text(encoding="utf-8")
    if "-ffast-math" not in ini:
        return  # flag gone entirely; nothing to protect
    fast = ini.index("-ffast-math")
    assert "-fno-finite-math-only" in ini, (
        "platformio.ini enables -ffast-math without -fno-finite-math-only. GCC then folds "
        "isfinite()/isnan()/isinf() to a constant and DELETES every such guard from the "
        "binary (93 sites across 42 files as of 2026-08-06, including the PDM cold-boot "
        "0/0->NaN guards). See docs/agent/SESSION_CANON_2026-08-06_audio_config_coupling.md"
    )
    assert ini.index("-fno-finite-math-only") > fast, (
        "-fno-finite-math-only must come AFTER -ffast-math; GCC applies these left to right."
    )


def test_per_mic_overrides_are_symmetric():
    """A constant overridden for one PDM mic must have a peer arm for the other."""
    text = CONSTANTS.read_text(encoding="utf-8")
    per_mic = {
        flag: {_normalise(n) for b in _block_bodies(text, flag) for n in _defined_names(b)}
        for flag in MIC_FLAGS
    }
    a, b = per_mic[MIC_FLAGS[0]], per_mic[MIC_FLAGS[1]]
    allowed = {_normalise(k) for k in KNOWN_ASYMMETRIC}
    unexpected = sorted(((a - b) | (b - a)) - allowed)
    assert not unexpected, (
        "Per-mic constant override asymmetry — one microphone silently inherits the other's "
        f"(or the SPH0645 base) value for: {unexpected}. This is the defect that let IM69D "
        "run on SPH0645 calibration-admission gates, defeating the guard that refuses a "
        "music-contaminated noise cal. Add the peer arm, or justify it in KNOWN_ASYMMETRIC."
    )


def test_mic_elif_chains_have_terminal_else():
    """`#if MIC_A / #elif MIC_B` with no `#else` leaves a third hardware path silently unset."""
    offenders = []
    for path in sorted(AUDIO_DIR.rglob("*.h")) + sorted(AUDIO_DIR.rglob("*.cpp")):
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
        depth_stack: list[bool] = []      # True while inside a mic-flag conditional
        saw_else: list[bool] = []
        saw_elif: list[bool] = []         # only CHAINS matter; a plain #ifdef needs no #else
        start_at: list[int] = []          # block start, so exemptions scan the WHOLE body
        for i, line in enumerate(lines):
            s = line.strip()
            if re.match(r"#\s*if(def)?\b", s):
                depth_stack.append(any(f in s for f in MIC_FLAGS))
                saw_else.append(False)
                saw_elif.append(False)
                start_at.append(i)
            elif re.match(r"#\s*elif\b", s) and depth_stack:
                depth_stack[-1] = depth_stack[-1] or any(f in s for f in MIC_FLAGS)
                saw_elif[-1] = True
            elif re.match(r"#\s*else\b", s) and saw_else:
                saw_else[-1] = True
            elif re.match(r"#\s*endif\b", s) and depth_stack:
                is_mic = depth_stack.pop()
                had_else = saw_else.pop()
                had_elif = saw_elif.pop()
                blk_start = start_at.pop()
                if is_mic and had_elif and not had_else:
                    ctx = "\n".join(lines[blk_start:i])
                    if not any(k in ctx for k in KNOWN_MISSING_ELSE):
                        offenders.append(f"{path.relative_to(ROOT)}:{i + 1}")
    assert not offenders, (
        "Mic-flag conditional with no terminal #else — a third hardware path (e.g. SPH0645, "
        f"which defines neither PDM flag) silently keeps the initialiser: {offenders}. "
        "Prefer an explicit loud bypass, as k1_mic_auto_sense.cpp does, over a silent zero."
    )
