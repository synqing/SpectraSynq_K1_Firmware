"""G2_TEMPO_BEHAVIOURAL_EQUIVALENCE_V1 host gate.

Spread ACF is the regression control, not ground truth.
Fixture click/silence trains are the behavioural oracle.
B489 flash remains HOLD until this gate, the Goertzel exact subgate,
and the 1.8 ms feasibility stop all pass.
"""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

HARNESS = Path(__file__).resolve().parents[1] / "scripts" / "regression-harness"
sys.path.insert(0, str(HARNESS))
import tempo_replay as trp  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
PACK = ROOT / "docs/forensics/runtime-evidence/20260816T-g2-tempo-behavioural-equivalence-v1"
TEMPO_CPP = ROOT / "SPECTRASYNQ_K1_FIRMWARE" / "audio" / "k1_tempo.cpp"
FPS = 12800.0 / 96.0
AP_HOP_US = 7.5e3
LOCK_CONF = 0.60
DIR_CONF = 0.45
IDLE_CONF = 0.30
PRISM_STRENGTH = 0.55

PROD = [
    "K1_TEMPO_CONF_V2",
    "K1_TEMPO_FLYWHEEL_V2",
    "K1_TEMPO_ACF_SPREAD_V1=1",
    "DEFAULT_SAMPLE_RATE=12800",
    "DEFAULT_SAMPLES_PER_CHUNK=96",
    "K1_TEMPO_NOVELTY_DECIMATION=3U",
]

DRIVER = r"""
#include "k1_tempo.h"
#include <cstdio>
void k1_tempo_debug_dump_raw(float*, int);
static K1AudioSnapshot mk(uint32_t ms, float novelty, bool silence) {
  K1AudioSnapshot a = {};
  a.frame_ms = ms; a.novelty = novelty; a.silence = silence;
  return a;
}
int main() {
  k1_tempo_init();
  char line[160];
  while (std::fgets(line, sizeof(line), stdin)) {
    unsigned int ms = 0; float nov = 0.0f; int sil = 0;
    if (std::sscanf(line, "%u %f %d", &ms, &nov, &sil) < 2) continue;
    k1_tempo_update(mk(ms, nov, sil != 0));
    K1TempoEvent e = k1_tempo_read();
    std::printf("T %u %.1f %.8f %d %.8f %d %.8f %d\n",
                ms, e.bpm, e.confidence, e.locked ? 1 : 0, e.phase01,
                e.beat_tick ? 1 : 0, e.beat_strength, sil);
  }
  float raw[96];
  k1_tempo_debug_dump_raw(raw, 96);
  std::printf("GOERTZEL_RAW");
  for (int i = 0; i < 96; i++) std::printf(" %.9g", raw[i]);
  std::printf("\n");
  return 0;
}
"""


def _build(defines: list[str], workdir: Path) -> Path:
    workdir.mkdir(parents=True, exist_ok=True)
    stub = workdir / "stub"
    stub.mkdir(exist_ok=True)
    (stub / "Arduino.h").write_text(trp.ARDUINO_STUB, encoding="utf-8")
    main_cpp = workdir / "main.cpp"
    binary = workdir / "tempo_beh"
    main_cpp.write_text(DRIVER, encoding="utf-8")
    cmd = [
        "clang++", "-std=c++17", "-Wall", "-Wextra", "-ffp-contract=off",
        "-DK1_TEMPO_HOST_TEST",
    ]
    cmd += ["-D" + d for d in defines]
    cmd += [
        "-I", str(stub), "-I", str(trp.FIRMWARE),
        "-I", str(trp.FIRMWARE / "audio"), "-I", str(trp.FIRMWARE / "system"),
        str(TEMPO_CPP), str(main_cpp), "-o", str(binary),
    ]
    result = subprocess.run(cmd, cwd=ROOT, text=True, capture_output=True)
    assert result.returncode == 0, result.stderr + result.stdout
    return binary


