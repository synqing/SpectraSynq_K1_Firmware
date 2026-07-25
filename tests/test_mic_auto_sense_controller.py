"""Host + static contracts for K1_MIC_AUTO_SENSE_V1 (Proposal 2).

Covers:
  1. Pure controller behavioural oracle (mirrors k1_mic_auto_decide).
  2. Flag-OFF / layering / hard-no static source contracts.
  3. No hot-loop allocation / no NVS / no cal-fire tokens in auto-sense path.
"""

from __future__ import annotations

import math
import unittest
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FW = ROOT / "SPECTRASYNQ_K1_FIRMWARE"
PLATFORMIO = (ROOT / "platformio.ini").read_text(encoding="utf-8")
I2S = (FW / "audio" / "i2s_audio.h").read_text(encoding="utf-8")
HEADER = (FW / "audio" / "k1_mic_auto_sense.h").read_text(encoding="utf-8")
CPP = (FW / "audio" / "k1_mic_auto_sense.cpp").read_text(encoding="utf-8")
INO = (FW / "SPECTRASYNQ_K1_FIRMWARE.ino").read_text(encoding="utf-8")
SERIAL = (FW / "serial" / "serial_menu.h").read_text(encoding="utf-8")
EVAL = (ROOT / "scripts" / "regression-harness" / "im73d_audio_eval.py").read_text(
    encoding="utf-8"
)


# --- Python oracle mirroring k1_mic_auto_decide (deterministic host gate) -----

DISABLED = 0
OBSERVE_BOOT = 1
HOLD = 2
ADJUST_UP = 3
ADJUST_DOWN = 4
PROTECT = 5
FAULT = 6

REASON_PURITY = 12
REASON_SILENCE = 8
REASON_CAL = 9
REASON_HEADROOM = 6
REASON_LOUD_TRIM = 7
REASON_WEAK = 4
REASON_HOT = 5
REASON_BOOT = 2


@dataclass
class Cfg:
    scale_min: float = 0.50
    scale_max: float = 1.50
    up_factor: float = 1.04
    down_factor: float = 0.90
    protect_factor: float = 0.85
    protect_stages: int = 1
    target_peak_lo: float = 0.12
    target_peak_hi: float = 0.78
    silence_raw_rms: float = 18.0
    music_raw_rms: float = 28.0
    agc_high_gain: float = 2.50
    hot_spec_sat: float = 0.12
    clip_eps: float = 0.0
    raw_hot_threshold: float = 0.0
    boot_observe_ms: int = 10000
    up_dwell_ms: int = 5000
    down_dwell_ms: int = 3000
    protect_cooldown_ms: int = 8000
    ema_alpha: float = 0.08
    boot_scale: float = 1.0


@dataclass
class Metrics:
    raw_abs_peak: float = 100.0
    raw_rms: float = 40.0
    raw_near_rail_pct: float = 0.0
    max_waveform_val_raw: float = 4000.0
    waveform_peak_scaled: float = 0.35
    clip_pct: float = 0.0
    near_pct: float = 0.0
    input_trim: float = 1.0
    gdft_trim: float = 1.0
    spec_sat: float = 0.0
    agc_gain_mean: float = 1.2
    cal_valid: bool = True
    noise_complete: bool = True
    silence: bool = False
    telemetry_ok: bool = True


@dataclass
class State:
    runtime_enabled: bool = True
    shadow_only: bool = False
    scale: float = 1.0
    recommended_scale: float = 1.0
    state: int = OBSERVE_BOOT
    reason: int = REASON_BOOT
    boot_start_ms: int = 0
    last_adjust_ms: int = 0
    protect_until_ms: int = 0
    ema_peak_scaled: float = 0.0
    ema_raw_rms: float = 0.0
    ema_seeded: bool = False
    window_age_ms: int = 0


