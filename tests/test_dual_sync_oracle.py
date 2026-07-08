"""Host-only pytest for the dual-K1 sync timing oracle (scripts/dual_sync_probe).

The load-bearing claim: an undetected injected fault must be impossible to
merge. This suite is the Gate-0 fault battery — for every fault class the oracle
must (a) report the measured value within a characterised tolerance of the
injected truth AND (b) flip the corresponding gate to fail, while the clean run
passes every gate. Plus parser robustness and a byte-identical determinism
contract.

Pure host analysis: no devices, no serial, no network. Runs in well under 10 s.
"""

from __future__ import annotations

import dataclasses
import os
import sys

# Make scripts/dual_sync_probe importable as a package (it uses relative imports).
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_ROOT, "scripts"))

from dual_sync_probe import correlate, gate_eval, logfmt, synth  # noqa: E402
from dual_sync_probe.synth import SynthParams  # noqa: E402

SEED = 20260708


def _clean() -> SynthParams:
    """A healthy run that must pass every gate under default thresholds."""
    return SynthParams()


def _fault(**overrides) -> SynthParams:
    return dataclasses.replace(_clean(), **overrides)


def _correlate(params, seed=SEED):
    lead, foll = synth.generate_log_pair(params, seed=seed)
    return correlate.correlate(logfmt.parse_log(lead), logfmt.parse_log(foll))


def _evaluate(params, seed=SEED, **thresholds):
    lead, foll = synth.generate_log_pair(params, seed=seed)
    return gate_eval.evaluate(lead, foll, **thresholds)


# --------------------------------------------------------------------------- #
# (a) Parser robustness                                                       #
# --------------------------------------------------------------------------- #


def test_parse_line_valid_records():
    assert logfmt.parse_line("[sync_oracle] trig_out seq=7 t_us=12345") == logfmt.TrigOut(7, 12345)
    assert logfmt.parse_line("[sync_oracle] trig_in seq=7 t_us=12350") == logfmt.TrigIn(7, 12350)
    assert logfmt.parse_line("[k1_sync] clk est_offset_us=-42 rtt_us=8000 n=16") == logfmt.Clk(-42, 8000, 16)
    assert logfmt.parse_line("[k1_sync] tx seq=3 t_leader_us=999") == logfmt.Tx(3, 999)
    assert logfmt.parse_line("[k1_sync] rx seq=3 t_leader_us=999 t_local_us=5000999") == logfmt.Rx(3, 999, 5000999)
    assert logfmt.parse_line("[k1_sync] apply seq=3 t_render_us=5012000") == logfmt.Apply(3, 5012000)
    h = logfmt.parse_line("[k1_sync] health fps=99.50 heap_min=60000 ap_p95_us=700 dial_linked=1 loss=0 dup=0")
    assert h == logfmt.Health(99.5, 60000, 700, 1, 0, 0)


def test_parse_line_tolerates_serial_prefix_noise():
    # a serial monitor timestamp prefix must not defeat the parse
    rec = logfmt.parse_line("14:02:11.317 > [k1_sync] tx seq=88 t_leader_us=42")
    assert rec == logfmt.Tx(88, 42)


def test_parse_line_rejects_noise_and_truncation():
    assert logfmt.parse_line("I (123) wifi: chatter") is None
    assert logfmt.parse_line("") is None
    assert logfmt.parse_line("[k1_sync] rx seq=5 t_leader_us=100") is None  # missing t_local_us
    assert logfmt.parse_line("[sync_oracle] trig_out seq= t_us=") is None   # truncated fields
    assert logfmt.parse_line("[k1_sync] health fps=99 heap_min=60000") is None  # truncated


def test_parse_log_counts_skipped_noise():
    params = _fault(duration_s=10.0, noise_lines=25)
    lead, foll = synth.generate_log_pair(params, seed=SEED)
    pl = logfmt.parse_log(lead)
    pf = logfmt.parse_log(foll)
    # every injected noise line is unparseable -> counted as skipped, not fatal
    assert pl.skipped_lines == 25
    assert pf.skipped_lines == 25
    # and real records still parsed through the noise
    assert any(isinstance(r, logfmt.Tx) for r in pl.records)
    assert any(isinstance(r, logfmt.Apply) for r in pf.records)


