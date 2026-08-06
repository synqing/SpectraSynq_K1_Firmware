"""Host reconstruction of K1's per-Goertzel-bin frequency honesty (alias-aware).

Measurement-only. Mirrors precompute_goertzel_constants() (system.h) for the
DEFAULT chroma profile (NOTE_OFFSET=12) to expose, per bin:

  sample_rate_hz, nyquist_hz
  target_hz             -- the musical note the bin is labelled with
  target_folded_hz      -- target folded into [0, Nyquist] (real-audio band)
  target_above_nyquist  -- the label itself is above Nyquist (not representable)
  k, block_size
  raw_center_hz         -- k * fs / block_size (the bare Goertzel resonance)
  effective_center_hz   -- raw_center folded into [0, Nyquist]
  target_error_hz       -- effective_center_hz - target_folded_hz
  label_error_hz        -- effective_center_hz - target_hz, ONLY when the label is
                           representable (target <= Nyquist); else None

WHY ALIAS-AWARE: at fs = 12800, Nyquist = 6400 Hz. A magnitude-only Goertzel on a
REAL sampled signal cannot distinguish f from fs - f, so a raw_center (or note
label) above Nyquist does NOT denote a physically distinct real-audio centre --
it folds. 9 of the 80 bins (71..79) are labelled ABOVE Nyquist. The firmware is
aware: k1_gdft_nyquist_safe_bin_hi() (constants.h) clamps the downstream onset /
AudioSemanticState consumers to the safe range (k1_audio_snapshot.cpp,
k1_onset_beat.cpp). Energy-side counterpart: high_bin_alias_audit.py (same fold
convention). Firmware is source of truth; this changes nothing in it.
"""

import re
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
FW = ROOT / "SPECTRASYNQ_K1_FIRMWARE"
CONSTANTS_H = (FW / "system" / "constants.h").read_text(encoding="utf-8")
CONFIG_TYPES_H = (FW / "system" / "config_types.h").read_text(encoding="utf-8")
SYSTEM_H = (FW / "system" / "system.h").read_text(encoding="utf-8")
GLOBALS_CONFIG = (FW / "system" / "globals_config.cpp").read_text(encoding="utf-8")


def _define_int(text, name):
    m = re.search(rf"#define\s+{re.escape(name)}\s+(\d+)", text)
    if not m:
        raise ValueError(f"missing #define {name}")
    return int(m.group(1))


def parse_notes():
    """The literal `const float notes[] = { ... };` table from constants.h."""
    m = re.search(r"const\s+float\s+notes\[\]\s*=\s*\{(.*?)\};", CONSTANTS_H, re.DOTALL)
    if not m:
        raise ValueError("notes[] table not found in constants.h")
    vals = [v.strip() for v in m.group(1).split(",") if v.strip()]
    return np.array([np.float32(v) for v in vals], dtype=np.float32)


def parse_note_offset():
    """DEFAULT NOTE_OFFSET from the globals_config.cpp aggregate init."""
    m = re.search(r"(\d+)\s*,\s*//\s*NOTE_OFFSET", GLOBALS_CONFIG)
    if not m:
        raise ValueError("default NOTE_OFFSET not found in globals_config.cpp")
    return int(m.group(1))


def parse_block_size_cap():
    """The block_size ceiling from system.h (if (block_size > N) block_size = N)."""
    m = re.search(r"block_size\s*>\s*(\d+)", SYSTEM_H)
    if not m:
        raise ValueError("block_size cap not found in system.h")
    return int(m.group(1))


# --- config (parsed; no hard-coded drift) ----------------------------------
SAMPLE_RATE = _define_int(CONFIG_TYPES_H, "DEFAULT_SAMPLE_RATE")
NUM_FREQS = _define_int(CONFIG_TYPES_H, "NUM_FREQS")
NOTE_OFFSET = parse_note_offset()
BLOCK_SIZE_CAP = parse_block_size_cap()
NOTES = parse_notes()
NYQUIST_HZ = SAMPLE_RATE / 2.0


def fold_to_real_audio_band(f, sample_rate=SAMPLE_RATE):
    """Map any frequency into the real-audio band [0, Nyquist] by folding.
    A magnitude-only Goertzel on real samples cannot distinguish f from
    sample_rate - f, so anything above Nyquist aliases back. Same convention as
    high_bin_alias_audit.py."""
    f_mod = f % sample_rate
    nyquist = sample_rate / 2.0
    return (sample_rate - f_mod) if f_mod > nyquist else f_mod