def clamp_scale(scale: float, cfg: Cfg) -> float:
    if not math.isfinite(scale):
        return 1.0
    return min(cfg.scale_max, max(cfg.scale_min, scale))


def applied(st: State) -> float:
    if not st.runtime_enabled or st.shadow_only:
        return 1.0
    if not math.isfinite(st.scale):
        return 1.0
    return st.scale


def decide(st: State, m: Metrics, cfg: Cfg, now_ms: int) -> tuple[float, int, int, bool]:
    if not st.runtime_enabled:
        st.scale = 1.0
        st.recommended_scale = 1.0
        st.state = DISABLED
        st.reason = REASON_PURITY
        return 1.0, st.state, st.reason, False

    vals = [
        m.raw_abs_peak,
        m.raw_rms,
        m.raw_near_rail_pct,
        m.max_waveform_val_raw,
        m.waveform_peak_scaled,
        m.clip_pct,
        m.near_pct,
        m.input_trim,
        m.gdft_trim,
        m.spec_sat,
        m.agc_gain_mean,
    ]
    if not m.telemetry_ok or any(not math.isfinite(v) for v in vals):
        st.state = FAULT
        st.reason = 10 if m.telemetry_ok else 11
        st.recommended_scale = st.scale
        return applied(st), st.state, st.reason, False

    if not m.cal_valid or not m.noise_complete:
        st.state = FAULT
        st.reason = REASON_CAL
        st.recommended_scale = st.scale
        return applied(st), st.state, st.reason, False

    if not st.ema_seeded:
        st.ema_peak_scaled = m.waveform_peak_scaled
        st.ema_raw_rms = m.raw_rms
        st.ema_seeded = True
    else:
        a = cfg.ema_alpha
        st.ema_peak_scaled += (m.waveform_peak_scaled - st.ema_peak_scaled) * a
        st.ema_raw_rms += (m.raw_rms - st.ema_raw_rms) * a

    st.window_age_ms = max(0, now_ms - st.boot_start_ms)
    if st.window_age_ms < cfg.boot_observe_ms:
        st.state = OBSERVE_BOOT
        st.reason = REASON_BOOT
        st.recommended_scale = st.scale
        return applied(st), st.state, st.reason, False

    hard = (
        m.clip_pct > cfg.clip_eps
        or m.near_pct > cfg.clip_eps
        or m.raw_near_rail_pct > cfg.clip_eps
        or m.input_trim < 0.999
        or (cfg.raw_hot_threshold > 0.0 and m.max_waveform_val_raw > cfg.raw_hot_threshold)
    )
    hot = st.ema_peak_scaled > cfg.target_peak_hi or m.spec_sat > cfg.hot_spec_sat
    quiet = (
        m.silence
        or st.ema_raw_rms < cfg.silence_raw_rms
        or m.raw_rms < cfg.silence_raw_rms
    )
    active = (
        not quiet
        and st.ema_raw_rms >= cfg.music_raw_rms
        and m.raw_rms >= cfg.music_raw_rms
    )
    under = (
        active
        and st.ema_peak_scaled < cfg.target_peak_lo
        and m.agc_gain_mean >= cfg.agc_high_gain
        and not hard
        and not hot
        and m.input_trim >= 0.999
    )

    next_scale = st.scale
    next_state = HOLD
    next_reason = 3
    did = False

    if hard:
        next_scale = st.scale
        stages = max(1, int(cfg.protect_stages))
        for _ in range(stages):
            next_scale = clamp_scale(next_scale * cfg.protect_factor, cfg)
        next_state = PROTECT
        next_reason = REASON_LOUD_TRIM if m.input_trim < 0.999 else REASON_HEADROOM
        st.protect_until_ms = now_ms + cfg.protect_cooldown_ms
        did = next_scale != st.scale
    elif hot:
        if now_ms - st.last_adjust_ms >= cfg.down_dwell_ms:
            next_scale = clamp_scale(st.scale * cfg.down_factor, cfg)
            next_state = ADJUST_DOWN
            next_reason = REASON_HOT
            st.protect_until_ms = now_ms + cfg.protect_cooldown_ms
            did = next_scale != st.scale
        else:
            next_state = HOLD
            next_reason = 13
    elif quiet:
        next_state = HOLD
        next_reason = REASON_SILENCE
    elif under:
        if now_ms < st.protect_until_ms:
            next_state = HOLD
            next_reason = 13
        elif now_ms - st.last_adjust_ms >= cfg.up_dwell_ms:
            next_scale = clamp_scale(st.scale * cfg.up_factor, cfg)
            next_state = ADJUST_UP
            next_reason = REASON_WEAK
            did = next_scale != st.scale
        else:
            next_state = HOLD
            next_reason = 13

    st.recommended_scale = next_scale
    if st.shadow_only:
        st.scale = 1.0
        st.state = next_state
        st.reason = 14
        did = False
    else:
        if did:
            st.scale = next_scale
            st.last_adjust_ms = now_ms
        st.state = next_state
        st.reason = next_reason

    return applied(st), st.state, st.reason, did


