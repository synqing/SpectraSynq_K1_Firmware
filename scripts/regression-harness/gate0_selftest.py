#!/usr/bin/env python3
"""Gate-0 fault-injection self-test for wireless_ab_bench.py admission gates.

NAMING (avoid confusion): "Gate 0" here is the HARNESS fault-evidence selftest.
It is NOT the K718/Remoted battery state-of-charge gate — that is a separate
physical lane and is NOT closed by this file. "GREEN" below means the harness
selftest passed, never that the device battery SoC gate passed.

doctrine: autonomous-agentic-build § "Gate 0 — prove the harness is FAULT-EVIDENT
before any retest". This fault-injection suite feeds the hardened bench the KNOWN-BAD captures
(the real cb1 DOWNLOAD-reset + cb2 USB-wedge that invalidated both counterbalanced
retests) plus synthetic edge cases that isolate each gate, and REQUIRES the bench
to mark every one INVALID — while still admitting every valid capture. An uncaught
bad capture is NOT a pass: it is a located oracle blind spot -> widen the gate.

These are VALIDITY-ADMISSION checks only. They do NOT touch the pre-registered
A/B pass/fail thresholds. Run before any counterbalanced retest; a human signs
Gate 0 off the green result.

    python3 scripts/regression-harness/gate0_selftest.py    # exit 0 = harness suite GREEN

No device, no network, no afplay — pure static fixtures.
"""
from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
BENCH = HERE / "wireless_ab_bench.py"
FIXTURES = HERE / "fixtures" / "bad-captures"

_spec = importlib.util.spec_from_file_location("wireless_ab_bench", BENCH)
wab = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(wab)


# ---------------------------------------------------------------------------
# Synthetic payload factory (deterministic; no RNG, no clock)
# ---------------------------------------------------------------------------
def valid_metrics(ap_samples: int = 95) -> dict:
    return {
        "lines_total": 480,
        "garbage_lines": 0,
        "crash_markers": 0,
        "ap_cadence": {
            "samples": ap_samples, "mean_gap_s": 1.005, "median_gap_s": 1.005,
            "max_gap_s": 1.013, "p95_jitter_ms": 2.3,
        },
        "beat": {
            "conf_mean_all": 0.88, "conf_mean_active": 0.88, "lock_ratio_active": 0.88,
            "bpm_mean_locked": 120.0, "bpm_std_locked": 0.15, "bpm_abs_err_vs_120": 0.02,
            "locked_samples": 80, "active_samples": ap_samples,
        },
        "onset": {"onset_sampled_count": 34, "bass_sampled_count": 6, "ostr_mean": 0.006, "bstr_mean": 0.84},
        "peak_scaled": {"mean": 0.18, "p95": 0.86, "hist_counts": [60, 25, 5, 1, 1, 1, 1, 0, 3, 5],
                        "hist_edges": [round(i * 0.1, 1) for i in range(11)]},
        "apcap": {"windows": 17, "peak_scaled_window_max": None},
        "render": {"surface": "vpf_frame_us", "resolution": "full-frame-rate", "p95_us": 4000.0,
                   "mean_us": 3900.0, "max_us": 5200.0},
        "vpf": {"reports": 90, "seq_gaps": 0},
    }


def valid_payload(metrics: dict | None = None, **over) -> dict:
    payload = {
        "tool": "wireless_ab_bench", "condition": "on", "index": 1,
        "port": "/dev/cu.usbmodemSYNTH", "identity": {"chip_id": "F887A500", "version": "40103"},
        "failure": None, "post_run_alive": True, "raw_log": None,
        "metrics": metrics if metrics is not None else valid_metrics(),
    }
    payload.update(over)
    return payload


# A minimal live-app log: an [AP] line precedes the stimulus -> APP_READY ok.
LOG_APP_READY = "[1.0] [AP] SSL=421 peak_scaled=0.18 silence=0 | bpm=120 conf=0.8 lock=1\n[2.0] #AFPLAY_START stim.wav\n"
# afplay reached with NO prior [AP] -> APP_READY reject (dead/booting device).
LOG_NO_AP = "[0.1] >>> :ap_stream=on\n[0.5] #AFPLAY_START stim.wav\n"
# device dropped to download mode mid-capture -> DOWNLOAD reject.
LOG_DOWNLOAD = ("[1.0] [AP] SSL=421 peak_scaled=0.18 silence=0 | bpm=120 conf=0.8 lock=1\n"
                "[2.0] #AFPLAY_START stim.wav\n"
                "[5.0] ESP-ROM:esp32s3-20210327\n"
                "[5.0] rst:0x15 (USB_UART_CHIP_RESET),boot:0x0 (DOWNLOAD(USB/UART0))\n"
                "[5.1] waiting for download\n")


