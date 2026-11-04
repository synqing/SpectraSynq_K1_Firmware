"""P4 alignment/drift estimator and evidence-epoch guarantees.

These are host tests. They do not touch silicon and they do not claim P4.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools" / "pcm1808"
PCM_CPP = ROOT / "SPECTRASYNQ_K1_FIRMWARE" / "audio" / "k1_pcm1808_input.cpp"


def test_align_estimator_selftest_passes() -> None:
    """The estimator must recover KNOWN lag and KNOWN ppm before it is trusted."""
    r = subprocess.run(
        [sys.executable, str(TOOLS / "p4_align.py"), "--selftest"],
        capture_output=True, text=True, check=False,
    )
    assert r.returncode == 0, r.stdout + r.stderr
    assert "P4_ALIGN_SELFTEST=PASS" in r.stdout


def test_align_flags_periodic_stimulus_as_ambiguous() -> None:
    """A periodic train aliases by one period; that must be surfaced, not hidden."""
    sys.path.insert(0, str(TOOLS))
    from p4_align import estimate_alignment, _synth  # noqa: E402

    fs = 12800.0
    n = int(fs * 6)
    periodic = _synth(n, fs, jitter=0.0)
    jittered = _synth(n, fs, jitter=0.35)
    delay = 256
    p = estimate_alignment(periodic, fs, [0.0] * delay + periodic[: n - delay], fs)
    j = estimate_alignment(jittered, fs, [0.0] * delay + jittered[: n - delay], fs)
    assert p["ambiguous"] is True
    assert j["ambiguous"] is False
    assert j["peak_to_sidelobe"] > p["peak_to_sidelobe"]


def test_uncorrelated_pair_is_not_reported_as_aligned() -> None:
    sys.path.insert(0, str(TOOLS))
    import random
    from p4_align import estimate_alignment, _synth  # noqa: E402

    fs = 12800.0
    n = int(fs * 4)
    rnd = random.Random(3)
    noise = [rnd.random() - 0.5 for _ in range(n)]
    r = estimate_alignment(_synth(n, fs), fs, noise, fs)
    assert r["peak_correlation"] < 0.5


def test_fill_is_clean_requires_zero_ring_drop() -> None:
    """P4 addendum: both ovf and ring drop must be zero during the evidence fill."""
    sys.path.insert(0, str(TOOLS))
    from fixture_runner import fill_is_clean  # noqa: E402

    good = {"ovf_delta_fill": 0, "drop_delta_fill": 0, "filled": 100, "target": 100}
    assert fill_is_clean(good) is True
    assert fill_is_clean({**good, "drop_delta_fill": 1}) is False
    assert fill_is_clean({**good, "ovf_delta_fill": 1}) is False
    assert fill_is_clean({**good, "filled": 99}) is False


def test_firmware_latches_epoch_counters_at_fill_completion() -> None:
    """The dump must not be the thing that defines the counters it reports.

    The hex dump runs on the serial/AP core and provokes ring drop itself, so a
    PASS judged on counters read at dump time is judging the dump.
    """
    src = PCM_CPP.read_text(encoding="utf-8")
    for symbol in (
        "s_raw_arm_ovf",
        "s_raw_end_ovf",
        "s_raw_arm_ring_drop",
        "s_raw_end_ring_drop",
        "s_raw_epoch_valid",
        "s_raw_t1_us",
    ):
        assert symbol in src, f"missing epoch snapshot symbol {symbol}"

    # latched at the fill-completion branch, before any serialisation
    tail = src.split("if (n >= target) {", 1)[1].split("}", 1)[0]
    assert "s_raw_end_ovf" in tail, "epoch counters not latched at fill completion"
    assert "s_raw_t1_us" in tail, "epoch end timestamp not latched at fill completion"

    # both the status line and the dump header must expose the epoch delta
    assert "[PCMRAW24EPOCH]" in src
    assert "ovf_epoch=" in src and "ring_drop_epoch=" in src


def test_align_fixture_generator_emits_jittered_and_control() -> None:
    r = subprocess.run(
        [sys.executable, str(TOOLS / "gen_p4_align_fixtures.py")],
        capture_output=True, text=True, check=False,
    )
    assert r.returncode == 0, r.stdout + r.stderr
    assert (TOOLS / "fixtures" / "p4_align_transients_jittered.wav").exists()
    assert (TOOLS / "fixtures" / "p4_align_transients_periodic_CONTROL.wav").exists()


def _main() -> int:
    """Stdlib runner so this file executes without pytest installed."""
    fns = [(n, f) for n, f in sorted(globals().items())
           if n.startswith("test_") and callable(f)]
    failures = 0
    for name, fn in fns:
        try:
            fn()
            print(f"  PASS {name}")
        except Exception as exc:  # noqa: BLE001
            print(f"  FAIL {name}: {type(exc).__name__}: {exc}")
            failures += 1
    print(f"P4_ALIGN_STATIC={'PASS' if failures == 0 else 'FAIL'} "
          f"tests={len(fns)} failures={failures}")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(_main())
