"""Static ratchets for the colour-fix flag set (canon 2026-08-14, HF-50..62;
promotion plan blocker #1). Each pins a failure class that already burned time:

- BRIGHT_EXCURSION and ENERGY_EXCURSION co-defined would compound two arc
  excursions (promotion plan §1.3) — mutual exclusion, per effective env chain.
- The consolidated candidate env must actually carry ALL fix flags (HF-56 was a
  fix that silently never landed; this pins the flag half of that class).
- The equalised sweep drive must contain an explicit rest mechanism (HF-51:
  scale-blind drives never rest on their own; the wake gate is load-bearing).
- Fix flags must not leak into shippable envs before the gated promotion.
"""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INI = (ROOT / "platformio.ini").read_text(encoding="utf-8")

FIX_FLAGS = {
    "K1_HUE_DRIVE_EQ_V1",
    "K1_FALLBACK_HELD_U_V1",
    "K1_PALETTE_BRIGHT_EXCURSION_V1",
    "K1_POSITION_SMOOTH_V1",
    "K1_INCANDESCENT_OUTPUT_V1",
    "K1_EDGE_PALETTE_HONOUR_V1",
}
SHIPPABLE_ENVS = {"k1_hardware", "k1_prod_im73d", "k1_bench_reference"}


def _sections():
    """env name -> section text."""
    out = {}
    for m in re.finditer(r"^\[env:([^\]]+)\]\n(.*?)(?=^\[|\Z)", INI, re.M | re.S):
        out[m.group(1)] = m.group(2)
    return out


def _effective_flags(env, sections, seen=None):
    """-D flags of an env including its extends chain."""
    seen = seen or set()
    if env in seen or env not in sections:
        return set()
    seen.add(env)
    body = sections[env]
    # Match -D anywhere in the (uncommented) section body, not just at line start:
    # `build_flags = -DFLAG` on one line is valid ini and would otherwise slip the
    # leak check entirely. Verified by mutation — the line-anchored form missed it.
    uncommented = "\n".join(
        l for l in body.splitlines() if not l.lstrip().startswith(("#", ";"))
    )
    flags = set(re.findall(r"-D([A-Za-z0-9_]+)", uncommented))
    ext = re.search(r"^extends\s*=\s*env:([^\s]+)", body, re.M)
    if ext:
        flags |= _effective_flags(ext.group(1), sections, seen)
    return flags


def test_bright_and_energy_excursion_are_mutually_exclusive():
    sections = _sections()
    offenders = [
        env for env in sections
        if {"K1_PALETTE_BRIGHT_EXCURSION_V1", "K1_PALETTE_ENERGY_EXCURSION_V1"}
        <= _effective_flags(env, sections)
    ]
    assert offenders == [], (
        f"envs compound BOTH palette excursions: {offenders} — "
        "S2 supersedes ENERGY_EXCURSION; they must never co-define"
    )


def test_consolidated_candidate_carries_every_fix_flag():
    sections = _sections()
    assert "k1_bench_im69d_colourfix" in sections, "candidate env missing"
    have = _effective_flags("k1_bench_im69d_colourfix", sections)
    missing = FIX_FLAGS - have
    assert missing == set(), (
        f"candidate env is missing fix flags: {sorted(missing)} — "
        "a fix that isn't in the flag chain silently never lands (HF-56 class)"
    )


def test_fix_flags_do_not_leak_into_shippable_envs_pre_promotion():
    sections = _sections()
    leaks = {
        env: sorted(FIX_FLAGS & _effective_flags(env, sections))
        for env in SHIPPABLE_ENVS
        if env in sections and FIX_FLAGS & _effective_flags(env, sections)
    }
    assert leaks == {}, (
        f"fix flags reached shippable envs before the gated promotion: {leaks} — "
        "promotion requires the plan's blockers closed + Captain eyes-on"
    )


CAL_FLAG = "K1_CAL_PARTIAL_COMMIT_V1"


def test_cal_partial_commit_does_not_leak_into_shippable_envs():
    """The partial commit changes calibration semantics (a valid DC survives an
    SSL refusal). It is a bench instrument until device-proven; production must
    stay byte-inert."""
    sections = _sections()
    leaks = sorted(
        env for env in SHIPPABLE_ENVS
        if env in sections and CAL_FLAG in _effective_flags(env, sections)
    )
    assert leaks == [], f"{CAL_FLAG} reached shippable envs: {leaks}"


