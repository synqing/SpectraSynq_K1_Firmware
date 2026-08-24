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

    def test_usb_underflow_first_miss_emits_ramp_not_pcm_replay(self):
        """First underflow: tail-to-zero ramp from s_hold when s_hold_valid.
        Second+ underflow: zeros. No full PCM replay (would fabricate 133 Hz)."""
        self.assertIn("s_hold_valid", USB_CPP)
        self.assertIn("pdMS_TO_TICKS(20)", USB_CPP)
        take = USB_CPP.split("void k1_usb_audio_take_canonical_samples", 1)[1]
        take = take.split("void k1_usb_audio_poll_telemetry", 1)[0]
        underflow = take.split("s_underflows++", 1)[1]
        # Must check consecutive count before emitting ramp.
        self.assertIn("s_consecutive_underflows == 0", underflow)
        # Ramp: linear fade from s_hold[] into out96[].
        self.assertIn("s_hold[i]", underflow)
        # Hold invalidated after one conceal — conceal budget consumed.
        self.assertIn("s_hold_valid = false", underflow)
        # Second+ underflow must fall through to zeros.
        self.assertIn("memset(out96, 0", underflow)
        # s_consecutive_underflows must increment.
        self.assertIn("s_consecutive_underflows++", underflow)

    def test_usb_underflow_hold_is_not_full_pcm_replay(self):
        """The ramp must not emit memcpy(out96, s_hold) verbatim — that
        would fabricate a 133.33 Hz periodic signal on sustained underflow."""
        take = USB_CPP.split("void k1_usb_audio_take_canonical_samples", 1)[1]
        take = take.split("void k1_usb_audio_poll_telemetry", 1)[0]
        underflow = take.split("s_underflows++", 1)[1]
        # Full-hop verbatim replay MUST NOT appear in the underflow branch.
        # (The ramp loop replaces it with a linear fade.)
        self.assertNotIn("memcpy(out96, s_hold", underflow)

    def test_usb_gen_bump_invalidates_hold(self):
        """Disconnect / suspend / rate change must clear s_hold_valid so
        resume does not emit stale PCM from a prior generation."""
        bump = USB_CPP.split("static void k1_usb_bump_generation()", 1)[1]
        bump = bump.split("static void k1_usb_record_age", 1)[0]
        self.assertIn("s_hold_valid = false", bump)
        self.assertIn("s_consecutive_underflows = 0", bump)

    def test_usb_inactive_path_does_not_clear_hold(self):
        """Inactive (stream not valid) path emits zeros but must not
        clear s_hold_valid — hold clearing belongs in gen-bump."""
        take = USB_CPP.split("void k1_usb_audio_take_canonical_samples", 1)[1]
        take = take.split("void k1_usb_audio_poll_telemetry", 1)[0]
        inactive = take.split("if (!k1_usb_stream_valid())", 1)[1]
        inactive = inactive.split("s_inactive_pacer_inited", 1)[0]
        self.assertIn("memset(out96, 0", inactive)
        self.assertNotIn("s_hold_valid = false", inactive)

    def test_usb_good_frame_resets_consecutive_underflow_count(self):
        """A successfully consumed frame must reset s_consecutive_underflows
        so the next single missed hop re-activates the ramp conceal."""
        take = USB_CPP.split("void k1_usb_audio_take_canonical_samples", 1)[1]
        take = take.split("void k1_usb_audio_poll_telemetry", 1)[0]
        # Reset must appear AFTER the underflow early-return block.
        after_underflow = take.split("s_consecutive_underflows++;", 1)[1]
        self.assertIn("s_consecutive_underflows = 0", after_underflow)

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

    def test_usb_agc_loudness_norm_written_from_digital_peak(self):
        """USB branch in acquire_sample_chunk must write agc_loudness_norm from
        the digital peak of the canonical hop (NOT mic IM69 raw RMS, NOT SSL).
        Guard must be #ifdef K1_STM (the variable lives there).
        EdgeMixer STM reads agc_loudness_norm; leaving it 0 kills USB modulation."""
        self.assertIn("agc_loudness_norm", I2S)
        # Must be inside a K1_STM guard in i2s_audio.h (the variable is conditional).
        self.assertIn("#ifdef K1_STM", I2S)
        # Must use max_waveform_val_raw (digital peak), not mic raw RMS.
        stm_block = I2S.split("#ifdef K1_STM", 1)[1]
        self.assertIn("max_waveform_val_raw", stm_block)
        self.assertIn("agc_loudness_norm", stm_block)
        self.assertNotIn("im69d_raw_i16_rms", stm_block.split("#endif", 1)[0])
        self.assertNotIn("im73d_raw_i16_rms", stm_block.split("#endif", 1)[0])

    def test_usb_force_present_diagnostic_flag_gates_silence_override(self):
        """silence=false must be guarded by K1_USB_FORCE_PRESENT_DIAGNOSTIC
        so production builds are not affected by the diagnostic bypass."""
        self.assertIn("K1_USB_FORCE_PRESENT_DIAGNOSTIC", INGRESS)
        # The flag must gate the silence=false assignment.
        diag_block = INGRESS.split("K1_USB_FORCE_PRESENT_DIAGNOSTIC", 1)[1]
        self.assertIn("silence = false", diag_block)

    def test_mic_tail_strings_remain_for_production_gain_gate(self):
        self.assertIn("waveform[i] = sample - CONFIG.DC_OFFSET;", I2S)
        self.assertIn("sample_window[i] = audio_response_gain_apply_sample", I2S)
        self.assertIn("waveform_fixed_point[i] = SQ15x16(audio_response_gain_apply_sample", I2S)
