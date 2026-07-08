"""Gate evaluator: two device logs in, the four Phase-0 sync gate numbers out,
as a deterministic JSON verdict.

Gates (probe-log-contract.md §2):

  gate1_clock_err  p95(|est_offset - wire_truth|)   <= clock_err_p95_us (4000)
  gate2_lateness   p99.9(apply_lateness)            <= lateness_p999_us (D=30000)
  gate3_e2e        max(apply_lateness)  (worst-case follower end-to-end)
                                                     <= e2e_us          (50000)
  gate4_health     composite: fps floor, heap floor, AP p95 ceiling,
                   dial-link uptime, stream loss                        (see defaults)

gate2 asks "does the leader-stamp->apply path fit the design delay-line budget
D"; gate3 asks "is the worst observed follower end-to-end under the absolute
50 ms perceptual ceiling regardless of D". They score the same measured
quantity at different statistics and thresholds, so they fail independently.

A gate whose evidence is absent (empty series) FAILS CLOSED — you cannot certify
a number you did not measure.

Deterministic by construction: no randomness, no run-time-of-day, integer µs,
fixed float rounding, ``sort_keys=True``.
"""

from __future__ import annotations

import argparse
import json
import sys
from typing import Optional

from . import correlate as _corr
from . import logfmt

# ----- default thresholds -------------------------------------------------- #
DEFAULT_CLOCK_ERR_P95_US = 4000
DEFAULT_LATENESS_P999_US = 30000  # == delay-line depth D
DEFAULT_E2E_US = 50000
DEFAULT_D_US = 30000
# gate4 health sub-thresholds
DEFAULT_FPS_FLOOR = 90.0
DEFAULT_HEAP_MIN_FLOOR = 20000
DEFAULT_AP_P95_US_MAX = 7500
DEFAULT_DIAL_UPTIME_MIN = 1.0
DEFAULT_STREAM_LOSS_MAX = 0


def _r_us(x: Optional[float]) -> Optional[int]:
    return None if x is None else int(round(x))


def _r6(x: Optional[float]) -> Optional[float]:
    return None if x is None else round(x, 6)


def evaluate(
    leader_text,
    follower_text,
    clock_err_p95_us: int = DEFAULT_CLOCK_ERR_P95_US,
    lateness_p999_us: int = DEFAULT_LATENESS_P999_US,
    e2e_us: int = DEFAULT_E2E_US,
    d_us: int = DEFAULT_D_US,
    fps_floor: float = DEFAULT_FPS_FLOOR,
    heap_min_floor: int = DEFAULT_HEAP_MIN_FLOOR,
    ap_p95_us_max: int = DEFAULT_AP_P95_US_MAX,
    dial_uptime_min: float = DEFAULT_DIAL_UPTIME_MIN,
    stream_loss_max: int = DEFAULT_STREAM_LOSS_MAX,
) -> dict:
    """Evaluate the four gates over a leader + follower log pair (strings or
    line iterables). Returns a JSON-serialisable, deterministic verdict dict."""
    leader = logfmt.parse_log(leader_text)
    follower = logfmt.parse_log(follower_text)
    c = _corr.correlate(leader, follower)

    # gate 1 — clock-offset error (p95 of absolute error)
    abs_err = [abs(e) for _, e in c.clock_error_series]
    g1_val = _corr.percentile(abs_err, 95.0)
    g1 = {
        "value_us": _r_us(g1_val),
        "threshold_us": clock_err_p95_us,
        "pass": (g1_val is not None and g1_val <= clock_err_p95_us),
        "n": len(abs_err),
    }

    # gate 2 — packet lateness p99.9 vs D
    g2_val = _corr.percentile(c.apply_lateness_us, 99.9)
    g2 = {
        "value_us": _r_us(g2_val),
        "threshold_us": lateness_p999_us,
        "pass": (g2_val is not None and g2_val <= lateness_p999_us),
        "n": len(c.apply_lateness_us),
    }

    # gate 3 — worst-case follower end-to-end (max apply lateness)
    g3_val = max(c.apply_lateness_us) if c.apply_lateness_us else None
    g3 = {
        "value_us": _r_us(g3_val),
        "threshold_us": e2e_us,
        "pass": (g3_val is not None and g3_val <= e2e_us),
        "n": len(c.apply_lateness_us),
    }

    # gate 4 — health composite
    subs = {
        "fps_min": {
            "value": (None if c.fps_min is None else round(c.fps_min, 2)),
            "floor": fps_floor,
            "pass": (c.fps_min is not None and c.fps_min >= fps_floor),
        },
        "heap_min": {
            "value": c.heap_min,
            "floor": heap_min_floor,
            "pass": (c.heap_min is not None and c.heap_min >= heap_min_floor),
        },
        "ap_p95_us": {
            "value": c.ap_p95_max,
            "ceiling": ap_p95_us_max,
            "pass": (c.ap_p95_max is not None and c.ap_p95_max <= ap_p95_us_max),
        },
        "dial_uptime": {
            "value": _r6(c.dial_uptime),
            "floor": dial_uptime_min,
            "pass": (c.dial_uptime is not None and c.dial_uptime >= dial_uptime_min),
        },
        "stream_loss": {
            "value": c.loss,
            "ceiling": stream_loss_max,
            "pass": (c.loss <= stream_loss_max),
        },
    }
    g4_pass = c.health_samples > 0 and all(s["pass"] for s in subs.values())
    g4 = {"pass": g4_pass, "health_samples": c.health_samples, "subgates": subs}

    verdict = {
        "gate1_clock_err": g1,
        "gate2_lateness": g2,
        "gate3_e2e": g3,
        "gate4_health": g4,
        "overall": bool(g1["pass"] and g2["pass"] and g3["pass"] and g4["pass"]),
        "diagnostics": {
            "trig_rounds": len(c.rounds),
            "incomplete_rounds": c.incomplete_rounds,
            "stream_expected": c.stream_expected,
            "stream_dup": c.dup,
            "stream_reorder": c.reorder,
            "apply_unmatched": c.unmatched_apply,
            "wire_asymmetry_p95_us": _r_us(
                _corr.percentile([abs(r.asymmetry_us) for r in c.rounds], 95.0)
            ),
            "leader_lines_total": leader.total_lines,
            "leader_lines_skipped": leader.skipped_lines,
            "follower_lines_total": follower.total_lines,
            "follower_lines_skipped": follower.skipped_lines,
        },
    }
    return verdict