def test_cal_partial_commit_is_applied_at_every_rollback_exit():
    """HF class 'a guard that is not called is not a guard': the rollback has TWO
    exits (restore-previous and no-previous-valid-profile). A partial commit wired
    to only one of them silently does nothing on the other path — which is exactly
    the path taken when the previous profile is invalid."""
    src = (ROOT / "SPECTRASYNQ_K1_FIRMWARE" / "calibration" /
           "noise_cal.h").read_text(encoding="utf-8")
    body = re.search(
        r"void noise_cal_restore_previous_or_invalidate\(\)\s*\{(.*?)\n\}",
        src, re.S)
    assert body, "rollback function not found"
    calls = len(re.findall(r"noise_cal_commit_partial_dc\s*\(", body.group(1)))
    assert calls == 2, (
        f"partial commit is applied at {calls} of the 2 rollback exits — "
        "an unreached guard is not a guard"
    )


def test_cal_partial_commit_persists_so_reboot_cannot_re_poison():
    """The cal profile file overwrites CONFIG.DC_OFFSET at boot (bridge_fs.h), so a
    RAM-only commit is undone by the next reboot (four-way identity, HF-58)."""
    src = (ROOT / "SPECTRASYNQ_K1_FIRMWARE" / "calibration" /
           "noise_cal.h").read_text(encoding="utf-8")
    fn = re.search(r"void noise_cal_commit_partial_dc\([^)]*\)\s*\{(.*?)\n\}",
                   src, re.S)
    assert fn, "noise_cal_commit_partial_dc not found"
    assert "save_calibration_profile" in fn.group(1), (
        "partial commit does not persist the profile — the boot-time profile "
        "load would restore the stale DC on the next reboot"
    )


def test_subsonic_hpf_cutoff_is_derived_from_note_offset():
    """The HPF may only remove content the GDFT cannot display. Its lowest bin is
    55 Hz * 2^(NOTE_OFFSET/12) — a RUNTIME value — so a hardcoded cutoff tuned for
    NOTE_OFFSET=12 (110 Hz) would cut an octave of real, displayed bass at
    NOTE_OFFSET=0 (a shipped configuration). The cutoff must be derived."""
    g = (ROOT / "SPECTRASYNQ_K1_FIRMWARE" / "system" /
         "globals.h").read_text(encoding="utf-8")
    i2s = (ROOT / "SPECTRASYNQ_K1_FIRMWARE" / "audio" /
           "i2s_audio.h").read_text(encoding="utf-8")

    fn = re.search(r"k1_subsonic_hpf_cutoff_hz\([^)]*\)\s*\{(.*?)\n\}", g, re.S)
    assert fn, "cutoff helper missing — cutoff is not derived"
    assert "note_offset" in fn.group(1) and "55.0f" in fn.group(1), (
        "cutoff helper does not derive from NOTE_OFFSET and the 55 Hz origin"
    )

    blk = re.search(r"#ifdef\s+K1_AP_SUBSONIC_HPF_V1(.*?)#endif", i2s, re.S)
    assert blk, "HPF derivation block not found in the audio path"
    assert "CONFIG.NOTE_OFFSET" in blk.group(1), (
        "the filter coefficient is not recomputed from the live NOTE_OFFSET"
    )
    assert "k1_subsonic_hpf_a" in i2s and "K1_SUBSONIC_HPF_A" not in i2s, (
        "the filter still uses a hardcoded coefficient macro"
    )


def test_subsonic_hpf_does_not_leak_into_shippable_envs():
    sections = _sections()
    leaks = sorted(
        env for env in SHIPPABLE_ENVS
        if env in sections and "K1_AP_SUBSONIC_HPF_V1" in _effective_flags(env, sections)
    )
    assert leaks == [], f"K1_AP_SUBSONIC_HPF_V1 reached shippable envs: {leaks}"


def test_equalised_sweep_drive_contains_a_rest_mechanism():
    """HF-51: a scale-blind drive without an explicit rest runs forever in
    silence (measured: full-bore motion with zero sound). The wake gate is
    load-bearing — deleting it must turn this test red."""
    led = (ROOT / "SPECTRASYNQ_K1_FIRMWARE" / "visual" /
           "led_utilities.h").read_text(encoding="utf-8")
    m = re.search(r"#ifdef\s+K1_HUE_DRIVE_EQ_V1(.*?)#else", led, re.S)
    assert m, "K1_HUE_DRIVE_EQ_V1 drive block not found"
    block = m.group(1)
    assert "k1_sweep_wake" in block and "structured" in block, (
        "the equalised drive lost its structural rest mechanism (wake gate) — "
        "the percentile of noise-within-noise is uniform; without the gate the "
        "sweep never rests in silence (HF-51)"
    )
    assert re.search(r"adv\s*=.*k1_sweep_wake", block), (
        "the wake gate exists but is not applied to the advance — a guard that "
        "is not on the path is not a guard"
    )