def _replay(binary: Path, text: str) -> tuple[list[dict], list[float]]:
    result = subprocess.run(
        [str(binary)], cwd=ROOT, text=True, input=text, capture_output=True
    )
    assert result.returncode == 0, result.stderr
    rows = []
    raw: list[float] = []
    for line in result.stdout.splitlines():
        if line.startswith("T "):
            p = line.split()
            rows.append({
                "ms": int(p[1]),
                "bpm": float(p[2]),
                "confidence": float(p[3]),
                "locked": int(p[4]),
                "phase01": float(p[5]),
                "beat_tick": int(p[6]),
                "beat_strength": float(p[7]),
                "silence": int(p[8]),
            })
        elif line.startswith("GOERTZEL_RAW"):
            raw = [float(x) for x in line.split()[1:]]
    return rows, raw


def _stream(frames: list[tuple[float, int]]) -> str:
    lines = []
    for index, (novelty, silence) in enumerate(frames):
        ms = int(index * 1000.0 / FPS + 0.5)
        lines.append(f"{ms} {novelty:.6f} {silence}")
    return "\n".join(lines) + "\n"


def _click(bpm: float, seconds: float, *, amplitude: float = 1.0, drop: float = 0.0, seed: int = 1) -> list[tuple[float, int]]:
    n = int(seconds * FPS)
    beat_ms = 60000.0 / bpm
    next_beat = 0.0
    state = seed & 0xFFFFFFFF
    frames = []
    for index in range(n):
        ms = index * 1000.0 / FPS
        nov = 0.0
        if ms + 1e-6 >= next_beat:
            next_beat += beat_ms
            state = (state * 1664525 + 1013904223) & 0xFFFFFFFF
            if (state / 0x100000000) >= drop:
                nov = amplitude
        frames.append((nov, 0))
    return frames


def _silence(seconds: float) -> list[tuple[float, int]]:
    return [(0.0, 1) for _ in range(int(seconds * FPS))]


def _flat(level: float, seconds: float) -> list[tuple[float, int]]:
    return [(level, 0) for _ in range(int(seconds * FPS))]


def _noise(seconds: float, seed: int = 99, amp: float = 0.04) -> list[tuple[float, int]]:
    n = int(seconds * FPS)
    state = seed & 0xFFFFFFFF
    frames = []
    for _ in range(n):
        state = (state * 1664525 + 1013904223) & 0xFFFFFFFF
        frames.append((amp * (state / 0x100000000), 0))
    return frames


def fixtures() -> dict[str, dict]:
    out: dict[str, dict] = {}
    out["silence_then_exit"] = {
        "stream": _stream(_silence(4.0) + _click(120.0, 20.0)),
        "kind": "silence_then_train",
        "target_bpm": 120.0,
        "silence_end_ms": 4000,
    }
    for bpm in (60, 90, 112, 120, 128, 144):
        out[f"steady_{int(bpm)}"] = {
            "stream": _stream(_click(float(bpm), 24.0)),
            "kind": "stationary",
            "target_bpm": float(bpm),
        }
    out["double_time_ambiguity"] = {
        "stream": _stream(_click(120.0, 16.0) + _click(60.0, 16.0)),
        "kind": "jump",
        "target_bpm": 60.0,
        "jump_ms": 16000,
        "pre_bpm": 120.0,
    }
    out["abrupt_bpm_change"] = {
        "stream": _stream(_click(90.0, 16.0) + _click(128.0, 16.0)),
        "kind": "jump",
        "target_bpm": 128.0,
        "jump_ms": 16000,
        "pre_bpm": 90.0,
    }
    out["weak_intermittent"] = {
        "stream": _stream(_click(120.0, 24.0, amplitude=0.35, drop=0.35, seed=7)),
        "kind": "dropout",
        "target_bpm": 120.0,
    }
    for offset in (0, 1, 2):
        frames = [(0.0, 0)] * offset + _click(120.0, 24.0)
        out[f"phase_cross_offset_{offset}"] = {
            "stream": _stream(frames),
            "kind": "stationary",
            "target_bpm": 120.0,
        }
    out["lock_acquire_release"] = {
        "stream": _stream(_click(120.0, 20.0) + _silence(4.0)),
        "kind": "release",
        "target_bpm": 120.0,
        "silence_start_ms": 20000,
    }
    out["novelty_ring_wrap"] = {
        "stream": _stream(_click(112.0, 24.0)),
        "kind": "stationary",
        "target_bpm": 112.0,
    }
    out["long_consecutive"] = {
        "stream": _stream(_click(120.0, 30.0)),
        "kind": "stationary",
        "target_bpm": 120.0,
        "dump_goertzel": True,
    }
    out["flat_then_train"] = {
        "stream": _stream(_flat(0.15, 4.0) + _click(120.0, 20.0)),
        "kind": "silence_then_train",
        "target_bpm": 120.0,
        "silence_end_ms": 4000,
        "silence_is_flat": True,
    }
    out["adversarial_noise"] = {
        "stream": _stream(_noise(8.0)),
        "kind": "noise",
        "target_bpm": None,
    }
    out["abrupt_82_to_108"] = {
        "stream": _stream(_click(82.0, 16.0) + _click(108.0, 16.0)),
        "kind": "jump",
        "target_bpm": 108.0,
        "jump_ms": 16000,
        "pre_bpm": 82.0,
    }
    return out