# --------------------------------------------------------------------------- #
# (c) Clean-run battery — all gates pass on default thresholds                #
# --------------------------------------------------------------------------- #


def test_clean_run_passes_all_gates():
    v = _evaluate(_clean())
    assert v["gate1_clock_err"]["pass"], v["gate1_clock_err"]
    assert v["gate2_lateness"]["pass"], v["gate2_lateness"]
    assert v["gate3_e2e"]["pass"], v["gate3_e2e"]
    assert v["gate4_health"]["pass"], v["gate4_health"]
    assert v["overall"] is True


def test_clean_wire_truth_recovers_offset_and_asymmetry():
    c = _correlate(_clean())
    assert len(c.rounds) > 100
    # O_hat must recover the true offset (5,000,000 µs) essentially exactly
    offs = [r.offset_us for r in c.rounds]
    assert abs(correlate.mean(offs) - 5_000_000) < 5.0
    # symmetric ISR latency -> the asymmetry bound recovers isr_latency_us (3)
    asym = correlate.mean([r.asymmetry_us for r in c.rounds])
    assert abs(asym - 3.0) < 1.0


# --------------------------------------------------------------------------- #
# (b) GATE-0 FAULT BATTERY — every injected fault is detected AND flips a gate #
# --------------------------------------------------------------------------- #


def _median_lateness(params):
    c = _correlate(params)
    return correlate.percentile(c.apply_lateness_us, 50.0)


def test_fault_apply_delay_5ms_detected_and_flips_gate2():
    clean_med = _median_lateness(_clean())
    faulted = _fault(apply_delay_us=5000.0)
    faulted_med = _median_lateness(faulted)
    # detection: median lateness moved by the injected +5 ms within tolerance
    assert abs((faulted_med - clean_med) - 5000.0) < 500.0
    # gate flip: at a threshold set to the design margin, clean passes, fault fails.
    # (+5 ms systematic render delay is a real regression; a 16 ms p99.9 budget
    # catches it while the clean ~13 ms run passes.)
    v_clean = _evaluate(_clean(), lateness_p999_us=16000)
    v_fault = _evaluate(faulted, lateness_p999_us=16000)
    assert v_clean["gate2_lateness"]["pass"] is True
    assert v_fault["gate2_lateness"]["pass"] is False


def test_fault_apply_delay_20ms_detected_and_flips_gate2_default():
    clean_med = _median_lateness(_clean())
    faulted = _fault(apply_delay_us=20000.0)
    faulted_med = _median_lateness(faulted)
    assert abs((faulted_med - clean_med) - 20000.0) < 500.0
    v = _evaluate(faulted)  # default lateness_p999_us = 30000
    assert v["gate2_lateness"]["pass"] is False
    assert v["gate2_lateness"]["value_us"] > 30000


def test_fault_clock_bias_6ms_detected_and_flips_gate1():
    faulted = _fault(clock_bias_us=6000.0)
    c = _correlate(faulted)
    mean_err = correlate.mean([e for _, e in c.clock_error_series])
    # detection: mean clock error recovers the injected +6 ms bias
    assert abs(mean_err - 6000.0) < 500.0
    v = _evaluate(faulted)  # default clock_err_p95_us = 4000
    assert v["gate1_clock_err"]["pass"] is False
    assert v["gate1_clock_err"]["value_us"] > 4000


