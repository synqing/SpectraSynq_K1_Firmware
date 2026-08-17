"""Ownership ratchet: Core-1 sources must not read live AP globals."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FW = ROOT / "SPECTRASYNQ_K1_FIRMWARE"

BANNED_IN_CORE1 = (
    "audio_semantic_read(",
    "k1_tempo_read(",
    "k1_onset_beat_read(",
    "k1_audio_snapshot_read(",
    "spectrogram[",
    "magnitudes_final[",
    "magnitudes_normalized[",
)

CORE1_DIRS = (
    FW / "effects",
    FW / "director",
    FW / "visual",
)


def _core1_sources() -> list[Path]:
    out: list[Path] = []
    for directory in CORE1_DIRS:
        if not directory.exists():
            continue
        out.extend(p for p in directory.rglob("*") if p.suffix in {".cpp", ".h", ".hpp"})
    return out


def test_core1_sources_never_read_live_ap_state():
    offenders: list[str] = []
    for path in _core1_sources():
        text = path.read_text(encoding="utf-8", errors="ignore")
        for banned in BANNED_IN_CORE1:
            start = 0
            while True:
                idx = text.find(banned, start)
                if idx < 0:
                    break
                # Allow VP-prefixed aliases (k1_vp_tempo_read, k1_vp_spectrogram[).
                prefix = text[max(0, idx - 7) : idx]
                if prefix.endswith("k1_vp_") or prefix.endswith("k1_vp"):
                    start = idx + len(banned)
                    continue
                offenders.append(f"{path.relative_to(ROOT)}: {banned}")
                break
    assert offenders == [], "\n".join(offenders)


def test_vp_bundle_does_not_reread_live_ap():
    text = (FW / "audio" / "k1_vp_audio_access.cpp").read_text(encoding="utf-8")
    assert "k1_tempo_read(" not in text
    assert "k1_onset_beat_read(" not in text
    assert "k1_audio_snapshot_read(" not in text
    assert "memcpy(k1_vp_spectrogram, spectrogram" not in text


def test_k1_hardware_enables_audio_frame_v1():
    pio = (ROOT / "platformio.ini").read_text(encoding="utf-8")
    start = pio.index("[env:k1_hardware]\n")
    end = pio.find("\n[env:", start + 1)
    section = pio[start:end if end >= 0 else len(pio)]
    assert "-DK1_AUDIO_FRAME_V1=1" in section


def test_host_shim_is_not_referenced_by_production_sources():
    # Production TUs must not include the host shim header.
    offenders = []
    for path in (FW / "audio").glob("*.cpp"):
        text = path.read_text(encoding="utf-8")
        if "k1_audio_frame_host_shim.h" in text and "K1_AUDIO_FRAME_HOST_TEST" not in text:
            offenders.append(str(path.relative_to(ROOT)))
    # k1_audio_frame.cpp includes the shim only under the host-test else branch.
    frame = (FW / "audio" / "k1_audio_frame.cpp").read_text(encoding="utf-8")
    assert "k1_audio_frame_host_shim.h" in frame
    assert "#else" in frame
    assert offenders == []
