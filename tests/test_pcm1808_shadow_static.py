"""P4 shadow dual-capture contract. Host-only; does not claim silicon."""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PLATFORMIO = (ROOT / "platformio.ini").read_text(encoding="utf-8")
PIO_BUILD = (ROOT / "scripts" / "agent" / "pio-build.sh").read_text(encoding="utf-8")
IDENT = (ROOT / "scripts" / "platformio" / "k1_device_identities.json").read_text(
    encoding="utf-8"
)
SOURCE = (ROOT / "SPECTRASYNQ_K1_FIRMWARE" / "audio" / "k1_audio_source.h").read_text(
    encoding="utf-8"
)
CPP = (ROOT / "SPECTRASYNQ_K1_FIRMWARE" / "audio" / "k1_pcm1808_input.cpp").read_text(
    encoding="utf-8"
)
HDR = (ROOT / "SPECTRASYNQ_K1_FIRMWARE" / "audio" / "k1_pcm1808_input.h").read_text(
    encoding="utf-8"
)
I2S = (ROOT / "SPECTRASYNQ_K1_FIRMWARE" / "audio" / "i2s_audio.h").read_text(
    encoding="utf-8"
)
MENU = (ROOT / "SPECTRASYNQ_K1_FIRMWARE" / "serial" / "serial_menu.cpp").read_text(
    encoding="utf-8"
)
TABLE = (
    ROOT / "SPECTRASYNQ_K1_FIRMWARE" / "serial" / "serial_typed_cmd_table.def"
).read_text(encoding="utf-8")
INO = (ROOT / "SPECTRASYNQ_K1_FIRMWARE" / "SPECTRASYNQ_K1_FIRMWARE.ino").read_text(
    encoding="utf-8"
)


def _env_block(env_name: str) -> str:
    match = re.search(rf"\[env:{re.escape(env_name)}\](.*?)(?=\n\[env:|\Z)", PLATFORMIO, flags=re.S)
    assert match, f"missing [env:{env_name}]"
    return match.group(1)


def test_shadow_env_keeps_mic_as_ap_source() -> None:
    shadow = _env_block("k1_main_rpl_pcm1808_shadow")
    assert "extends = env:k1_main_rpl_im69d" in shadow
    assert "-DK1_PCM1808_SHADOW=1" in shadow
    assert "-DK1_PCM1808_PROBE_V1" in shadow
    assert "-DK1_AUDIO_SOURCE_PCM1808=1" not in shadow
    assert "-DK1_AUDIO_SOURCE_MIC=0" not in shadow
    assert "+<audio/k1_pcm1808_input.cpp>" in shadow
    assert "-DDEFAULT_SAMPLE_RATE=48000" not in shadow


def test_production_envs_do_not_enable_shadow() -> None:
    hw = _env_block("k1_hardware")
    rpl = _env_block("k1_main_rpl_im69d")
    probe = _env_block("k1_main_rpl_pcm1808_probe")
    assert "-DK1_PCM1808_SHADOW=1" not in hw
    assert "-DK1_PCM1808_SHADOW=1" not in rpl
    assert "-DK1_PCM1808_SHADOW=1" not in probe


def test_shadow_registered_on_main_rpl_chip_only() -> None:
    assert "k1_main_rpl_pcm1808_shadow" in IDENT
    assert "k1_main_rpl_pcm1808_shadow" in PIO_BUILD
    assert "k1_main_rpl_pcm1808_shadow" not in _env_block("k1_hardware")


def test_shadow_flag_cannot_own_ingress() -> None:
    assert "K1_PCM1808_SHADOW cannot share a build with PCM1808 ingress ownership" in SOURCE
    assert "K1_PCM1808_SHADOW requires the microphone to remain the AP source" in SOURCE
    assert "K1_PCM1808_PRESENT" in SOURCE
    assert "microphone and PCM1808 capture cannot both own ingress" in SOURCE


def test_pair_dump_refuses_while_epoch_armed() -> None:
    dump = CPP.split("static void k1_pcmpair_dump", 1)[1].split("bool k1_pcm1808_dispatch", 1)[0]
    assert "DUMP REFUSED" in dump
    assert "epoch still armed" in dump
    assert "s_raw_dumping = 1" in dump
    # serialisation is after the refuse-if-armed guard
    assert dump.find("DUMP REFUSED") < dump.find("s_raw_dumping = 1")