def _parse_clicks(text: str) -> list[int]:
    times = []
    for line in text.splitlines():
        if not line.strip():
            continue
        ms_s, nov_s, sil_s = line.split()
        if float(nov_s) > 0.0 and int(sil_s) == 0:
            times.append(int(ms_s))
    return times


def _bpm_close(value: float, target: float) -> bool:
    return abs(value - target) < 0.6


def _octave_wrong(value: float, target: float) -> bool:
    if _bpm_close(value, target):
        return False
    return _bpm_close(value, target * 2.0) or _bpm_close(value, target / 2.0)


def _first_correct_lock(rows: list[dict], target: float) -> int | None:
    for row in rows:
        if row["locked"] and _bpm_close(row["bpm"], target):
            return row["ms"]
    return None


def _ap_index_from_ms(ms: int) -> int:
    return int(round(ms * FPS / 1000.0))


def _ms_from_ap_index(index: int) -> int:
    return int(index * 1000.0 / FPS + 0.5)


def _emit_index_for_ap(ap_index: int) -> int:
    # Frame 0 primes and does not emit. Later emits are AP indices 3, 6, 9, ...
    if ap_index <= 0:
        return 3
    return ((ap_index + 2) // 3) * 3


def _novelty_beat_times(click_ms: list[int], n_frames: int) -> list[int]:
    """Map AP-frame clicks onto the peak-held novelty emit that actually feeds the tracker."""
    seen: set[int] = set()
    out: list[int] = []
    for ms in click_ms:
        emit = _emit_index_for_ap(_ap_index_from_ms(ms))
        if emit >= n_frames:
            continue
        t = _ms_from_ap_index(emit)
        if t not in seen:
            seen.add(t)
            out.append(t)
    return out


def _sorted_beat_report(truth: list[int], ticks: list[int]) -> dict:
    """Monotonic pairing: leftover |n_ticks-n_truth| is the count error; phase shows up as timing."""
    t = sorted(truth)
    k = sorted(ticks)
    n = min(len(t), len(k))
    errors_us = [abs(k[i] - t[i]) * 1000.0 for i in range(n)]
    return {
        "n_truth": len(t),
        "n_ticks": len(k),
        "count_delta": abs(len(k) - len(t)),
        "n_matched": n,
        "max_err_us": max(errors_us) if errors_us else 0.0,
        "p99_err_us": sorted(errors_us)[int(0.99 * (len(errors_us) - 1))] if errors_us else 0.0,
        "within_7500_us": sum(1 for e in errors_us if e <= AP_HOP_US),
        "median_err_us": sorted(errors_us)[len(errors_us) // 2] if errors_us else 0.0,
    }


def _unmatched(truth: list[int], ticks: list[int], window_ms: float) -> tuple[list[int], list[int]]:
    used = [False] * len(truth)
    extra: list[int] = []
    for tick in ticks:
        best = None
        best_d = window_ms + 1.0
        for i, click in enumerate(truth):
            if used[i]:
                continue
            d = abs(tick - click)
            if d < best_d:
                best_d = d
                best = i
        if best is None or best_d > window_ms:
            extra.append(tick)
        else:
            used[best] = True
    missing = [click for i, click in enumerate(truth) if not used[i]]
    return extra, missing


def _unlock_count(rows: list[dict]) -> int:
    unlocks = 0
    prev = 1
    for row in rows:
        if prev == 1 and row["locked"] == 0:
            unlocks += 1
        prev = row["locked"]
    return unlocks


def _wrong_locked(rows: list[dict], target: float) -> tuple[int, int]:
    wrong = [r for r in rows if r["locked"] and not _bpm_close(r["bpm"], target)]
    oct_wrong = [r for r in wrong if _octave_wrong(r["bpm"], target)]
    return len(wrong), len(oct_wrong)


def _product_gates(row: dict) -> dict[str, int]:
    conf = row["confidence"]
    return {
        "locked": row["locked"],
        "director_trust": int(row["locked"] == 1 and conf >= DIR_CONF),
        "conf_idle": int(conf < IDLE_CONF),
        "conf_full": int(conf >= LOCK_CONF),
        "beat_accept": int(row["beat_tick"] == 1 and row["locked"] == 1),
        "prism_spawn": int(
            row["locked"] == 1 and row["beat_tick"] == 1 and row["beat_strength"] > PRISM_STRENGTH
        ),
    }


def test_rolling_acf_behaviour_against_fixture_truth():
    cases = fixtures()
    failures: dict[str, list[str]] = {}
    fixture_rows: dict[str, dict] = {}
    goertzel_ok = None
    goertzel_max_abs = None
    with tempfile.TemporaryDirectory(prefix="tempo_beh_") as tmp:
        tmp_path = Path(tmp)
        reference = _build(PROD, tmp_path / "ref")
        candidate = _build(PROD + ["K1_TEMPO_ACF_INCREMENTAL_V1=1"], tmp_path / "cand")
        for name, spec in cases.items():
            ref_rows, ref_raw = _replay(reference, spec["stream"])
            cand_rows, cand_raw = _replay(candidate, spec["stream"])
            notes: list[str] = []
            row_out: dict = {"kind": spec["kind"]}
            if spec.get("dump_goertzel"):
                goertzel_ok = ref_raw == cand_raw
                if ref_raw and cand_raw and len(ref_raw) == len(cand_raw):
                    goertzel_max_abs = max(abs(a - b) for a, b in zip(ref_raw, cand_raw))
                if not goertzel_ok:
                    notes.append("GOERTZEL_RAW_NOT_BIT_IDENTICAL")
            clicks = _parse_clicks(spec["stream"])
            n_frames = len(cand_rows)
            novelty_beats = _novelty_beat_times(clicks, n_frames)
            kind = spec["kind"]
            target = spec.get("target_bpm")

            def ticks(rows: list[dict], lo: int, hi: int) -> list[int]:
                return [r["ms"] for r in rows if r["beat_tick"] and lo <= r["ms"] < hi]

            if kind == "noise" or (spec.get("silence_is_flat") and kind == "silence_then_train"):
                prefix_end = spec.get("silence_end_ms", cand_rows[-1]["ms"] + 1)
                if kind == "noise":
                    prefix_end = cand_rows[-1]["ms"] + 1
                cand_prefix = [r for r in cand_rows if r["ms"] < prefix_end]
                ref_prefix = [r for r in ref_rows if r["ms"] < prefix_end]
                cand_false_lock = sum(r["locked"] for r in cand_prefix)
                ref_false_lock = sum(r["locked"] for r in ref_prefix)
                cand_false_tick = sum(r["beat_tick"] for r in cand_prefix)
                row_out["false_lock"] = cand_false_lock
                row_out["false_tick"] = cand_false_tick
                if cand_false_lock > 0:
                    notes.append(f"false_lock={cand_false_lock}")
                if cand_false_tick > 0:
                    notes.append(f"false_tick={cand_false_tick}")
                if cand_false_lock > ref_false_lock:
                    notes.append("false_lock_worse_than_spread")
                for prow in cand_prefix:
                    g = _product_gates(prow)
                    if g["prism_spawn"] or g["conf_full"] or g["director_trust"]:
                        notes.append(f"product_gate_on_noise/flat ms={prow['ms']} {g}")
                        break

            if kind == "silence_then_train" and not spec.get("silence_is_flat"):
                cand_prefix = [r for r in cand_rows if r["ms"] < spec["silence_end_ms"]]
                if any(r["locked"] or r["beat_tick"] for r in cand_prefix):
                    notes.append("silence_false_lock_or_tick")

            if kind == "release":
                ref_hold = sum(
                    1 for r in ref_rows if r["ms"] >= spec["silence_start_ms"] and r["locked"]
                )
                cand_hold = sum(
                    1 for r in cand_rows if r["ms"] >= spec["silence_start_ms"] and r["locked"]
                )
                ref_ticks = sum(
                    1 for r in ref_rows if r["ms"] >= spec["silence_start_ms"] and r["beat_tick"]
                )
                cand_ticks = sum(
                    1 for r in cand_rows if r["ms"] >= spec["silence_start_ms"] and r["beat_tick"]
                )
                row_out["silence_locked_frames"] = {"cand": cand_hold, "ref": ref_hold}
                row_out["silence_ticks"] = {"cand": cand_ticks, "ref": ref_ticks}
                if cand_hold > ref_hold:
                    notes.append("slower_lock_release_than_spread")
                if cand_ticks > ref_ticks:
                    notes.append("silence_ticks_worse_than_spread")

            if kind in ("stationary", "dropout", "jump", "silence_then_train", "release") and target is not None:
                ref_lock = _first_correct_lock(ref_rows, target)
                cand_lock = _first_correct_lock(cand_rows, target)
                row_out["cand_lock_ms"] = cand_lock
                row_out["ref_lock_ms"] = ref_lock
                if kind == "jump":
                    pre_bpm = spec.get("pre_bpm")
                    if pre_bpm is not None:
                        pre_end = spec["jump_ms"]
                        cand_pre = _first_correct_lock(
                            [r for r in cand_rows if r["ms"] < pre_end], pre_bpm
                        )
                        ref_pre = _first_correct_lock(
                            [r for r in ref_rows if r["ms"] < pre_end], pre_bpm
                        )
                        row_out["cand_pre_lock_ms"] = cand_pre
                        row_out["ref_pre_lock_ms"] = ref_pre
                        if ref_pre is not None and cand_pre is None:
                            notes.append(f"failed_pre_jump_lock target={pre_bpm}")
                        elif ref_pre is not None and cand_pre is not None and cand_pre > ref_pre:
                            notes.append(f"slower_pre_jump_lock cand={cand_pre} ref={ref_pre}")
                    post = [r for r in cand_rows if r["ms"] >= spec["jump_ms"]]
                    ref_post_lock = _first_correct_lock(
                        [r for r in ref_rows if r["ms"] >= spec["jump_ms"]], target
                    )
                    cand_post_lock = _first_correct_lock(post, target)
                    row_out["cand_reacquire_ms"] = cand_post_lock
                    row_out["ref_reacquire_ms"] = ref_post_lock
                    if cand_post_lock is None:
                        if ref_post_lock is None:
                            row_out["control_cannot_reacquire"] = True
                        else:
                            notes.append("failed_reacquire_after_jump")
                        settle_from = 10**9
                    else:
                        if ref_post_lock is not None and cand_post_lock > ref_post_lock:
                            notes.append(
                                f"slower_reacquire cand={cand_post_lock} ref={ref_post_lock}"
                            )
                        settle_from = cand_post_lock + 2000
                    trans_lo = spec["jump_ms"]
                    trans_hi = (cand_post_lock or spec["jump_ms"]) + 2000
                    cand_trans_ticks = sum(
                        1 for r in cand_rows if trans_lo <= r["ms"] < trans_hi and r["beat_tick"]
                    )
                    ref_trans_ticks = sum(
                        1 for r in ref_rows if trans_lo <= r["ms"] < trans_hi and r["beat_tick"]
                    )
                    row_out["transition_ticks"] = {
                        "cand": cand_trans_ticks,
                        "ref": ref_trans_ticks,
                    }
                    if cand_trans_ticks > ref_trans_ticks:
                        notes.append(
                            f"transition_false_beats cand={cand_trans_ticks} ref={ref_trans_ticks}"
                        )
                    settle_to = cand_rows[-1]["ms"] + 1
                else:
                    if cand_lock is None:
                        if ref_lock is None:
                            row_out["control_cannot_lock"] = True
                        else:
                            notes.append("never_locked_correct_bpm")
                        settle_from = 10**9
                    else:
                        if ref_lock is not None and cand_lock > ref_lock:
                            notes.append(f"slower_acquire cand={cand_lock} ref={ref_lock}")
                        settle_from = cand_lock + 2000
                    settle_to = spec["silence_start_ms"] if kind == "release" else cand_rows[-1]["ms"] + 1
                settled = [r for r in cand_rows if settle_from <= r["ms"] < settle_to]
                settled_ref = [r for r in ref_rows if settle_from <= r["ms"] < settle_to]
                edge_ms = 23
                if settled:
                    cand_wrong, cand_oct = _wrong_locked(settled, target)
                    ref_wrong, ref_oct = _wrong_locked(settled_ref, target)
                    row_out["wrong_bpm_frames"] = {"cand": cand_wrong, "ref": ref_wrong}
                    row_out["wrong_octave_frames"] = {"cand": cand_oct, "ref": ref_oct}
                    if cand_oct > ref_oct:
                        notes.append(f"wrong_octave_regression n={cand_oct} ref={ref_oct}")
                    if cand_wrong > ref_wrong:
                        notes.append(f"wrong_bpm_regression n={cand_wrong} ref={ref_wrong}")
                    cand_unlocks = _unlock_count(settled)
                    ref_unlocks = _unlock_count(settled_ref)
                    row_out["unlocks"] = {"cand": cand_unlocks, "ref": ref_unlocks}
                    if kind == "dropout":
                        if cand_unlocks > ref_unlocks:
                            notes.append(
                                f"dropout_unlocks_worse cand={cand_unlocks} ref={ref_unlocks}"
                            )
                    elif cand_unlocks > 0:
                        notes.append(f"unexpected_lock_releases={cand_unlocks}")
                    truth = [
                        t
                        for t in novelty_beats
                        if settle_from + edge_ms <= t < settle_to - edge_ms
                    ]
                    tick_win = ticks(cand_rows, settle_from + edge_ms, settle_to - edge_ms)
                    tick_ref = ticks(ref_rows, settle_from + edge_ms, settle_to - edge_ms)
                    counted = _sorted_beat_report(truth, tick_win)
                    counted_ref = _sorted_beat_report(truth, tick_ref)
                    row_out["beat_sorted"] = {
                        "cand": counted,
                        "ref": counted_ref,
                    }
                    cand_miss = counted["count_delta"]
                    ref_miss = counted_ref["count_delta"]
                    if cand_miss > ref_miss:
                        extra, missing = _unmatched(truth, tick_win, 80.0)
                        extra_ref, missing_ref = _unmatched(truth, tick_ref, 80.0)
                        row_out["unmatched_80ms"] = {
                            "cand_extra_ms": extra,
                            "cand_missing_ms": missing,
                            "ref_extra_ms": extra_ref,
                            "ref_missing_ms": missing_ref,
                        }
                        notes.append(
                            f"beat_count_worse_than_spread cand={counted} ref={counted_ref}"
                        )
                    if counted["count_delta"] == 0 and counted_ref["count_delta"] == 0:
                        cand_t = counted["max_err_us"]
                        ref_t = counted_ref["max_err_us"]
                        cand_med = counted["median_err_us"]
                        ref_med = counted_ref["median_err_us"]
                        if cand_t > AP_HOP_US:
                            if ref_t <= AP_HOP_US:
                                notes.append(
                                    f"beat_timing_gt_7500us cand={cand_t} ref={ref_t}"
                                )
                            elif cand_med > ref_med + 3.0 * AP_HOP_US:
                                notes.append(
                                    f"beat_timing_median_worse cand_med={cand_med} ref_med={ref_med}"
                                )
                            else:
                                row_out["timing_7500_unmet_by_control"] = True
            fixture_rows[name] = row_out
            if notes:
                failures[name] = notes

    control_gaps = {
        name: row
        for name, row in fixture_rows.items()
        if row.get("control_cannot_lock")
        or row.get("control_cannot_reacquire")
        or row.get("timing_7500_unmet_by_control")
    }

    receipt = {
        "lane": "G2_TEMPO_BEHAVIOURAL_EQUIVALENCE_V1",
        "verdict": "FAIL" if failures else "PASS",
        "goertzel_raw_bit_identical": goertzel_ok,
        "goertzel_max_abs_err": goertzel_max_abs,
        "failures": failures,
        "control_gaps": sorted(control_gaps),
        "fixtures": fixture_rows,
        "timing_oracle": (
            "Analytical AP clicks are mapped onto the peak-held novelty emit "
            "(frames 3,6,9,...) before the 7500 us bound is applied. The flywheel "
            "can only tick on emit frames; judging vs raw AP clicks would confuse "
            "decimation with tracker error."
        ),
        "B489_FLASH": "HOLD",
        "GATE3": "BLOCKED",
        "F887": "NO",
        "CROSS80": "HOLD",
        "ONSET": "HOLD",
        "MABUTRACE": "NOT_REQUIRED_FOR_G2_SERVICE_P99",
    }
    PACK.mkdir(parents=True, exist_ok=True)
    (PACK / "HOST_BEHAVIOURAL.json").write_text(
        json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    goertzel_receipt = {
        "lane": "G2_TEMPO_BEHAVIOURAL_EQUIVALENCE_V1",
        "subgate": "TEMPO_GOERTZEL_EXACT",
        "verdict": "PASS" if goertzel_ok else "FAIL",
        "bit_identical": goertzel_ok,
        "max_abs_err": goertzel_max_abs,
        "identity": (
            "k1_tempi[*].magnitude_raw after the same novelty stream, "
            "spread k1_compute_magnitude vs incremental shared-window, "
            "-ffp-contract=off"
        ),
        "B489_FLASH": "HOLD",
    }
    (PACK / "HOST_GOERTZEL.json").write_text(
        json.dumps(goertzel_receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    assert failures == {}, json.dumps(
        {"failures": failures, "goertzel": goertzel_ok}, indent=2, sort_keys=True
    )
    assert goertzel_ok is True


def test_production_does_not_enable_rolling_acf():
    hardware = (ROOT / "platformio.ini").read_text(encoding="utf-8")
    start = hardware.index("[env:k1_hardware]")
    end = hardware.find("\n[env:", start + 1)
    section = hardware[start:end]
    assert "K1_TEMPO_ACF_INCREMENTAL_V1=1" not in section
    assert "#define K1_TEMPO_ACF_INCREMENTAL_V1 0" in TEMPO_CPP.read_text(encoding="utf-8")