# ---------------------------------------------------------------------------
# Suite: (label, payload, log_text, expect_admitted, expect_reason_substrings)
# ---------------------------------------------------------------------------
def fault_injection_cases() -> list[tuple]:
    cases: list[tuple] = []

    # --- real frozen evidence (the captures that broke both retests) ---
    for fx in sorted(FIXTURES.glob("*.json")):
        d = json.loads(fx.read_text())
        g = d.get("_gate0") or {}
        cases.append((f"REAL {fx.name}", d, None, g.get("expect_admitted"), g.get("expect_reasons", [])))

    # --- synthetic isolators (each trips exactly one gate class) ---
    cases.append(("SYNTH good_minimal", valid_payload(), None, True, []))
    cases.append(("SYNTH truncated (U4)", valid_payload(valid_metrics(ap_samples=40)), None, False, ["AP_FLOOR"]))
    no_render = valid_metrics()
    no_render["render"] = {"surface": None, "resolution": None, "p95_us": None, "mean_us": None, "max_us": None}
    cases.append(("SYNTH no_render (U5)", valid_payload(no_render), None, False, ["COMPLETENESS"]))
    cases.append(("SYNTH wrong_device (U6)", valid_payload(identity={"chip_id": "DEADBEEF", "version": "40103"}),
                  None, False, ["IDENTITY"]))
    cases.append(("SYNTH peak_none (U5)", valid_payload({**valid_metrics(), "peak_scaled": {"mean": None, "p95": None,
                  "hist_counts": [0] * 10, "hist_edges": [round(i * 0.1, 1) for i in range(11)]}}),
                  None, False, ["COMPLETENESS"]))
    cases.append(("SYNTH post_run_dead (U7)", valid_payload(post_run_alive=False), None, False, ["LIVENESS"]))

    # --- log-gated cases (U3 app-ready / U6 download-marker) ---
    cases.append(("SYNTH app_ready_ok (U3)", valid_payload(), LOG_APP_READY, True, []))
    cases.append(("SYNTH no_ap_before_afplay (U3)", valid_payload(), LOG_NO_AP, False, ["APP_READY"]))
    cases.append(("SYNTH download_in_log (U6)", valid_payload(), LOG_DOWNLOAD, False, ["DOWNLOAD"]))

    return cases


def run_admission_suite() -> list[str]:
    failures: list[str] = []
    print("=== Harness Gate-0 admission suite (fault-injection) ===")
    for label, payload, log_text, expect_admitted, expect_reasons in fault_injection_cases():
        verdict = wab.admit_capture(payload, log_text=log_text)
        got = verdict["admitted"]
        reasons = "; ".join(verdict["reasons"])
        ok = (got == expect_admitted)
        # for a rejection, also require it was caught for the RIGHT reason class
        if not expect_admitted:
            for substr in expect_reasons:
                if substr not in reasons:
                    ok = False
                    failures.append(f"{label}: expected reason '{substr}' missing (got: {reasons or 'NONE'})")
        if got != expect_admitted:
            failures.append(f"{label}: admitted={got} expected={expect_admitted} (reasons: {reasons or 'NONE'})")
        flag = "ok " if ok else "XX "
        print(f"  {flag}{label:34s} admitted={got!s:5s} {('['+reasons+']') if reasons else ''}"[:118])
    return failures


def run_compare_integration() -> list[str]:
    """End-to-end: the CLI compare must return INVALID (exit 2) for any set that
    contains a non-admitted capture, and must NOT return INVALID for an all-good
    set. This is the trust-root: no PASS/FAIL verdict from corrupted data."""
    failures: list[str] = []
    good = str(FIXTURES / "good_test1_on_1.json")
    bad = str(FIXTURES / "bad_cb1_off2_download_reset.json")

    def compare_exit(off: list[str], on: list[str]) -> int:
        return subprocess.run(
            [sys.executable, str(BENCH), "compare", "--off", *off, "--on", *on],
            capture_output=True, text=True,
        ).returncode

    print("=== Gate-0 compare integration ===")
    rc_bad = compare_exit([good, bad], [good])
    print(f"  compare(set with bad cb1)         -> exit {rc_bad} (expect 2=INVALID)")
    if rc_bad != 2:
        failures.append(f"compare with bad capture returned {rc_bad}, expected 2 (INVALID)")
    rc_good = compare_exit([good], [good])
    print(f"  compare(all-admitted set)         -> exit {rc_good} (expect 0/1, NOT 2)")
    if rc_good == 2:
        failures.append("compare on an all-admitted set wrongly returned INVALID (exit 2)")
    return failures


def main() -> int:
    failures = run_admission_suite() + run_compare_integration()
    print("-" * 60)
    if failures:
        print("Harness Gate 0 selftest: RED — %d blind spot(s) located:" % len(failures))
        for f in failures:
            print("  - " + f)
        return 1
    print("Harness Gate 0 selftest: GREEN — every known-bad capture rejected, every valid")
    print("capture admitted, compare refuses PASS/FAIL on any set with a rejected capture.")
    print("(HARNESS gate only — NOT the K718/Remoted battery SoC gate, which stays separate.)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
