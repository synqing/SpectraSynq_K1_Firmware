"""Host gate for the AFE2 exposure stage (audio/k1_afe2.cpp).

Compiles the firmware's own k1_afe2.cpp with tests/k1_afe2_host.cpp and runs it on a 100 s
programme of level steps. Two checks:

1. Differential: every hop's how_much equals an independent implementation of the specification
   (the reference below, a copy of
   _scratch/k1-fe-show-m2_20261110/audio-forensics/design/afe2_reference.py).
2. Behaviour, at named moments of the programme:
   - a loud passage sits at full;
   - a passage 10 dB quieter is shown clearly smaller and stays smaller for 10 s (a breakdown);
   - the return of the loud passage is at full within 100 ms (a drop lands at once);
   - a passage 14 dB quieter that persists is still small after 40 s, and has been re-exposed
     45 s later (a quieter programme is not a breakdown for ever);
   - silence falls to the floor and never below it;
   - gamma 0 gives 1.0 on every hop (exactly the behaviour without the stage).
"""
from pathlib import Path
import array
import math
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[1]
AUDIO = ROOT / "SPECTRASYNQ_K1_FIRMWARE" / "audio"
HOST = Path(__file__).parent / "k1_afe2_host.cpp"

RATE, HOP = 12800, 96
FC_HZ, TAU_S_ATTACK, TAU_S_RELEASE = 110.0, 0.030, 1.5
TAU_A_UP, TAU_A_SLOW, TAU_A_FAST = 3.0, 60.0, 4.0
T_HOLD, Q_QUIET, Q_EXIT, A_MIN = 45.0, 0.25, 0.70, 36.0
SIL_ENTER, SIL_EXIT = 16.0, 25.0   # stage 2 silence test, counts^2 (4.0 / 5.0 counts rms)
TAU_Q_RELEASE = 0.3                # its own release, so the delay after a stop does not grow with loudness

# (seconds, peak amplitude in raw counts). 400 is about the Main RPL microphone level at
# living-room volume; 126 is 10 dB below it; 80 is 14 dB below it.
PROGRAMME = ((5, 400), (10, 126), (5, 400), (70, 80), (5, 0), (5, 400))
# Stage 2: the same programme, then the music stops (20 s of digital silence), a quiet room
# (peak 3 counts, about 1.7 counts rms, the measured room floor), and the music again.
PROGRAMME_S2 = PROGRAMME + ((20, 0), (10, 3), (5, 400))


def _compiler():
    for cc in ("c++", "clang++", "g++"):
        if shutil.which(cc):
            return cc
    raise AssertionError("C++17 host compiler required")


def _programme(programme=PROGRAMME):
    """Deterministic broadband noise (a 32-bit LCG) at the scheduled peak amplitudes."""
    out = array.array("h")
    state = 0x1234ABCD
    for seconds, amp in programme:
        for _ in range(seconds * RATE):
            state = (state * 1664525 + 1013904223) & 0xFFFFFFFF
            out.append(int(((state >> 8) / 8388608.0 - 1.0) * amp))
    return out


def _alpha(dt, tau):
    return 1.0 - math.exp(-dt / tau)


def _reference(samples, gamma=1.0, floor=0.25, quiet_out=None):
    w0 = 2.0 * math.pi * FC_HZ / RATE
    cw, al = math.cos(w0), math.sin(w0) / (2.0 * math.sqrt(0.5))
    a0 = 1.0 + al
    b0, b1, b2, a1, a2 = (1 + cw) / 2 / a0, -(1 + cw) / a0, (1 + cw) / 2 / a0, -2 * cw / a0, (1 - al) / a0
    z1 = z2 = 0.0
    S, A, quiet, fast, silent, Sq = 0.0, A_MIN, 0.0, False, False, 0.0
    dt = HOP / RATE
    out = []
    for h0 in range(0, len(samples) - HOP + 1, HOP):
        acc = 0.0
        for x in samples[h0:h0 + HOP]:
            y = b0 * x + z1
            z1 = b1 * x - a1 * y + z2
            z2 = b2 * x - a2 * y
            acc += y * y
        e = acc / HOP
        S += _alpha(dt, TAU_S_ATTACK if e > S else TAU_S_RELEASE) * (e - S)
        if S > A:
            A += _alpha(dt, TAU_A_UP) * (S - A)
            quiet, fast = 0.0, False
        else:
            if S < Q_QUIET * A:
                quiet += dt
                if quiet > T_HOLD:
                    fast = True
            else:
                quiet = 0.0
            if fast and S > Q_EXIT * A:
                fast = False
            A += _alpha(dt, TAU_A_FAST if fast else TAU_A_SLOW) * (S - A)
        A = max(A, A_MIN)
        ratio = S / A
        if gamma == 1.0:
            h = math.sqrt(ratio)
        elif gamma == 0.0:
            h = 1.0
        else:
            h = ratio ** (gamma * 0.5) if ratio > 0.0 else 0.0
        out.append(min(1.0, max(floor, h)))
        Sq += _alpha(dt, TAU_S_ATTACK if e > Sq else TAU_Q_RELEASE) * (e - Sq)
        silent = (Sq < SIL_EXIT) if silent else (Sq < SIL_ENTER)
        if quiet_out is not None:
            quiet_out.append(1 if silent else 0)
    return out


