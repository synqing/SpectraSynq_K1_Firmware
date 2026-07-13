"""Static craft gate for K1 light-show effect ports.

Locks in the 2026-07-11 gem-port session's hard-won lessons so no future change
silently reintroduces the "stuttering / on-off" amateur look. Canon:
docs/effect-craft/PORTING_CRAFT_CANON.md ; shared kit: visual/easing.h.

Scope: the manifests below — effects governed by the easing canon. When you add a
NEW audio-reactive port, add it to GOVERNED_PORTS (and to KIT_PORTS if it uses the
shared kit, which new ports SHOULD). Legacy native effects roll their own private
followers and some are legitimately stateless/event-gated, so enforcement is
manifest-scoped by design (auto-scanning all effects would false-positive).
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FW = ROOT / "SPECTRASYNQ_K1_FIRMWARE"
EFFECTS = FW / "effects"

# Ports eased via the shared kit — MUST include easing.h and call k1ease::follow.
KIT_PORTS = [
    "light_mode_bloom_bt.cpp",
    "light_mode_moire_cathedral.cpp",
]
# All ports governed by the easing canon (kit ports + ports eased with a valid
# private asymmetric follower). Each MUST show asymmetric easing + no raw gate.
GOVERNED_PORTS = KIT_PORTS + [
    "light_mode_waveform_hybrid_k1.cpp",   # eased via its own wfhyb_follow (tau_up/tau_dn)
    "light_mode_shockwave.cpp",
    "light_mode_iris.cpp",
]

# Evidence of an asymmetric follower: the shared kit, OR a private follower that
# distinguishes a rising (attack) tau from a falling (release) tau.
_ASYM = re.compile(
    r"k1ease::follow\(|attack_tau|release_tau|tau_up|tau_dn|_ATTACK_TAU|_RELEASE_TAU")


def test_easing_kit_exists_and_exports_api():
    """The shared easing kit must exist — no rolling a 9th private follower."""
    easing = FW / "visual" / "easing.h"
    assert easing.exists(), "visual/easing.h (the canonical easing kit) is missing"
    text = easing.read_text()
    assert "namespace k1ease" in text
    for sym in ("follow(", "safe_dt(", "decay(", "ema("):
        assert sym in text, f"easing.h must export k1ease::{sym}"


def test_canon_and_skill_present():
    """The craft canon + the skill that points to it must not be deleted."""
    assert (ROOT / "docs" / "effect-craft" / "PORTING_CRAFT_CANON.md").exists(), \
        "docs/effect-craft/PORTING_CRAFT_CANON.md (the craft canon) is missing"
    skill = ROOT / ".claude" / "skills" / "k1-effect-development" / "SKILL.md"
    assert skill.exists() and "MANDATORY Temporal Easing" in skill.read_text(), \
        "k1-effect-development skill must retain the mandatory-easing section"


def test_kit_ports_use_shared_easing_kit():
    """Kit ports must include easing.h AND call k1ease::follow."""
    for name in KIT_PORTS:
        f = EFFECTS / name
        assert f.exists(), f"kit port {name} not found"
        text = f.read_text()
        assert '#include "easing.h"' in text, (
            f'{name}: must #include "easing.h" — canon §1')
        assert "k1ease::follow(" in text, (
            f"{name}: must apply k1ease::follow(...) to its audio drive "
            f"(fast attack / slow release) — canon §1")


def test_governed_ports_apply_asymmetric_easing():
    """Every governed port must show an asymmetric follower (shared or private) —
    proof it eases an audio drive rather than writing it raw to brightness."""
    for name in GOVERNED_PORTS:
        text = (EFFECTS / name).read_text()
        assert _ASYM.search(text), (
            f"{name}: no asymmetric follower found (k1ease::follow or attack/release "
            f"taus). Raw audio -> brightness is the #1 amateur-look rejection — canon §1")


def test_governed_ports_have_no_raw_multiplicative_silence_gate():
    """A hard `snap.silence ? 0` is fine as the TARGET of a follower (assignment),
    but must never directly multiply output (a hard snap-to-black). Flag the raw
    multiplicative form; allow the assign-then-follow form."""
    raw_gate = re.compile(r"[*].*snap\.silence\s*\?\s*0|snap\.silence\s*\?\s*0[^;]*[*]")
    for name in GOVERNED_PORTS:
        text = (EFFECTS / name).read_text()
        for i, line in enumerate(text.splitlines(), 1):
            if raw_gate.search(line) and "k1ease" not in line:
                raise AssertionError(
                    f"{name}:{i}: raw multiplicative silence gate — ease it "
                    f"(sil = k1ease::follow(sil, snap.silence?0:1, dt, 0.05, 0.30)) "
                    f"and multiply output by the eased value (canon §1)")


def test_governed_ports_are_frame_rate_independent():
    """Followers must be driven by a clamped dt, never a bare frame counter."""
    for name in GOVERNED_PORTS:
        text = (EFFECTS / name).read_text()
        has_dt = ("k1ease::safe_dt(" in text) or re.search(r"float\s+dt\s*=", text)
        assert has_dt, (
            f"{name}: no dt source — use k1ease::safe_dt(millis(), fx.<p>_last_ms) "
            f"so easing is frame-rate independent (canon §1.7)")
