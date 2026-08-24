"""USB canonical samples must not take the microphone conditioning path."""

from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FW = ROOT / "SPECTRASYNQ_K1_FIRMWARE"
USB_CPP = (FW / "audio" / "k1_usb_audio_input.cpp").read_text(encoding="utf-8")
INGRESS = (FW / "audio" / "k1_audio_ingress.h").read_text(encoding="utf-8")
I2S = (FW / "audio" / "i2s_audio.h").read_text(encoding="utf-8")
ASSEMBLER = (FW / "audio" / "k1_usb_pcm_assembler.h").read_text(encoding="utf-8")


class UsbAudioSampleDomainTest(unittest.TestCase):
    def test_usb_tu_does_not_apply_mic_conditioning(self):
        self.assertNotIn("K1_MIC_IM69D_INPUT_GAIN", USB_CPP)
        self.assertNotIn("CONFIG.DC_OFFSET", USB_CPP)
        self.assertNotIn("CONFIG.SENSITIVITY", USB_CPP)
        self.assertNotIn("k1_loud_guard", USB_CPP)
        self.assertNotIn("k1_mic_health", USB_CPP)
        self.assertNotIn("k1_mic_auto_sense", USB_CPP)
        self.assertNotIn("applyVolume", USB_CPP)
        self.assertNotIn("i2s_audio.h", USB_CPP)

    def test_usb_commit_helper_has_no_im69_or_dc(self):
        self.assertNotIn("K1_MIC_IM69D_INPUT_GAIN", INGRESS)
        self.assertNotIn("CONFIG.DC_OFFSET", INGRESS)
        self.assertNotIn("CONFIG.SENSITIVITY", INGRESS)
        self.assertIn("k1_audio_commit_canonical_frame", INGRESS)
        self.assertIn("audio_response_gain_apply_sample", INGRESS)

    def test_usb_commit_runs_waveform_peak_envelope(self):
        self.assertIn("k1_usb_update_waveform_peak_envelope", INGRESS)
        self.assertIn("waveform_peak_scaled", INGRESS)
        self.assertIn("max_waveform_val_follower", INGRESS)
        self.assertIn("CONFIG.SWEET_SPOT_MIN_LEVEL = 0", INGRESS)

    def test_usb_underflow_holds_last_frame_instead_of_zeros(self):
        self.assertIn("s_hold_valid", USB_CPP)
        self.assertIn("pdMS_TO_TICKS(20)", USB_CPP)
        self.assertIn("memcpy(out96, s_hold", USB_CPP)
        take = USB_CPP.split("void k1_usb_audio_take_canonical_samples", 1)[1]
        take = take.split("void k1_usb_audio_poll_telemetry", 1)[0]
        underflow = take.split("s_underflows++", 1)[1]
        self.assertIn("s_hold_valid", underflow)
        self.assertIn("memcpy(out96, s_hold", underflow)
        # Zeros remain only as the cold-start fallback before any live hop.

    def test_usb_acquire_is_early_return_before_i2s_read(self):
        acquire_idx = I2S.index("void acquire_sample_chunk")
        usb_idx = I2S.index("k1_usb_audio_take_canonical_samples", acquire_idx)
        commit_idx = I2S.index("k1_audio_commit_canonical_frame", acquire_idx)
        read_idx = I2S.index("i2s_channel_read", acquire_idx)
        self.assertLess(usb_idx, commit_idx)
        self.assertLess(commit_idx, read_idx)
        self.assertIn("#if K1_AUDIO_SOURCE_USB", I2S)

    def test_assembler_is_endian_neutral_memcpy(self):
        self.assertIn("memcpy(a->buf + a->filled, src, take)", ASSEMBLER)
        self.assertNotIn("ntohs", ASSEMBLER)
        self.assertNotIn("__builtin_bswap", ASSEMBLER)

    def test_mic_tail_strings_remain_for_production_gain_gate(self):
        self.assertIn("waveform[i] = sample - CONFIG.DC_OFFSET;", I2S)
        self.assertIn("sample_window[i] = audio_response_gain_apply_sample", I2S)
        self.assertIn("waveform_fixed_point[i] = SQ15x16(audio_response_gain_apply_sample", I2S)