def _run(tmp_path, samples, gamma, floor, column=0):
    exe = tmp_path / "k1_afe2_host"
    if not exe.exists():
        cmd = [_compiler(), "-std=c++17", "-O2", "-Wall", "-Wextra", "-Werror", f"-I{AUDIO}",
               str(HOST), str(AUDIO / "k1_afe2.cpp"), "-o", str(exe)]
        built = subprocess.run(cmd, capture_output=True, text=True)
        assert built.returncode == 0, built.stdout + built.stderr
    pcm = tmp_path / "programme.s16le"
    if not pcm.exists():
        pcm.write_bytes(samples.tobytes())
    ran = subprocess.run([str(exe), str(pcm), str(HOP), str(RATE), str(gamma), str(floor)],
                         capture_output=True, text=True)
    assert ran.returncode == 0, ran.stderr
    return [float(line.split()[column]) for line in ran.stdout.splitlines()]


def _at(values, seconds):
    return values[int(seconds * RATE / HOP)]


def test_afe2_matches_reference_and_behaves(tmp_path):
    samples = _programme()
    got = _run(tmp_path, samples, 1.0, 0.25)
    want = _reference(samples)
    assert len(got) == len(want) == len(samples) // HOP
    worst = max(abs(g - w) for g, w in zip(got, want))
    assert worst < 2e-3, f"firmware and reference differ by {worst}"

    assert _at(got, 4.9) > 0.90                      # loud passage at full
    assert 0.25 <= _at(got, 14.9) < 0.45             # 10 dB quieter: clearly smaller, still so after 10 s
    assert _at(got, 15.1) > 0.90                     # the loud passage returns: full within 100 ms
    assert _at(got, 60.0) < 0.35                     # 14 dB quieter, 40 s in: still a breakdown
    assert _at(got, 89.9) > 0.80                     # 70 s in: re-exposed to the quieter programme
    assert _at(got, 94.9) == 0.25                    # silence: on the floor, not below it
    assert _at(got, 95.1) > 0.90                     # music again: full at once
    assert min(got) >= 0.25 and max(got) <= 1.0


def test_afe2_silence_test_matches_reference_and_behaves(tmp_path):
    """Stage 2: the quiet flag equals the reference on every hop, never rises while music plays
    (including a passage 14 dB under the loud one), rises within 4 s of a loud stop (its own 0.3 s
    release), holds through a quiet room, and falls within 100 ms when the music returns. The
    firmware's 5 s dwell turns quiet into silence; it is not modelled here."""
    samples = _programme(PROGRAMME_S2)
    got = [int(v) for v in _run(tmp_path, samples, 1.0, 0.25, column=4)]
    want = []
    _reference(samples, quiet_out=want)
    assert len(got) == len(want) == len(samples) // HOP
    mismatched = [i for i, (g, w) in enumerate(zip(got, want)) if g != w]
    assert not mismatched, f"firmware and reference quiet differ on {len(mismatched)} hops, first {mismatched[:5]}"

    hop_s = HOP / RATE
    assert not any(got[:int(90.0 / hop_s)])          # 90 s of music (incl. 14 dB down): never quiet
    assert _at(got, 94.9) == 1                       # the programme's own 5 s of silence: quiet (dwell not met)
    assert not any(got[int(95.1 / hop_s):int(100.0 / hop_s)])  # music back: clear within 100 ms
    assert _at(got, 101.0) == 0                      # 1 s after a loud stop: still counted as music
    assert _at(got, 104.0) == 1                      # 4 s after a loud stop: quiet (the dwell then applies)
    assert all(got[int(104.0 / hop_s):int(130.0 / hop_s)])  # silence, then a quiet room: stays quiet
    assert _at(got, 130.1) == 0                      # music again: not quiet within 100 ms


def test_afe2_gamma_zero_is_identity(tmp_path):
    got = _run(tmp_path, _programme(), 0.0, 0.25)
    assert set(got) == {1.0}


def test_afe2_wiring():
    """One meter on the raw hop; brightness scaled on both edges for the live path only; the
    level-free envelope keeps its own state; the guard still reads that envelope."""
    i2s = (AUDIO / "i2s_audio.h").read_text(encoding="utf-8")
    led = (ROOT / "SPECTRASYNQ_K1_FIRMWARE" / "visual" / "led_utilities.h").read_text(encoding="utf-8")
    assert "k1_afe2_process_hop(k1_afe2, im69d_samples_i16" in i2s
    assert "waveform_peak_scaled = k1_afe2_level_enabled ? (k1_afe2_peak_env * k1_afe2.how_much) : k1_afe2_peak_env;" in i2s
    assert "(k1_afe2_peak_env >= K1_LOUD_GUARD_PEAK_PIN_THRESHOLD)" in i2s
    assert "if (!k1_authored_suppresses_live_update()) brightness *= SQ15x16(k1_afe2_brightness_scale());" in led
    assert "if (!k1_authored_suppresses_live_update()) bright_val *= k1_afe2_brightness_scale();" in led
    # Stage 2 (accepted): the IM69D product silence decision is the meter's quiet flag.
    assert "#if defined(K1_MIC_IM69D_PDM_V1) && !defined(K1_AP_DRIVE_CONTRACT_V1)" in i2s
    assert "k1_rms_silent_state = k1_afe2_ready && k1_afe2.quiet;" in i2s
