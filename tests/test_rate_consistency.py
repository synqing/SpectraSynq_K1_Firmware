"""Rate-consistency gate: every host-harness replica of the firmware audio-frame
and novelty-emit rates MUST equal the constants hard-coded in sb_tempo.cpp.

sb_tempo's Goertzel/ACF tempo bins are computed at a FIXED novelty rate. If a host
replica (novelty_from_wav hop/rate, bt_acf_4way / acf_ceiling_sweep decimation +
emit rate) drifts to 2x or 0.5x of the firmware's rate, every BPM the harness scores
is wrong by that factor and the whole offline-validation pipe silently lies (a 120 BPM
click reads ~139 — the exact bug the sb_tempo.cpp comment at line 14-19 documents).

This test reads the four authoritative constants straight out of sb_tempo.cpp
(SB_AP_FRAME_HZ, SB_NOVELTY_DECIMATION, SB_NOVELTY_RATE_HZ, SB_HISTORY_LENGTH) by
text-parsing the source — NO compile — then asserts each Python replica agrees:

  - novelty_from_wav: SAMPLE_RATE / HOP  == SB_AP_FRAME_HZ  (133.33 Hz, hop=96)
  - bt_acf_4way:      SB_AP_FRAME_HZ, SB_NOVELTY_DECIMATION, SB_NOVELTY_RATE_HZ,
                      SB_HISTORY_LENGTH all equal the firmware values
  - acf_ceiling_sweep:FPS_FULL == SB_AP_FRAME_HZ, FPS_DECIM == SB_NOVELTY_RATE_HZ,
                      SB_NOVELTY_DECIMATION agrees

Pure-Python, no clang, so it is cheap in the pytest gate. It FAILS hard on any
2x/0.5x mismatch (the only failure mode that matters), and on a missing constant.

Mirrors tests/test_onset_beat_replay.py style (stdlib unittest, ROOT-relative paths).
"""

import math
import re
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
HARNESS = ROOT / "scripts" / "regression-harness"
FW_AUDIO = ROOT / "SPECTRASYNQ_K1_FIRMWARE" / "audio"
FW_SYSTEM = ROOT / "SPECTRASYNQ_K1_FIRMWARE" / "system"
SB_TEMPO_CPP = FW_AUDIO / "sb_tempo.cpp"
SB_ONSET_CPP = FW_AUDIO / "sb_onset_beat.cpp"
SB_SEMANTIC_CPP = FW_AUDIO / "sb_semantic_state.cpp"
CONFIG_TYPES_H = FW_SYSTEM / "config_types.h"

# Allow `import novelty_from_wav` etc. exactly as the other harness consumers do.
sys.path.insert(0, str(HARNESS))

REL_TOL = 1e-4   # the firmware rates are exact ratios; this only guards float printf drift


def _read(path):
    return Path(path).read_text(encoding="utf-8")


def _grep_float(text, name, env=None):
    """Return the float value assigned to a `... NAME = <expr>;` line. Evaluates a
    simple arithmetic expr so we read the firmware's INTENT (12800.0f/96.0f, or
    SB_AP_FRAME_HZ / SB_NOVELTY_DECIMATION) rather than a magic literal.

    `env` maps already-resolved constant names -> float so a constant defined in terms
    of an earlier one (SB_NOVELTY_RATE_HZ = SB_AP_FRAME_HZ / (float)SB_NOVELTY_DECIMATION)
    resolves. Strips C float/int suffixes (f/F/u/U/l/L) and `(float)`/`(int)` casts."""
    env = env or {}
    # grab the RHS of `NAME = <expr>` up to the first terminator: ';' (C++), '#'
    # (Python comment), or end-of-line. Works for both sb_tempo.cpp and the .py replicas.
    m = re.search(rf"\b{re.escape(name)}\s*=\s*([^;#\n]+)", text)
    if not m:
        return None
    expr = m.group(1)
    expr = re.sub(r"\((?:float|int|uint\w*|double)\)", "", expr)        # drop casts
    expr = re.sub(r"(?<=[0-9.])[fFlLuU]+", "", expr)                    # strip numeric suffixes
    # substitute any known symbol names with their resolved float values
    for sym, val in env.items():
        expr = re.sub(rf"\b{re.escape(sym)}\b", repr(float(val)), expr)
    expr = re.sub(r"\(([0-9eE.+\-/*() ]+)\)", r"(\1)", expr)
    expr = expr.strip()
    # only digits, dot, e/E, sign, arithmetic ops, parens, whitespace may remain
    if not re.fullmatch(r"[0-9eE.+\-/*() ]+", expr):
        return None
    try:
        return float(eval(expr, {"__builtins__": {}}, {}))  # noqa: S307 (sandboxed, numeric-only)
    except Exception:  # noqa: BLE001
        return None