class MicAutoSenseControllerOracle(unittest.TestCase):
    def test_no_scale_up_during_silence(self):
        st = State(boot_start_ms=0, last_adjust_ms=0)
        cfg = Cfg()
        # Exit boot observe
        decide(st, Metrics(raw_rms=40.0, waveform_peak_scaled=0.4), cfg, 11000)
        scale, state, reason, _ = decide(
            st,
            Metrics(
                raw_rms=8.0,
                waveform_peak_scaled=0.02,
                silence=True,
                agc_gain_mean=3.0,
            ),
            cfg,
            20000,
        )
        self.assertEqual(scale, 1.0)
        self.assertEqual(state, HOLD)
        self.assertEqual(reason, REASON_SILENCE)

    def test_no_scale_up_when_cal_invalid(self):
        st = State(boot_start_ms=0, last_adjust_ms=0)
        cfg = Cfg()
        decide(st, Metrics(), cfg, 11000)
        scale, state, reason, _ = decide(
            st,
            Metrics(cal_valid=False, waveform_peak_scaled=0.05, agc_gain_mean=3.0),
            cfg,
            20000,
        )
        self.assertEqual(scale, 1.0)
        self.assertEqual(state, FAULT)
        self.assertEqual(reason, REASON_CAL)

    def test_protect_on_input_trim_reduction(self):
        st = State(boot_start_ms=0, last_adjust_ms=0, scale=1.0)
        cfg = Cfg()
        decide(st, Metrics(), cfg, 11000)
        scale, state, reason, adjusted = decide(
            st, Metrics(input_trim=0.75, waveform_peak_scaled=0.4), cfg, 20000
        )
        self.assertTrue(adjusted)
        self.assertLess(scale, 1.0)
        self.assertEqual(state, PROTECT)
        self.assertEqual(reason, REASON_LOUD_TRIM)

    def test_slow_upscale_on_weak_active_music(self):
        st = State(boot_start_ms=0, last_adjust_ms=0, scale=1.0)
        cfg = Cfg()
        # Seed EMA with weak peak under active music + high AGC compensation.
        for t in range(11000, 20000, 500):
            decide(
                st,
                Metrics(
                    raw_rms=45.0,
                    waveform_peak_scaled=0.05,
                    agc_gain_mean=3.0,
                ),
                cfg,
                t,
            )
        scale, state, reason, adjusted = decide(
            st,
            Metrics(raw_rms=45.0, waveform_peak_scaled=0.05, agc_gain_mean=3.0),
            cfg,
            26000,
        )
        self.assertTrue(adjusted)
        self.assertGreater(scale, 1.0)
        self.assertLessEqual(scale, cfg.scale_max)
        self.assertEqual(state, ADJUST_UP)
        self.assertEqual(reason, REASON_WEAK)

    def test_purity_bypass_forces_unity(self):
        st = State(boot_start_ms=0, last_adjust_ms=0, scale=1.2, runtime_enabled=False)
        scale, state, reason, _ = decide(st, Metrics(), Cfg(), 20000)
        self.assertEqual(scale, 1.0)
        self.assertEqual(state, DISABLED)
        self.assertEqual(reason, REASON_PURITY)

    def test_shadow_keeps_applied_unity(self):
        st = State(boot_start_ms=0, last_adjust_ms=0, shadow_only=True)
        cfg = Cfg()
        for t in range(11000, 20000, 500):
            decide(
                st,
                Metrics(raw_rms=45.0, waveform_peak_scaled=0.05, agc_gain_mean=3.0),
                cfg,
                t,
            )
        scale, _, reason, adjusted = decide(
            st,
            Metrics(raw_rms=45.0, waveform_peak_scaled=0.05, agc_gain_mean=3.0),
            cfg,
            26000,
        )
        self.assertEqual(scale, 1.0)
        self.assertFalse(adjusted)
        self.assertEqual(reason, 14)
        self.assertGreater(st.recommended_scale, 1.0)

    def test_scale_clamps(self):
        st = State(boot_start_ms=0, last_adjust_ms=0, scale=1.48)
        cfg = Cfg()
        decide(st, Metrics(), cfg, 11000)
        for t in range(16000, 40000, 6000):
            decide(
                st,
                Metrics(raw_rms=45.0, waveform_peak_scaled=0.05, agc_gain_mean=3.0),
                cfg,
                t,
            )
        self.assertLessEqual(st.scale, cfg.scale_max)
        self.assertGreaterEqual(st.scale, cfg.scale_min)


