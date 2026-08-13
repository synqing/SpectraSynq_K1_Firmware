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
    flags = set(re.findall(r"^\s*-D([A-Za-z0-9_]+)", body, re.M))
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