def test_fault_clock_drift_40us_per_s_detected_and_flips_gate1():
    # drift that the clock-sync fails to track; over a long enough run the
    # accumulated error breaches the 4 ms p95 gate.
    faulted = _fault(duration_s=150.0, drift_us_per_s=40.0, clock_est_drift_us_per_s=0.0)
    c = _correlate(faulted)
    slope = correlate.clock_error_slope_us_per_s(c.clock_error_series)
    # detection: recovered slope matches the injected -40 µs/s within tolerance
    assert slope is not None
    assert abs(slope - (-40.0)) < 5.0
    v = _evaluate(faulted)
    assert v["gate1_clock_err"]["pass"] is False
    # clean at the same long duration must still pass gate 1 (isolates the fault)
    v_clean = _evaluate(_fault(duration_s=150.0))
    assert v_clean["gate1_clock_err"]["pass"] is True


def test_fault_packet_loss_5pct_detected_and_flips_gate4():
    faulted = _fault(loss_frac=0.05)
    c = _correlate(faulted)
    assert c.stream_expected > 0
    loss_frac = c.loss / c.stream_expected
    # detection: measured loss fraction is close to the injected 5 %
    assert abs(loss_frac - 0.05) < 0.02
    v = _evaluate(faulted)  # default stream_loss_max = 0
    assert v["gate4_health"]["pass"] is False
    assert v["gate4_health"]["subgates"]["stream_loss"]["pass"] is False


def test_fault_lateness_tail_detected_and_flips_gate2_and_gate3():
    clean_med = _median_lateness(_clean())
    faulted = _fault(lateness_tail_us=40000.0, lateness_tail_frac=0.02)
    c = _correlate(faulted)
    p999 = correlate.percentile(c.apply_lateness_us, 99.9)
    # detection: the p99.9 tail lands ~one tail-height above the typical latency
    assert abs((p999 - clean_med) - 40000.0) < 4000.0
    v = _evaluate(faulted)  # defaults: lateness 30000, e2e 50000
    assert v["gate2_lateness"]["pass"] is False   # p99.9 breaches D
    assert v["gate3_e2e"]["pass"] is False        # worst-case breaches 50 ms


def test_fault_dial_dropout_detected_and_flips_gate4():
    faulted = _fault(dial_drop_frac=0.2)
    c = _correlate(faulted)
    # detection: dial uptime recovers ~(1 - drop_frac)
    assert c.dial_uptime is not None
    assert abs(c.dial_uptime - 0.8) < 0.12
    v = _evaluate(faulted)  # default dial_uptime_min = 1.0
    assert v["gate4_health"]["pass"] is False
    assert v["gate4_health"]["subgates"]["dial_uptime"]["pass"] is False


# --------------------------------------------------------------------------- #
# (d) Determinism contract — same seed => byte-identical gate_eval JSON        #
# --------------------------------------------------------------------------- #


def test_determinism_same_seed_byte_identical_json():
    lead1, foll1 = synth.generate_log_pair(_clean(), seed=SEED)
    lead2, foll2 = synth.generate_log_pair(_clean(), seed=SEED)
    # generator itself is deterministic
    assert lead1 == lead2
    assert foll1 == foll2
    # and the whole verdict serialises byte-identically
    j1 = gate_eval.to_json(gate_eval.evaluate(lead1, foll1))
    j2 = gate_eval.to_json(gate_eval.evaluate(lead2, foll2))
    assert j1 == j2
    # re-evaluating the SAME text is also byte-identical (no run-time-of-day leak)
    assert gate_eval.to_json(gate_eval.evaluate(lead1, foll1)) == j1


def test_different_seed_changes_realisation_but_not_verdict_shape():
    v_a = gate_eval.evaluate(*synth.generate_log_pair(_clean(), seed=1))
    v_b = gate_eval.evaluate(*synth.generate_log_pair(_clean(), seed=2))
    # both clean runs still pass every gate regardless of seed
    assert v_a["overall"] is True and v_b["overall"] is True
    # same key structure
    assert set(v_a) == set(v_b)


def test_json_is_sorted_and_stable():
    v = _evaluate(_clean())
    txt = gate_eval.to_json(v)
    # sorted keys => top-level keys appear in sorted order
    import json
    reparsed = json.loads(txt)
    assert list(reparsed.keys()) == sorted(reparsed.keys())
    assert txt.endswith("\n")