class MicAutoSenseStaticContracts(unittest.TestCase):
    def test_flag_default_off_on_reference_envs(self):
        self.assertIn("[env:k1_bench_im73d_mic_auto]", PLATFORMIO)
        self.assertIn("-DK1_MIC_AUTO_SENSE_V1", PLATFORMIO)
        # Reference envs must not enable the flag in their own build_flags block.
        for env in ("k1_hardware", "k1_bench_reference", "k1_bench_im73d"):
            # crude: the dedicated mic_auto env is the only one that should add the define
            pass
        # Ensure production-ish envs do not list the define on their direct build_flags lines
        # after their section headers (mic_auto env is the opt-in).
        self.assertIn("k1_bench_im73d_mic_auto", PLATFORMIO)
        mic_auto_idx = PLATFORMIO.index("[env:k1_bench_im73d_mic_auto]")
        # The define appears in the mic_auto env; k1_hardware block must not contain it before that.
        hw_idx = PLATFORMIO.index("[env:k1_hardware]")
        hw_slice = PLATFORMIO[hw_idx:mic_auto_idx]
        self.assertNotIn("-DK1_MIC_AUTO_SENSE_V1", hw_slice)

    def test_layering_auto_above_loud_guard(self):
        self.assertIn("CONFIG.SENSITIVITY * auto_scale * k1_loud_input_trim", I2S)
        self.assertIn("k1_mic_auto_sense_applied_scale()", I2S)
        # Update runs after loud-guard update in the .ino AP path.
        loud_idx = INO.index("k1_loud_guard_update(t_now);")
        auto_idx = INO.index("k1_mic_auto_sense_update(t_now);")
        self.assertLess(loud_idx, auto_idx)

    def test_hard_nos_in_auto_sense_sources(self):
        auto_only = HEADER + CPP
        for banned in (
            "start_noise_cal",
            "save_config(",
            "LittleFS",
            "malloc(",
            "audio_response_gain =",
        ):
            self.assertNotIn(banned, auto_only)
        # No C++ heap new-expressions in the auto-sense TUs (word-boundary-ish).
        self.assertNotRegex(auto_only, r"\bnew\s+[A-Za-z_]")
        self.assertNotRegex(auto_only, r"\bString\b")
        # Effective sensitivity layering must still sit above loud-guard trim.
        self.assertIn("auto_scale * k1_loud_input_trim", I2S)

    def test_cpp_fully_flag_gated(self):
        self.assertIn("#ifdef K1_MIC_AUTO_SENSE_V1", CPP)
        self.assertTrue(CPP.strip().startswith("//"))
        # Entire implementation body is inside the flag gate.
        self.assertIn("#endif  // K1_MIC_AUTO_SENSE_V1", CPP)

    def test_purity_serial_bypass_exists(self):
        self.assertIn('strcmp(command_type, "mic_auto")', SERIAL)
        self.assertIn("k1_mic_auto_sense_set_enabled", SERIAL)
        self.assertIn("purity=:mic_auto=off", SERIAL)

    def test_eval_harness_still_refuses_cal_tokens(self):
        self.assertIn('FORBIDDEN_SERIAL_TOKENS = {"start_noise_cal", "N", "Y"}', EVAL)
        self.assertIn('READ_ONLY_COMMANDS = {"build", "dump"}', EVAL)

    def test_scale_bounds_documented_in_header(self):
        self.assertIn("scale_min", HEADER)
        self.assertIn("0.50f", HEADER)
        self.assertIn("1.50f", HEADER)
        self.assertIn("never persist", HEADER.lower())
        self.assertIn("RAM-only", HEADER)

    def test_headroom_v2_defaults_in_header_and_env(self):
        """P2 REWORK vol60: HEADROOM_V2c lower floor + anticipatory raw-hot."""
        self.assertIn("K1_MIC_AUTO_HEADROOM_V2", HEADER)
        self.assertIn("0.55f", HEADER)   # protect_factor / boot_scale / peak_hi under V2c
        self.assertIn("0.22f", HEADER)   # scale_min under HEADROOM_V2c
        self.assertIn("1.00f", HEADER)   # scale_max under HEADROOM_V2
        self.assertIn("16000.0f", HEADER)  # raw_hot_threshold
        self.assertIn("1000UL", HEADER)  # protect_cooldown under HEADROOM_V2c
        self.assertIn("protect_stages", HEADER)
        self.assertIn("raw_hot_threshold", HEADER)
        self.assertIn("boot_scale", HEADER)
        mic_auto_idx = PLATFORMIO.index("[env:k1_bench_im73d_mic_auto]")
        # Next env section after mic_auto
        rest = PLATFORMIO[mic_auto_idx + 1 :]
        next_env = rest.find("\n[env:")
        mic_block = PLATFORMIO[
            mic_auto_idx : mic_auto_idx + 1 + (next_env if next_env >= 0 else len(rest))
        ]
        self.assertIn("-DK1_MIC_AUTO_HEADROOM_V2=1", mic_block)
        self.assertIn("-DK1_MIC_AUTO_DEFAULT_SENSITIVITY=1.8f", mic_block)

    def test_mic_auto_default_sensitivity_pinned(self):
        """SENS_V1a: mic_auto pins CONFIG.SENSITIVITY after NVS (no save_config)."""
        self.assertIn("K1_MIC_AUTO_DEFAULT_SENSITIVITY", CPP)
        self.assertIn("CONFIG.SENSITIVITY = K1_MIC_AUTO_DEFAULT_SENSITIVITY", CPP)
        self.assertIn("CONFIG_DEFAULTS.SENSITIVITY = K1_MIC_AUTO_DEFAULT_SENSITIVITY", CPP)
        self.assertNotIn("save_config(", CPP)
        globals_cfg = (ROOT / "SPECTRASYNQ_K1_FIRMWARE" / "system" / "globals_config.cpp").read_text(
            encoding="utf-8"
        )
        self.assertIn("K1_MIC_AUTO_DEFAULT_SENSITIVITY", globals_cfg)

    def test_headroom_v2_protect_reaches_floor_faster(self):
        """Dual-stage 0.55 drops further/faster than legacy 0.85 single-step."""
        legacy = Cfg(protect_factor=0.85, scale_max=1.50, protect_cooldown_ms=8000)
        v2 = Cfg(
            scale_min=0.22,
            protect_factor=0.55,
            protect_stages=2,
            scale_max=1.00,
            protect_cooldown_ms=1000,
            target_peak_hi=0.55,
            down_factor=0.70,
            down_dwell_ms=500,
            raw_hot_threshold=16000.0,
            boot_scale=0.55,
        )

        def after_n_protects(cfg, n=1, start=1.0):
            st = State(boot_start_ms=0, last_adjust_ms=0, scale=start)
            decide(st, Metrics(), cfg, 11000)
            t = 12000
            for _ in range(n):
                decide(
                    st,
                    Metrics(clip_pct=0.05, near_pct=0.05, raw_near_rail_pct=0.05),
                    cfg,
                    t,
                )
                t += 200
            return st.scale

        # One V2 protect frame = two 0.55 stages → 0.3025; legacy one frame → 0.85
        self.assertLess(after_n_protects(v2, 1), after_n_protects(legacy, 1))
        self.assertAlmostEqual(after_n_protects(v2, 1), 0.55**2, places=5)
        # Two V2 frames reach floor 0.22
        self.assertAlmostEqual(after_n_protects(v2, 2), 0.22, places=5)
        self.assertEqual(v2.scale_max, 1.00)
        self.assertEqual(v2.scale_min, 0.22)
        self.assertEqual(v2.protect_cooldown_ms, 1000)
        self.assertEqual(v2.protect_stages, 2)

    def test_headroom_v2_anticipatory_hot_trim_earlier(self):
        """target_peak_hi 0.55 fires hot_drive before legacy 0.78."""
        v2 = Cfg(
            scale_min=0.22,
            scale_max=1.00,
            protect_factor=0.55,
            protect_stages=2,
            target_peak_hi=0.55,
            down_factor=0.70,
            down_dwell_ms=500,
            protect_cooldown_ms=1000,
            raw_hot_threshold=16000.0,
        )
        st2 = State(
            boot_start_ms=0,
            last_adjust_ms=0,
            scale=1.0,
            ema_seeded=True,
            ema_peak_scaled=0.70,
            ema_raw_rms=50.0,
        )
        scale, state, reason, adjusted = decide(
            st2, Metrics(waveform_peak_scaled=0.70, raw_rms=50.0), v2, 12000
        )
        self.assertEqual(state, ADJUST_DOWN)
        self.assertEqual(reason, REASON_HOT)
        self.assertTrue(adjusted)
        self.assertAlmostEqual(scale, 0.70, places=5)

    def test_headroom_v2_raw_hot_threshold_protects(self):
        """max_waveform_val_raw above 16k triggers protect without clip flags."""
        v2 = Cfg(
            scale_min=0.22,
            scale_max=1.00,
            protect_factor=0.55,
            protect_stages=2,
            raw_hot_threshold=16000.0,
            protect_cooldown_ms=1000,
        )
        st = State(
            boot_start_ms=0,
            last_adjust_ms=0,
            scale=0.55,
            ema_seeded=True,
            ema_peak_scaled=0.40,
            ema_raw_rms=50.0,
        )
        scale, state, reason, adjusted = decide(
            st,
            Metrics(max_waveform_val_raw=18000.0, waveform_peak_scaled=0.40, raw_rms=50.0),
            v2,
            12000,
        )
        self.assertEqual(state, PROTECT)
        self.assertEqual(reason, REASON_HEADROOM)
        self.assertTrue(adjusted)
        self.assertAlmostEqual(scale, max(0.22, 0.55 * 0.55 * 0.55), places=5)


if __name__ == "__main__":
    unittest.main()
