"""Host gate for AP α = dt/(τ+dt) at 100 Hz reference.

Step 1.1 of fps_agc_clock_fix: equivalence at the tuning cadence, plus
wall-clock envelope match at the dumped AP rates (93 vs 139 Hz).
"""

from __future__ import annotations

import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HEADER = ROOT / "SPECTRASYNQ_K1_FIRMWARE" / "audio" / "k1_agc_dt_clock.h"
GDFT = ROOT / "SPECTRASYNQ_K1_FIRMWARE" / "audio" / "k1_gdft_core.cpp"
I2S = ROOT / "SPECTRASYNQ_K1_FIRMWARE" / "audio" / "i2s_audio.h"
UTIL = ROOT / "SPECTRASYNQ_K1_FIRMWARE" / "system" / "utilities.h"

DT_REF = 0.010
OLD = {
    "attack": 0.28,
    "release": 0.02,
    "noise": 0.001,
    "gain": 0.05,
    "follow_attack": 0.25,
    "follow_release": 0.005,
    "peak_attack_snap": 0.65,
    "peak_attack_sym": 0.25,
    "peak_release_snap": 0.15,
    "peak_release_sym": 0.25,
}


def tau_from_alpha(alpha: float, dt_ref: float = DT_REF) -> float:
    return dt_ref * (1.0 - alpha) / alpha


def alpha_from_tau(dt: float, tau: float) -> float:
    return dt / (tau + dt)


def clamp_dt(dt: float) -> float:
    return min(0.020, max(0.004, dt))


def test_header_exists():
    text = HEADER.read_text(encoding="utf-8")
    assert "k1_alpha_from_tau_s" in text
    assert "expf(" not in text
    assert "exp(" not in text
    assert "K1_AGC_DT_REF_S = 0.010f" in text
    assert "K1_AGC_ALPHA_ATTACK_REF = 0.28f" in text


def test_alpha_tau_equivalence_at_100hz():
    for name, alpha_old in OLD.items():
        tau = tau_from_alpha(alpha_old)
        recovered = alpha_from_tau(DT_REF, tau)
        assert math.isclose(recovered, alpha_old, rel_tol=0, abs_tol=1e-12), (
            f"{name}: {recovered} != {alpha_old} at 100 Hz"
        )


def test_documented_taus_match_handover():
    assert math.isclose(tau_from_alpha(0.28) * 1000.0, 25.714285714285715, rel_tol=1e-9)
    assert math.isclose(tau_from_alpha(0.02) * 1000.0, 490.0, rel_tol=1e-9)
    assert math.isclose(tau_from_alpha(0.001) * 1000.0, 9990.0, rel_tol=1e-9)
    assert math.isclose(tau_from_alpha(0.05) * 1000.0, 190.0, rel_tol=1e-9)
    assert math.isclose(tau_from_alpha(0.25) * 1000.0, 30.0, rel_tol=1e-9)
    assert math.isclose(tau_from_alpha(0.005) * 1000.0, 1990.0, rel_tol=1e-9)
    assert math.isclose(tau_from_alpha(0.65) * 1000.0, 5.384615384615385, rel_tol=1e-9)
    assert math.isclose(tau_from_alpha(0.15) * 1000.0, 56.66666666666667, rel_tol=1e-9)


def _envelope(signal, dt: float, tau_a: float, tau_r: float) -> list[float]:
    a = alpha_from_tau(clamp_dt(dt), tau_a)
    r = alpha_from_tau(clamp_dt(dt), tau_r)
    env = 0.0
    out = []
    for x in signal:
        if x > env:
            env += (x - env) * a
        else:
            env += (x - env) * r
        out.append(env)
    return out


def test_wall_clock_envelope_93_vs_139_hz():
    """Same physical stimulus, two AP rates — envelopes match at shared times."""
    tau_a = tau_from_alpha(0.28)
    tau_r = tau_from_alpha(0.02)
    duration = 2.0
    # Step up at 0.2 s, down at 1.0 s
    def stim(t: float) -> float:
        return 1.0 if 0.2 <= t < 1.0 else 0.05

    def sample(hz: float):
        dt = 1.0 / hz
        n = int(duration / dt)
        times = [i * dt for i in range(n)]
        sig = [stim(t) for t in times]
        return times, _envelope(sig, dt, tau_a, tau_r)

    t93, e93 = sample(93.0)
    t139, e139 = sample(139.0)

    # Compare at 10 ms grid by linear interpolation
    err = 0.0
    count = 0
    t = 0.05
    while t < duration - 0.05:
        def interp(ts, es, x):
            i = 0
            while i + 1 < len(ts) and ts[i + 1] < x:
                i += 1
            if i + 1 >= len(ts):
                return es[-1]
            u = (x - ts[i]) / (ts[i + 1] - ts[i])
            return es[i] + u * (es[i + 1] - es[i])

        err += abs(interp(t93, e93, t) - interp(t139, e139, t))
        count += 1
        t += 0.010
    mean_abs = err / count
    # Onset-dt class: same wall-clock filter; residual is sampling, not rate
    assert mean_abs < 0.02, f"mean abs envelope delta {mean_abs:.4f}"


def test_hardcoded_alphas_diverge_across_rates():
    """Sanity: the bug we are fixing — fixed α at two rates is NOT wall-clock equal."""
    duration = 1.5

    def stim(t: float) -> float:
        return 1.0 if t >= 0.1 else 0.0

    def env_fixed(hz: float, a: float):
        dt = 1.0 / hz
        n = int(duration / dt)
        env = 0.0
        last_t = 0.0
        last_e = 0.0
        for i in range(n):
            t = i * dt
            x = stim(t)
            env += (x - env) * a
            last_t, last_e = t, env
        return last_t, last_e

    # Attack 0.28 at 93 vs 139 Hz for 400 ms of a step
    def env_at(hz: float, t_query: float, a: float) -> float:
        dt = 1.0 / hz
        env = 0.0
        t = 0.0
        while t < t_query:
            x = 1.0 if t >= 0.1 else 0.0
            env += (x - env) * a
            t += dt
        return env

    # Mid-attack, not settled: 80 ms after the step, fixed-α rates still disagree.
    slow = env_at(93.0, 0.18, 0.28)
    fast = env_at(139.0, 0.18, 0.28)
    assert abs(slow - fast) > 0.02


def test_firmware_uses_dt_form_not_expf():
    gdft = GDFT.read_text(encoding="utf-8")
    i2s = I2S.read_text(encoding="utf-8")
    assert "k1_agc_dt_clock.h" in gdft
    assert "k1_agc_dt_clock.h" in i2s
    assert "k1_alpha_from_tau_s" in gdft
    assert "k1_alpha_from_tau_s" in i2s
    # AGC clock path must not grow expf
    assert "expf(-" not in gdft[gdft.index("BROADBAND AGC") : gdft.index("agc_gain += ")]
    assert "<esp_timer.h>" not in HEADER.read_text(encoding="utf-8")


def test_low_pass_array_still_uses_system_fps():
    gdft = GDFT.read_text(encoding="utf-8")
    assert "low_pass_array(magnitudes_final, magnitudes_last, NUM_FREQS, SYSTEM_FPS" in gdft
    util = UTIL.read_text(encoding="utf-8")
    assert "1.0" in util  # Hz-compensated form lives here; do not dt-warp the call
