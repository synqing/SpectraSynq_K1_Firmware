"""Audio-profile tombstone gate (Captain order 2026-08-11).

The IM73D-gated tempo/silence constants were measured on Bench Unit 2 under a mic
identity that Captain correction 2026-08-10 voided. They are DELETED from source,
not carried behind a label, because a carried-and-labelled constant reliably
becomes a trusted one.

These tests are the tripwire against reinstatement. They assert the ABSENCE of
the six deleted values and the PRESENCE of the fail-closed guard — a purely
documentary tombstone would let the next agent paste the numbers back.

Provenance: docs/forensics/audio-profile/2026-08-11-im73d-profile-tombstone.md
"""
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
FW = ROOT / "SPECTRASYNQ_K1_FIRMWARE"
PROFILE = FW / "audio" / "k1_audio_profile.h"
TEMPO = FW / "audio" / "k1_tempo.cpp"
GLOBALS = FW / "system" / "globals.h"
EFFECT = FW / "effects" / "light_mode_waveform_tempo.cpp"
PIO = ROOT / "platformio.ini"


def test_profile_header_exists_and_declares_not_characterised():
    t = PROFILE.read_text(encoding="utf-8")
    assert "K1_AUDIO_PROFILE_NOT_CHARACTERISED" in t
    assert "K1_AUDIO_PROFILE_SPH0645" in t
    # IM73D must resolve to NOT_CHARACTERISED, never to a silent default.
    m = re.search(r"#if defined\(K1_MIC_IM73D_PDM_V1\)(.*?)#else", t, re.S)
    assert m and "K1_AUDIO_PROFILE_NOT_CHARACTERISED" in m.group(1)


def test_guard_fails_closed_without_an_explicit_acknowledgement():
    t = PROFILE.read_text(encoding="utf-8")
    assert "#error" in t, "the guard must be a hard compile error, not a warning"
    assert "K1_AUDIO_PROFILE_UNCHARACTERISED_ACK" in t
    # the #error must be reachable ONLY when the ack is absent
    assert re.search(
        r"!defined\(K1_AUDIO_PROFILE_UNCHARACTERISED_ACK\)", t
    ), "the error must be conditional on the ack being missing"


def test_globals_includes_the_guard_so_every_tu_compiles_it():
    assert "k1_audio_profile.h" in GLOBALS.read_text(encoding="utf-8"), (
        "globals.h must include the profile header, or the fail-closed #error "
        "never reaches the compiler for most translation units."
    )


@pytest.mark.parametrize("path,pattern,what", [
    (TEMPO,   r"K1_LOCK_CONFIDENCE\s*=\s*0\.28f",       "lock floor 0.28"),
    (TEMPO,   r"K1_CONF_V2_REL\s+0\.18f",               "lock-release 0.18"),
    (TEMPO,   r"novelty\s*\*\s*4\.0f",                  "novelty x4.0 boost"),
    (GLOBALS, r"K1_SILENCE_RMS_ENTER\s*=\s*0\.001f",    "silence RMS enter 0.001"),
    (GLOBALS, r"K1_SILENCE_RMS_EXIT\s*=\s*0\.003f",     "silence RMS exit 0.003"),
    (EFFECT,  r"lock_gate\s*<\s*0\.55f",                "effect lock-gate floor 0.55"),
])
def test_voided_constant_is_not_reinstated(path, pattern, what):
    assert not re.search(pattern, path.read_text(encoding="utf-8")), (
        f"{what} was tombstoned on 2026-08-11 — it was measured on Bench Unit 2 "
        "under a mic identity Captain correction 2026-08-10 voided. Do not "
        "reinstate it. Derive a new profile from first principles and add it to "
        "audio/k1_audio_profile.h. See "
        "docs/forensics/audio-profile/2026-08-11-im73d-profile-tombstone.md"
    )


def test_no_mic_gated_calibration_branches_remain_in_the_tempo_path():
    """The tempo/silence path must be mic-agnostic until a profile is derived."""
    for path in (TEMPO, EFFECT):
        assert "K1_MIC_IM73D_PDM_V1" not in path.read_text(encoding="utf-8"), (
            f"{path.name} must carry no mic-gated calibration branch. Mic "
            "PLUMBING (pin maps, driver mode, buffers) legitimately lives behind "
            "this macro elsewhere; CALIBRATION does not."
        )


def test_sph_reference_values_survive_unconditionally():
    t = TEMPO.read_text(encoding="utf-8")
    assert re.search(r"K1_LOCK_CONFIDENCE\s*=\s*0\.60f", t)
    assert re.search(r"K1_CONF_V2_REL\s+0\.42f", t)
    g = GLOBALS.read_text(encoding="utf-8")
    assert re.search(r"K1_SILENCE_RMS_ENTER\s*=\s*0\.04f", g)
    assert re.search(r"K1_SILENCE_RMS_EXIT\s*=\s*0\.08f", g)


def test_every_uncharacterised_env_declares_the_exposure():
    """An env defining the IM73D mic macro must ack, or its build cannot link."""
    text = PIO.read_text(encoding="utf-8")
    blocks = re.split(r"^\[env:", text, flags=re.M)[1:]
    for b in blocks:
        name = b.split("]", 1)[0]
        code = "\n".join(ln.split(";", 1)[0] for ln in b.splitlines())
        if "-DK1_MIC_IM73D_PDM_V1" in code:
            assert "-DK1_AUDIO_PROFILE_UNCHARACTERISED_ACK" in code, (
                f"[env:{name}] defines K1_MIC_IM73D_PDM_V1 but does not declare "
                "K1_AUDIO_PROFILE_UNCHARACTERISED_ACK — the build will fail "
                "closed at audio/k1_audio_profile.h, which is the intended "
                "behaviour. Declare the exposure or derive a profile."
            )


def test_production_sph_env_is_not_uncharacterised():
    """k1_hardware must never need the ack — it is the calibrated reference."""
    text = PIO.read_text(encoding="utf-8")
    m = re.search(r"^\[env:k1_hardware\]((?:(?!^\[).)*)", text, re.S | re.M)
    assert m
    code = "\n".join(ln.split(";", 1)[0] for ln in m.group(1).splitlines())
    assert "-DK1_MIC_IM73D_PDM_V1" not in code
    assert "-DK1_AUDIO_PROFILE_UNCHARACTERISED_ACK" not in code