def _block_size(target, nl, nr, sample_rate, cap, bin_index=0, x2_crossover=0):
    """Mirror system.h Rayleigh sizing with ×2 crossover.

    Bins with index < x2_crossover keep legacy ×2; at/above use fs/Δf (1-semitone).
    CTO default x2_crossover=0 → global drop of ×2.
    """
    dl = np.float32(abs(np.float32(nl) - np.float32(target)))
    dr = np.float32(abs(np.float32(nr) - np.float32(target)))
    max_distance = np.float32(max(np.float32(0.0), dl, dr))
    if max_distance <= np.float32(0.0):
        return 0
    resolution_div = 2.0 if bin_index < x2_crossover else 1.0
    bs = int(sample_rate / (float(max_distance) * resolution_div))  # int/double -> trunc
    return min(bs, cap)


def _bin_k(block_size, target, sample_rate):
    """Mirror system.h: k = (int)(0.5 + (block_size * target_freq) / SAMPLE_RATE)."""
    if block_size == 0:
        return 0
    inner = np.float32(np.float32(block_size) * np.float32(target)) / np.float32(sample_rate)
    return int(0.5 + float(inner))


def _bin_k_true_center(block_size, target, sample_rate):
    """Mirror system.h ON path (K1_GDFT_TRUE_CENTER_V1): the coefficient is
    2*cos(2*PI*target/fs), so the bin resonates at EXACTLY target. The implied k is
    target*block_size/fs and is NOT rounded -> raw_center == target. Used only for
    representable bins (target <= Nyquist); above Nyquist the firmware keeps
    rounded-k, so this helper is not called there."""
    if block_size == 0:
        return 0.0
    return float(np.float32(np.float32(block_size) * np.float32(target)) / np.float32(sample_rate))


def compute_bins(sample_rate=SAMPLE_RATE, note_offset=NOTE_OFFSET,
                 num_freqs=NUM_FREQS, notes=NOTES, cap=BLOCK_SIZE_CAP,
                 mode="rounded_k", x2_crossover=0):
    """Per-bin alias-aware honesty table mirroring precompute_goertzel_constants().

    mode="rounded_k"  (default) -> legacy K1_GDFT_TRUE_CENTER_V1=0 behaviour.
    mode="true_center"          -> K1_GDFT_TRUE_CENTER_V1=1: representable bins
                                   (target <= Nyquist) resonate at the exact target;
                                   above-Nyquist bins keep rounded-k (folded).
    x2_crossover                -> mirror K1_GDFT_X2_CROSSOVER_BIN (default 0 =
                                   global 1-semitone / drop ×2).
    """
    if mode not in ("rounded_k", "true_center"):
        raise ValueError(f"unknown mode {mode!r}")
    nyquist = sample_rate / 2.0
    bins = []
    for i in range(num_freqs):
        target = float(notes[i + note_offset])
        # neighbour selection (system.h): endpoints clamp the missing side to self.
        if i == 0:
            nl, nr = notes[i + note_offset], notes[i + note_offset + 1]
        elif i == num_freqs - 1:
            nl, nr = notes[i + note_offset - 1], notes[i + note_offset]
        else:
            nl, nr = notes[i + note_offset - 1], notes[i + note_offset + 1]

        block_size = _block_size(target, nl, nr, sample_rate, cap,
                                 bin_index=i, x2_crossover=x2_crossover)
        if mode == "true_center" and target <= nyquist:
            # representable bin: exact-frequency coefficient (non-integer k)
            k = _bin_k_true_center(block_size, target, sample_rate)
        else:
            # rounded-k (legacy, and the above-Nyquist branch even in true_center)
            k = _bin_k(block_size, target, sample_rate)
        if block_size > 0:
            raw_center = k * sample_rate / block_size
            true_res = sample_rate / block_size
        else:
            raw_center = 0.0
            true_res = 0.0

        effective_center = fold_to_real_audio_band(raw_center, sample_rate)
        target_folded = fold_to_real_audio_band(target, sample_rate)
        target_above_nyquist = target > nyquist
        # label_error is only meaningful where the labelled note is representable.
        label_error = None if target_above_nyquist else (effective_center - target)

        bins.append({
            "bin": i,
            "sample_rate_hz": sample_rate,
            "nyquist_hz": nyquist,
            "target_hz": target,
            "target_folded_hz": target_folded,
            "target_above_nyquist": target_above_nyquist,
            "k": k,
            "block_size": block_size,
            "raw_center_hz": raw_center,
            "effective_center_hz": effective_center,
            "target_error_hz": effective_center - target_folded,
            "label_error_hz": label_error,
            "true_resolution_hz": true_res,
        })
    return bins