def _grep_define(text, name, env=None):
    """Return the float assigned by `#define NAME <value>` (numeric only). Used for
    the calibratable/tau constants that are #defines rather than `= <expr>;`."""
    env = env or {}
    m = re.search(rf"#define\s+{re.escape(name)}\s+([^\n/]*(?:/[^\n/]*)*)", text)
    if not m:
        return None
    try:
        expr = m.group(1).split("//", 1)[0].strip()
        expr = re.sub(r"\((?:float|int|uint\w*|double)\)", "", expr)
        expr = re.sub(r"(?<=[0-9.])[fFlLuU]+", "", expr)
        for sym, val in env.items():
            expr = re.sub(rf"\b{re.escape(sym)}\b", repr(float(val)), expr)
        if not re.fullmatch(r"[0-9eE.+\-/*() ]+", expr):
            return None
        return float(eval(expr, {"__builtins__": {}}, {}))  # noqa: S307 (sandboxed, numeric-only)
    except ValueError:
        return None


def _alpha_from_tau(rate_hz, tau_s):
    """Continuous-time EMA alpha at a given update rate: 1 - exp(-(1/rate)/tau).
    This is the EXACT derivation the firmware uses for the conf/flywheel EMAs."""
    return 1.0 - math.exp(-(1.0 / rate_hz) / tau_s)


class RateConsistencyTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cpp = _read(SB_TEMPO_CPP)
        cls.config_types = _read(CONFIG_TYPES_H)
        macro_env = {
            "DEFAULT_SAMPLE_RATE": _grep_define(cls.config_types, "DEFAULT_SAMPLE_RATE"),
            "DEFAULT_SAMPLES_PER_CHUNK": _grep_define(cls.config_types, "DEFAULT_SAMPLES_PER_CHUNK"),
            "SB_TEMPO_NOVELTY_DECIMATION": _grep_define(cls.config_types, "SB_TEMPO_NOVELTY_DECIMATION"),
        }
        tempo_ap_define = _grep_define(cls.cpp, "SB_TEMPO_AP_FRAME_HZ", macro_env)
        tempo_decim_define = _grep_define(cls.config_types, "SB_TEMPO_NOVELTY_DECIMATION", macro_env)
        if tempo_ap_define is not None:
            macro_env["SB_TEMPO_AP_FRAME_HZ"] = tempo_ap_define
        if tempo_decim_define is not None:
            macro_env["SB_TEMPO_NOVELTY_DECIMATION"] = tempo_decim_define
        cls.fw_ap_hz = _grep_float(cls.cpp, "SB_AP_FRAME_HZ", macro_env)
        cls.fw_decim = _grep_float(cls.cpp, "SB_NOVELTY_DECIMATION", macro_env)
        # SB_NOVELTY_RATE_HZ is defined as SB_AP_FRAME_HZ / (float)SB_NOVELTY_DECIMATION —
        # resolve it by substituting the two already-parsed firmware constants.
        env = {}
        if cls.fw_ap_hz is not None:
            env["SB_AP_FRAME_HZ"] = cls.fw_ap_hz
        if cls.fw_decim is not None:
            env["SB_NOVELTY_DECIMATION"] = cls.fw_decim
        cls.fw_nov_hz = _grep_float(cls.cpp, "SB_NOVELTY_RATE_HZ", env)
        cls.fw_hist = _grep_float(cls.cpp, "SB_HISTORY_LENGTH")

    # --- firmware self-consistency (anchors the rest) ----------------------------
    def test_firmware_constants_present(self):
        self.assertIsNotNone(self.fw_ap_hz, "SB_AP_FRAME_HZ not found in sb_tempo.cpp")
        self.assertIsNotNone(self.fw_decim, "SB_NOVELTY_DECIMATION not found in sb_tempo.cpp")
        self.assertIsNotNone(self.fw_nov_hz, "SB_NOVELTY_RATE_HZ not found in sb_tempo.cpp")
        self.assertIsNotNone(self.fw_hist, "SB_HISTORY_LENGTH not found in sb_tempo.cpp")

    def test_firmware_rates_are_the_known_ratios(self):
        # 12800/96 = 133.333..., /3 = 44.444..., history 512. A 2x/0.5x edit here trips this.
        default_sr = _grep_define(self.config_types, "DEFAULT_SAMPLE_RATE")
        default_hop = _grep_define(self.config_types, "DEFAULT_SAMPLES_PER_CHUNK")
        self.assertAlmostEqual(self.fw_ap_hz, default_sr / default_hop, delta=self.fw_ap_hz * REL_TOL)
        self.assertEqual(int(self.fw_decim), 3)
        self.assertAlmostEqual(self.fw_nov_hz, self.fw_ap_hz / self.fw_decim,
                               delta=self.fw_nov_hz * REL_TOL)
        self.assertEqual(int(self.fw_hist), 512)

    # --- novelty_from_wav replica ------------------------------------------------
    def test_novelty_from_wav_frame_rate_matches_firmware(self):
        import novelty_from_wav as nfw
        host_ap_hz = nfw.SAMPLE_RATE / nfw.HOP
        self.assertEqual(nfw.HOP, 96, "novelty hop must be SAMPLES_PER_CHUNK=96")
        # The crucial 2x/0.5x guard: host AP frame rate == firmware AP frame rate.
        self.assertAlmostEqual(
            host_ap_hz, self.fw_ap_hz, delta=self.fw_ap_hz * REL_TOL,
            msg=f"novelty_from_wav AP rate {host_ap_hz:.3f}Hz != firmware {self.fw_ap_hz:.3f}Hz "
                f"(SAMPLE_RATE={nfw.SAMPLE_RATE}, HOP={nfw.HOP})")

    # --- bt_acf_4way replica -----------------------------------------------------
    def test_bt_acf_4way_constants_match_firmware(self):
        src = _read(HARNESS / "bt_acf_4way.py")
        host_ap = _grep_float(src, "SB_AP_FRAME_HZ")
        host_dec = _grep_float(src, "SB_NOVELTY_DECIMATION")
        # bt_acf_4way: SB_NOVELTY_RATE_HZ = SB_AP_FRAME_HZ / SB_NOVELTY_DECIMATION
        env = {}
        if host_ap is not None:
            env["SB_AP_FRAME_HZ"] = host_ap
        if host_dec is not None:
            env["SB_NOVELTY_DECIMATION"] = host_dec
        host_nov = _grep_float(src, "SB_NOVELTY_RATE_HZ", env)
        host_hist = _grep_float(src, "SB_HISTORY_LENGTH")
        self.assertIsNotNone(host_ap, "bt_acf_4way missing SB_AP_FRAME_HZ")
        self.assertIsNotNone(host_nov, "bt_acf_4way missing SB_NOVELTY_RATE_HZ")
        self.assertAlmostEqual(host_ap, self.fw_ap_hz, delta=self.fw_ap_hz * REL_TOL,
                               msg="bt_acf_4way SB_AP_FRAME_HZ drifted from firmware")
        self.assertEqual(int(host_dec), int(self.fw_decim),
                         "bt_acf_4way decimation drifted from firmware")
        self.assertAlmostEqual(host_nov, self.fw_nov_hz, delta=self.fw_nov_hz * REL_TOL,
                               msg="bt_acf_4way SB_NOVELTY_RATE_HZ drifted from firmware")
        self.assertEqual(int(host_hist), int(self.fw_hist),
                         "bt_acf_4way SB_HISTORY_LENGTH drifted from firmware")

    # --- acf_ceiling_sweep replica ----------------------------------------------
    def test_acf_ceiling_sweep_rates_match_firmware(self):
        src = _read(HARNESS / "acf_ceiling_sweep.py")
        host_dec = _grep_float(src, "SB_NOVELTY_DECIMATION")
        self.assertIsNotNone(host_dec, "acf_ceiling_sweep missing SB_NOVELTY_DECIMATION")
        self.assertEqual(int(host_dec), int(self.fw_decim),
                         "acf_ceiling_sweep decimation drifted from firmware")
        # FPS_FULL = nfw.SAMPLE_RATE / nfw.HOP ; FPS_DECIM = FPS_FULL / SB_NOVELTY_DECIMATION.
        # Recompute from the imported novelty module + the file's own decimation, then
        # assert both land on the firmware rates (catches a hop or /N edit anywhere).
        import novelty_from_wav as nfw
        fps_full = nfw.SAMPLE_RATE / nfw.HOP
        fps_decim = fps_full / int(host_dec)
        self.assertAlmostEqual(fps_full, self.fw_ap_hz, delta=self.fw_ap_hz * REL_TOL,
                               msg="acf_ceiling_sweep FPS_FULL != firmware AP rate")
        self.assertAlmostEqual(fps_decim, self.fw_nov_hz, delta=self.fw_nov_hz * REL_TOL,
                               msg="acf_ceiling_sweep FPS_DECIM != firmware novelty rate")


    # --- V2 EMA derivations are self-consistent with the EMIT rate ----------------
    def test_confv2_alpha_is_derived_from_novelty_rate(self):
        # SB_CONF_V2_ALPHA_NOMINAL = 1 - exp(-(1/SB_NOVELTY_RATE_HZ)/SB_CONF_V2_TAU_S).
        # The conf EMA updates once per NOVELTY EMIT (44.44 Hz), so the alpha MUST be
        # derived at that rate, NOT the AP frame rate. Pin both the derivation and the
        # documented ~0.1393 value; a rate-domain mistake (using 133 Hz) trips this.
        tau = _grep_define(self.cpp, "SB_CONF_V2_TAU_S")
        self.assertIsNotNone(tau, "SB_CONF_V2_TAU_S not found in sb_tempo.cpp")
        # The source must literally divide by SB_NOVELTY_RATE_HZ (emit rate), not AP rate.
        self.assertRegex(
            self.cpp,
            r"SB_CONF_V2_ALPHA_NOMINAL\s*=\s*[\s\S]{0,80}?SB_NOVELTY_RATE_HZ[\s\S]{0,40}?SB_CONF_V2_TAU_S",
            "SB_CONF_V2_ALPHA_NOMINAL must be derived from SB_NOVELTY_RATE_HZ / SB_CONF_V2_TAU_S",
        )
        expected = _alpha_from_tau(self.fw_nov_hz, tau)
        self.assertAlmostEqual(expected, 0.1393, delta=0.002,
                               msg=f"conf EMA alpha at emit rate should be ~0.1393, got {expected:.4f}")

    def test_flywheel_floor_alpha_is_derived_from_novelty_rate(self):
        # SB_FW_FLOOR_ALPHA = 1 - exp(-(1/SB_NOVELTY_RATE_HZ)/SB_FW_ONSET_FLOOR_TAU_S).
        # Flywheel runs per EMIT (44.44 Hz). Pin the derivation + the documented 0.0723.
        tau = _grep_define(self.cpp, "SB_FW_ONSET_FLOOR_TAU_S")
        self.assertIsNotNone(tau, "SB_FW_ONSET_FLOOR_TAU_S not found in sb_tempo.cpp")
        self.assertRegex(
            self.cpp,
            r"SB_FW_FLOOR_ALPHA\s*=\s*[\s\S]{0,80}?SB_NOVELTY_RATE_HZ[\s\S]{0,60}?SB_FW_ONSET_FLOOR_TAU_S",
            "SB_FW_FLOOR_ALPHA must be derived from SB_NOVELTY_RATE_HZ / SB_FW_ONSET_FLOOR_TAU_S",
        )
        expected = _alpha_from_tau(self.fw_nov_hz, tau)
        self.assertAlmostEqual(expected, 0.0723, delta=0.002,
                               msg=f"flywheel floor alpha at emit rate should be ~0.0723, got {expected:.4f}")

    def test_onset_v2_band_alphas_match_133hz_tau_rederivation(self):
        # Onset V2 band EMAs run once per AP FRAME (133.33 Hz, dt=7.5 ms) — NOT the
        # tempo emit rate. The source documents donor taus (kick 525 ms, snare 792 ms,
        # hihat 1592 ms) re-derived at 133.33 Hz via a = dt/(tau+dt). Recompute from the
        # firmware AP rate and the documented taus; assert the hard-coded alphas match.
        src = _read(SB_ONSET_CPP)
        dt_ms = 1000.0 / self.fw_ap_hz  # 7.5 ms at 133.33 Hz
        cases = {  # constant name -> donor tau (ms) stated in the source comment
            "SBV2_KICK_ALPHA": 525.0,
            "SBV2_SNARE_ALPHA": 792.0,
            "SBV2_HIHAT_ALPHA": 1592.0,
        }
        for const, tau_ms in cases.items():
            coded = _grep_float(src, const) or _grep_define(src, const)
            self.assertIsNotNone(coded, f"{const} not found in sb_onset_beat.cpp")
            expected = dt_ms / (tau_ms + dt_ms)  # a = dt/(tau+dt) at 133.33 Hz
            # 1e-3 tolerance: the firmware rounds the alpha to 4 dp.
            self.assertAlmostEqual(coded, expected, delta=1e-3,
                                   msg=f"{const}={coded} != dt/(tau+dt)@133Hz ({expected:.4f}); "
                                       f"rate-domain or tau drift")

    # --- INJECTION: a 2x / 0.5x rate edit MUST be detected ------------------------
    def test_2x_and_half_rate_injection_is_detected(self):
        # Inject a doubled / halved AP frame rate into an in-memory copy of the source
        # and prove the self-consistency cross-checks FAIL. This is the only failure
        # mode that matters: a hop or SR edit that silently scales every BPM. We verify
        # by injection (not just by asserting the live values) so the GUARD itself is
        # proven to fire, not merely the current numbers.
        for factor in (2.0, 0.5):
            mutated = re.sub(
                r"(#define\s+SB_TEMPO_AP_FRAME_HZ\s+)\(\(float\)DEFAULT_SAMPLE_RATE\s*/\s*\(float\)DEFAULT_SAMPLES_PER_CHUNK\)",
                rf"\g<1>({factor} * (float)DEFAULT_SAMPLE_RATE / (float)DEFAULT_SAMPLES_PER_CHUNK)",
                self.cpp,
            )
            self.assertNotEqual(mutated, self.cpp,
                                f"injection ({factor}x) did not rewrite SB_TEMPO_AP_FRAME_HZ — test is blind")
            macro_env = {}
            macro_env = {
                "DEFAULT_SAMPLE_RATE": _grep_define(self.config_types, "DEFAULT_SAMPLE_RATE"),
                "DEFAULT_SAMPLES_PER_CHUNK": _grep_define(self.config_types, "DEFAULT_SAMPLES_PER_CHUNK"),
                "SB_TEMPO_NOVELTY_DECIMATION": _grep_define(self.config_types, "SB_TEMPO_NOVELTY_DECIMATION"),
            }
            tempo_ap_define = _grep_define(mutated, "SB_TEMPO_AP_FRAME_HZ", macro_env)
            tempo_decim_define = _grep_define(self.config_types, "SB_TEMPO_NOVELTY_DECIMATION", macro_env)
            self.assertIsNotNone(tempo_ap_define)
            if tempo_ap_define is not None:
                macro_env["SB_TEMPO_AP_FRAME_HZ"] = tempo_ap_define
            if tempo_decim_define is not None:
                macro_env["SB_TEMPO_NOVELTY_DECIMATION"] = tempo_decim_define
            inj_ap = _grep_float(mutated, "SB_AP_FRAME_HZ", macro_env)
            self.assertIsNotNone(inj_ap)
            # 1) the AP rate itself no longer matches the true firmware ratio
            self.assertFalse(
                abs(inj_ap - self.fw_ap_hz) <= self.fw_ap_hz * REL_TOL,
                f"{factor}x injection should break the AP-rate ratio assertion",
            )
            # 2) the derived novelty rate scales too -> EMA alphas now wrong by `factor`
            env = {"SB_AP_FRAME_HZ": inj_ap, "SB_NOVELTY_DECIMATION": self.fw_decim}
            inj_nov = _grep_float(mutated, "SB_NOVELTY_RATE_HZ", env)
            self.assertAlmostEqual(inj_nov, self.fw_nov_hz * factor, delta=inj_nov * REL_TOL,
                                   msg=f"{factor}x AP injection must scale the novelty emit rate by {factor}x")
            tau = _grep_define(self.cpp, "SB_CONF_V2_TAU_S")
            good_alpha = _alpha_from_tau(self.fw_nov_hz, tau)
            bad_alpha = _alpha_from_tau(inj_nov, tau)
            self.assertGreater(abs(bad_alpha - good_alpha), 0.01,
                               f"{factor}x injection must materially shift the conf EMA alpha")

    # --- AudioSemanticState rate diagnostics self-describe the firmware rates ------
    def test_semantic_state_rate_diagnostics_match_firmware(self):
        # The spine exposes the rate self-description (Phase 7.2). Pin that it mirrors
        # the SAME decimation sb_tempo.cpp uses and derives ap/novelty from SR/hop, so
        # the diagnostics cannot silently disagree with the tempo lane's true cadence.
        self.assertTrue(SB_SEMANTIC_CPP.exists(),
                        "sb_semantic_state.cpp missing (spine not present)")
        src = _read(SB_SEMANTIC_CPP)
        decim = _grep_float(src, "SB_SEMANTIC_NOVELTY_DECIMATION", {
            "SB_TEMPO_NOVELTY_DECIMATION": self.fw_decim,
        })
        self.assertIsNotNone(decim, "SB_SEMANTIC_NOVELTY_DECIMATION not found in sb_semantic_state.cpp")
        self.assertEqual(int(decim), int(self.fw_decim),
                         "spine novelty decimation mirror drifted from sb_tempo.cpp")
        # ap_frame_hz must be SR/hop and novelty must be ap/decim (string-level guard so
        # a refactor that hard-codes a literal Hz instead of deriving is caught).
        self.assertRegex(src, r"ap\s*=\s*\(spc[\s\S]{0,40}?sr\s*/\s*\(float\)spc",
                         "spine ap_frame_hz must derive from SR / hop")
        self.assertRegex(src, r"nov\s*=\s*[\s\S]{0,80}?ap\s*/\s*\(float\)SB_SEMANTIC_NOVELTY_DECIMATION",
                         "spine novelty_rate_hz must derive from ap / decimation")


if __name__ == "__main__":
    unittest.main()