def to_json(verdict: dict) -> str:
    """Canonical deterministic JSON: sorted keys, 2-space indent, trailing
    newline. Byte-identical for identical input."""
    return json.dumps(verdict, sort_keys=True, indent=2) + "\n"


def format_summary(verdict: dict) -> str:
    """Human-readable one-screen summary."""
    lines = []
    lines.append("Dual-K1 sync gate verdict")
    lines.append("=" * 40)

    def _row(name, g, unit="µs"):
        val = g.get("value_us")
        thr = g.get("threshold_us")
        mark = "PASS" if g["pass"] else "FAIL"
        vs = "n/a" if val is None else f"{val} {unit}"
        return f"  [{mark}] {name}: {vs} (limit {thr} {unit}, n={g.get('n', '-')})"

    lines.append(_row("gate1 clock-err p95", verdict["gate1_clock_err"]))
    lines.append(_row("gate2 lateness p99.9", verdict["gate2_lateness"]))
    lines.append(_row("gate3 e2e worst-case", verdict["gate3_e2e"]))
    g4 = verdict["gate4_health"]
    lines.append(f"  [{'PASS' if g4['pass'] else 'FAIL'}] gate4 health "
                 f"(samples={g4['health_samples']})")
    for sub_name, sub in sorted(g4["subgates"].items()):
        mark = "PASS" if sub["pass"] else "FAIL"
        lines.append(f"        [{mark}] {sub_name}: {sub['value']}")
    lines.append("-" * 40)
    lines.append(f"  OVERALL: {'PASS' if verdict['overall'] else 'FAIL'}")
    d = verdict["diagnostics"]
    lines.append(
        f"  trig_rounds={d['trig_rounds']} "
        f"incomplete={d['incomplete_rounds']} "
        f"loss={verdict['gate4_health']['subgates']['stream_loss']['value']} "
        f"dup={d['stream_dup']} reorder={d['stream_reorder']} "
        f"asym_p95={d['wire_asymmetry_p95_us']}µs"
    )
    return "\n".join(lines)


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="gate_eval",
        description="Evaluate the four dual-K1 sync gates over a leader + "
        "follower serial log pair. Deterministic JSON verdict on stdout.",
    )
    p.add_argument("leader_log", help="path to the leader (main K1) serial log")
    p.add_argument("follower_log", help="path to the follower (bench K1) serial log")
    p.add_argument("--clock-err-p95-us", type=int, default=DEFAULT_CLOCK_ERR_P95_US)
    p.add_argument("--lateness-p999-us", type=int, default=DEFAULT_LATENESS_P999_US)
    p.add_argument("--e2e-us", type=int, default=DEFAULT_E2E_US)
    p.add_argument("--d-us", type=int, default=DEFAULT_D_US)
    p.add_argument("--fps-floor", type=float, default=DEFAULT_FPS_FLOOR)
    p.add_argument("--heap-min-floor", type=int, default=DEFAULT_HEAP_MIN_FLOOR)
    p.add_argument("--ap-p95-us-max", type=int, default=DEFAULT_AP_P95_US_MAX)
    p.add_argument("--dial-uptime-min", type=float, default=DEFAULT_DIAL_UPTIME_MIN)
    p.add_argument("--stream-loss-max", type=int, default=DEFAULT_STREAM_LOSS_MAX)
    p.add_argument(
        "--summary",
        action="store_true",
        help="also print a human-readable summary to stderr",
    )
    return p


def main(argv=None) -> int:
    args = _build_parser().parse_args(argv)
    with open(args.leader_log, "r", encoding="utf-8", errors="replace") as fh:
        leader_text = fh.read()
    with open(args.follower_log, "r", encoding="utf-8", errors="replace") as fh:
        follower_text = fh.read()
    verdict = evaluate(
        leader_text,
        follower_text,
        clock_err_p95_us=args.clock_err_p95_us,
        lateness_p999_us=args.lateness_p999_us,
        e2e_us=args.e2e_us,
        d_us=args.d_us,
        fps_floor=args.fps_floor,
        heap_min_floor=args.heap_min_floor,
        ap_p95_us_max=args.ap_p95_us_max,
        dial_uptime_min=args.dial_uptime_min,
        stream_loss_max=args.stream_loss_max,
    )
    sys.stdout.write(to_json(verdict))
    if args.summary:
        sys.stderr.write(format_summary(verdict) + "\n")
    return 0 if verdict["overall"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