def summarize(bins):
    nyquist = bins[0]["nyquist_hz"]
    above = [b for b in bins if b["target_above_nyquist"]]
    representable = [b for b in bins if not b["target_above_nyquist"]]
    worst = max(representable, key=lambda b: abs(b["label_error_hz"]))
    res = [b["true_resolution_hz"] for b in bins]
    return {
        "num_bins": len(bins),
        "nyquist_hz": nyquist,
        "num_above_nyquist": len(above),
        "above_nyquist_bins": [b["bin"] for b in above],
        # Worst label error among bins whose note is actually representable.
        "max_representable_label_error_hz": abs(worst["label_error_hz"]),
        "max_representable_label_error_bin": worst["bin"],
        "max_representable_label_error_target_hz": worst["target_hz"],
        "min_resolution_hz": min(res),
        "max_resolution_hz": max(res),
        "max_effective_center_hz": max(b["effective_center_hz"] for b in bins),
    }


def render_markdown(bins):
    s = summarize(bins)
    lines = []
    lines.append("# K1 GDFT Per-Bin Frequency Honesty (alias-aware, DEFAULT profile)")
    lines.append("")
    lines.append("> Generated by `scripts/regression-harness/gdft_center_honesty_model.py`. "
                 "Validated by `tests/test_gdft_center_honesty.py`. Energy-side counterpart: "
                 "`high_bin_alias_audit.py`.")
    lines.append("")
    lines.append(f"- Config: `fs={SAMPLE_RATE} Hz`, `Nyquist={NYQUIST_HZ:.0f} Hz`, "
                 f"`NUM_FREQS={NUM_FREQS}`, `NOTE_OFFSET={NOTE_OFFSET}`, "
                 f"`block_size_cap={BLOCK_SIZE_CAP}`.")
    lines.append(f"- **{s['num_above_nyquist']} bins are labelled ABOVE Nyquist** "
                 f"(bins {s['above_nyquist_bins'][0]}..{s['above_nyquist_bins'][-1]}): "
                 f"not physically representable; their raw_center FOLDS into the real band.")
    lines.append(f"- For representable bins, the rounded-k coefficient still offsets the "
                 f"centre: worst label error **{s['max_representable_label_error_hz']:.1f} Hz** "
                 f"at bin {s['max_representable_label_error_bin']} "
                 f"(label {s['max_representable_label_error_target_hz']:.1f} Hz).")
    lines.append(f"- Every effective_center <= Nyquist ({NYQUIST_HZ:.0f} Hz). "
                 f"Resolution cell spans {s['min_resolution_hz']:.1f}..{s['max_resolution_hz']:.1f} Hz.")
    lines.append("")
    lines.append("| bin | target_hz | >Nyq | target_folded_hz | block_size | k "
                 "| raw_center_hz | effective_center_hz | label_error_hz | true_res_hz |")
    lines.append("|----:|----------:|:---:|-----------------:|-----------:|--:"
                 "|-------------:|--------------------:|---------------:|------------:|")
    for b in bins:
        le = "n/a" if b["label_error_hz"] is None else f"{b['label_error_hz']:+.2f}"
        flag = "yes" if b["target_above_nyquist"] else ""
        lines.append(f"| {b['bin']} | {b['target_hz']:.2f} | {flag} "
                     f"| {b['target_folded_hz']:.2f} | {b['block_size']} | {b['k']} "
                     f"| {b['raw_center_hz']:.2f} | {b['effective_center_hz']:.2f} "
                     f"| {le} | {b['true_resolution_hz']:.1f} |")
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    print(render_markdown(compute_bins()))
