"""Held dashboard values must not inflate n or move percentiles / correlation."""

from __future__ import annotations

import math

from scorer.fresh_stats import mask_bit, pearson, summarise


def test_held_repeats_do_not_inflate_n_or_percentiles():
    # One real bpm=120 then nine held 120s (FPS/poll rows).
    pairs = [(120.0, True)] + [(120.0, False)] * 9
    naive = summarise((v, True) for v, _ in pairs)
    fresh = summarise(pairs)
    assert naive["n"] == 10
    assert fresh["n"] == 1
    assert fresh["p50"] == 120.0
    assert fresh["p95"] == 120.0
    assert fresh["p99"] == 120.0


def test_held_tail_cannot_pull_p95_down():
    real = [(10.0, True), (20.0, True), (90.0, True)]
    held = real + [(10.0, False)] * 100
    s_real = summarise(real)
    s_held = summarise(held)
    assert s_real["n"] == s_held["n"] == 3
    assert s_real["p95"] == s_held["p95"]
    naive = summarise((v, True) for v, _ in held)
    assert naive["n"] == 103
    assert naive["p95"] < s_real["p95"]


def test_correlation_ignores_held_y():
    x = [(1.0, True), (2.0, True), (3.0, True)]
    y_fresh = [(1.0, True), (2.0, True), (3.0, True)]
    y_held = [(1.0, True), (2.0, False), (3.0, True)]
    r_all = pearson(x, y_fresh)
    r_mask = pearson(x, y_held)
    assert abs(r_all - 1.0) < 1e-9
    # only two joint-fresh points (1 and 3) still correlate
    assert r_mask == r_mask and abs(r_mask - 1.0) < 1e-9
    y_noise_held = [(1.0, True)] + [(0.0, False)] * 2
    r_bad_if_counted = pearson([(1.0, True), (2.0, True), (3.0, True)], [(1.0, True), (0.0, True), (0.0, True)])
    r_ok = pearson([(1.0, True), (2.0, True), (3.0, True)], y_noise_held)
    assert r_bad_if_counted != r_bad_if_counted or abs(r_bad_if_counted) < 0.99
    assert math.isnan(r_ok)  # one joint-fresh point


def test_update_mask_slot1_is_bit0():
    assert mask_bit(0b1, 1) is True
    assert mask_bit(0b1, 2) is False
    assert mask_bit(1 << 15, 16) is True
    assert mask_bit(1 << 19, 20) is True
