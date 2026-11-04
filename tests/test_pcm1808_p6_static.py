"""P6 Line-In canonicalisation remains probe-only and source-explicit."""
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
PIO = (ROOT / "platformio.ini").read_text()
CPP = (ROOT / "SPECTRASYNQ_K1_FIRMWARE/audio/k1_pcm1808_input.cpp").read_text()
HDR = (ROOT / "SPECTRASYNQ_K1_FIRMWARE/audio/k1_pcm1808_input.h").read_text()

def test_p6_env_is_probe_only_mid_minus24db():
    block = PIO.split("[env:k1_main_rpl_pcm1808_p6_probe]",1)[1].split("[env:",1)[0]
    assert "extends = env:k1_main_rpl_pcm1808_line_p5_probe" in block
    assert "-DK1_PCM1808_MONO_POLICY=K1_PCM1808_MONO_MID" in block
    assert "-DK1_PCM1808_CANON_TRIM_Q15=2048" in block
    product = PIO.split("[env:k1_main_rpl_im69d]",1)[1].split("[env:",1)[0]
    assert "K1_PCM1808_MONO_POLICY" not in product
    assert "K1_PCM1808_CANON_TRIM_Q15" not in product

def test_policy_names_physical_channels_without_dma_swap():
    assert "k1_pcm_physical_left(slot0, slot1)" in CPP
    assert "k1_pcm_physical_mid(slot0, slot1)" in CPP
    assert "k1_pcm_physical_right(slot0, slot1)" in CPP
    assert "k1_pcm1808_unpack_le24(fr)" in CPP
    assert "k1_pcm1808_unpack_le24(fr + 3)" in CPP

def test_canonical_trim_is_bounded_and_observable():
    assert "K1_PCM1808_CANON_TRIM_Q15 32768" in HDR
    assert "K1_PCM1808_CANON_TRIM_Q15 < 1" in HDR
    assert "k1_pcm1808_apply_canon_trim" in CPP
    assert "[PCMCAN]" in CPP