def test_pair_fill_ok_requires_ovf_and_drop_zero() -> None:
    assert "ovf_epoch == 0 && drop_epoch == 0" in CPP
    assert "s_pair_end_mic_err == 0" in CPP
    assert "fill_ok=" in CPP


def test_pair_commands_reach_parse_command_ladder() -> None:
    parse = MENU[MENU.find("parse_command") :]
    m = re.search(r"#ifdef\s+K1_PCM1808_PROBE_V1\s*\n(.*?)#endif", parse, re.S)
    assert m, "parse_command must carry a K1_PCM1808_PROBE_V1-gated hop"
    assert "k1_pcm1808_dispatch(command_type, command_data)" in m.group(1)
    for cmd in ("pcmpair_arm", "pcmpair_status", "pcmpair_dump"):
        assert f'SERIAL_TYPED_CMD("{cmd}"' in TABLE
        assert f'strcmp(command_type, "{cmd}")' in CPP


def test_mic_tap_is_before_gain() -> None:
    assert "k1_pcm1808_pair_note_mic" in I2S
    assert "k1_pcm1808_shadow_drain" in I2S
    tap_at = I2S.find("k1_pcm1808_pair_note_mic")
    gain_at = I2S.find("K1_MIC_IM69D_INPUT_GAIN")
    assert tap_at > 0 and gain_at > tap_at


def test_shadow_drain_does_not_feed_ap() -> None:
    assert "k1_pcm1808_shadow_drain" in HDR
    drain = CPP.split("void k1_pcm1808_shadow_drain", 1)[1].split("void k1_pcm1808_pair_hop_begin", 1)[0]
    assert "k1_pcm_ring_discard" in drain
    assert "k1_audio_commit_canonical_frame" not in drain
    assert "take_canonical_samples" not in drain


def test_hop_end_is_after_gdft() -> None:
    gdft = INO.find("process_GDFT();")
    hop = INO.find("k1_pcm1808_pair_hop_end();")
    assert gdft > 0 and hop > gdft


def test_pair_cap_is_bounded() -> None:
    assert "K1_PCMPAIR_MAX_MS = 4000" in CPP
    assert "ps_malloc" in CPP
    assert "store=PSRAM" in CPP


def test_pair_decoder_roundtrip_and_refuses_armed_dump() -> None:
    sys_path_note = str(ROOT / "tools" / "pcm1808")
    import sys

    sys.path.insert(0, sys_path_note)
    from p4_pair_decode import decode_text  # noqa: E402

    pcm = bytes([0x01, 0x00, 0x00, 0x02, 0x00, 0x00])  # slot0=1, slot1=2
    mic = bytes([0x03, 0x00])  # int16 3
    hop = bytes([0xE8, 0x03])  # 1000 us
    def hx(b: bytes) -> str:
        return b.hex()

    dump = (
        "[PCMPAIR-BEGIN] epoch_valid=1 fill_ok=1 ovf_epoch=0 ring_drop_epoch=0 "
        "mic_err_epoch=0 dur_us=4000000 pcm_frames=1 mic_samples=1 hop_n=1 "
        "hop_mean=1000 hop_p95=1000 hop_p99=1000 hop_max=1000 cap_read_us=10 "
        "slot0=RIGHT slot1=LEFT ap_source=im69d mic_only=0 fixture=selftest\n"
        f"[PCMPAIR-PCM bytes=6 crc32={__import__('zlib').crc32(pcm) & 0xFFFFFFFF:08x} sr=48000 fmt=le24_s0s1]\n"
        f"{hx(pcm)}\n"
        "[PCMPAIR-PCM-END]\n"
        f"[PCMPAIR-MIC bytes=2 crc32={__import__('zlib').crc32(mic) & 0xFFFFFFFF:08x} sr=12800 fmt=s16le pre_gain=1]\n"
        f"{hx(mic)}\n"
        "[PCMPAIR-MIC-END]\n"
        "[PCMPAIR-HOP bytes=2 n=1 fmt=u16le_us]\n"
        f"{hx(hop)}\n"
        "[PCMPAIR-HOP-END]\n"
        "[PCMPAIR-END]\n"
    )
    d = decode_text(dump)
    assert d["clean"] is True
    assert d["slot0"] == [1]
    assert d["slot1"] == [2]
    assert d["mic"] == [3]
    assert d["hops_us"] == [1000]
    try:
        decode_text("[PCMPAIR] DUMP REFUSED: epoch still armed — freeze first\n")
        raise AssertionError("refused dump must not decode")
    except SystemExit:
        pass
