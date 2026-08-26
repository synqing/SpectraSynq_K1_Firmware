#!/usr/bin/env python3
"""Offline colour-parity scorer for look-library rtrace dumps.

Scores:
  - Gold ΔG: green lift in gold-region pixels (R>G>B, R significant)
    between slot 0 (IDENTITY) and slot 1 (GOLD_LIFT / SHARED_1D_256)
  - Grey stability: slot 2 (TUNGSTEN) should desaturate; slot 1 shared-1D
    should not wash grey
  - Slot 1 vs slot 0 delta direction (positive ΔG = gold lift, negative = sink)

WS2812 dump format: rgb8hex (6 hex chars/LED, post-look+post-gamma u8)
WS2816 dump format: rgb16hex (12 hex chars/LED, R16BE G16BE B16BE,
                    post-look pre-HW-gamma u16 from Lever-2 wire)

Usage: python3 score_parity.py <dump_dir>
"""
from __future__ import annotations
import json, re, sys, pathlib
import numpy as np

BEGIN_RE = re.compile(r'^\[RTRACE-BEGIN\b(?P<body>[^\]]*)\]\s*$')
F_RE = re.compile(r'^F,(?P<idx>\d+),(?P<ms>\d+),(?P<mode>\d+),(?P<hex>[0-9a-f]+)\s*$')


def parse_dump(path: pathlib.Path):
    """Return list of (mode, np.array shape (px,3) uint) frames and metadata."""
    fmt = 'rgb8hex'
    frames = []
    with open(path, 'r', errors='replace') as fh:
        for line in fh:
            s = line.strip()
            bm = BEGIN_RE.match(s)
            if bm:
                body = bm.group('body')
                m = re.search(r'\bfmt=(\w+)', body)
                if m:
                    fmt = m.group(1)
                continue
            m = F_RE.match(s)
            if not m:
                continue
            hexs = m.group('hex')
            if fmt == 'rgb16hex':
                if len(hexs) == 0 or len(hexs) % 12 != 0:
                    continue
                raw = bytes.fromhex(hexs)
                px = np.frombuffer(raw, dtype='>u2').reshape(-1, 3).copy().astype(np.uint32)
            else:  # rgb8hex
                if len(hexs) == 0 or len(hexs) % 6 != 0:
                    continue
                raw = bytes.fromhex(hexs)
                px = np.frombuffer(raw, dtype='u1').reshape(-1, 3).copy().astype(np.uint32)
            frames.append({'mode': int(m.group('mode')), 'px': px})
    return fmt, frames


def gold_pixels(frames_px, fmt):
    """Return stacked gold-like pixels across all frames.

    Gold criterion: R > G > B, R > 10% scale, R/G > 1.2.
    (Covers the gold hue band in an HSV stim ramp.)
    """
    max_val = 65535 if fmt == 'rgb16hex' else 255
    thresh = max_val * 0.10
    all_r, all_g, all_b = [], [], []
    for f in frames_px:
        px = f['px']
        r, g, b = px[:, 0], px[:, 1], px[:, 2]
        mask = (r > g) & (g > b) & (r > thresh) & (r > g * 1.2)
        if mask.any():
            all_r.append(r[mask])
            all_g.append(g[mask])
            all_b.append(b[mask])
    if not all_r:
        return None, None, None
    return np.concatenate(all_r), np.concatenate(all_g), np.concatenate(all_b)


def grey_pixels(frames_px, fmt):
    """Return grey-ish pixels (R≈G≈B within 10% of max)."""
    max_val = 65535 if fmt == 'rgb16hex' else 255
    thresh = max_val * 0.05  # minimum brightness
    all_sat = []
    for f in frames_px:
        px = f['px']
        r, g, b = px[:, 0].astype(float), px[:, 1].astype(float), px[:, 2].astype(float)
        mx = np.maximum.reduce([r, g, b])
        mn = np.minimum.reduce([r, g, b])
        bright_mask = mx > thresh
        if not bright_mask.any():
            continue
        sat = (mx[bright_mask] - mn[bright_mask]) / (mx[bright_mask] + 1e-6)
        all_sat.append(sat)
    if not all_sat:
        return None
    return np.concatenate(all_sat)


def score_device(tag: str, slot_dumps: dict[int, pathlib.Path]) -> dict:
    """Score gold ΔG for one device. Returns metric dict."""
    parsed = {}
    for slot, path in slot_dumps.items():
        fmt, frames = parse_dump(path)
        parsed[slot] = {'fmt': fmt, 'frames': frames, 'path': str(path)}

    fmt = parsed[0]['fmt']
    max_val = 65535 if fmt == 'rgb16hex' else 255
    scale = max_val

    result = {
        'device': tag,
        'fmt': fmt,
        'scale': scale,
        'slot_frame_counts': {s: len(parsed[s]['frames']) for s in parsed},
    }

    # Gold ΔG: slot 1 vs slot 0
    r0, g0, b0 = gold_pixels(parsed[0]['frames'], fmt)
    r1, g1, b1 = gold_pixels(parsed[1]['frames'], fmt)

    if g0 is not None and g1 is not None:
        mean_g0 = float(np.mean(g0))
        mean_g1 = float(np.mean(g1))
        delta_g = mean_g1 - mean_g0
        delta_g_pct = delta_g / scale * 100.0
        result['gold_mean_g_slot0'] = round(mean_g0, 2)
        result['gold_mean_g_slot1'] = round(mean_g1, 2)
        result['gold_delta_g'] = round(delta_g, 2)
        result['gold_delta_g_pct'] = round(delta_g_pct, 2)
        result['gold_n_pixels_slot0'] = int(g0.size)
        result['gold_n_pixels_slot1'] = int(g1.size)
        result['gold_direction'] = 'LIFT' if delta_g > 0 else ('SINK' if delta_g < 0 else 'FLAT')
    else:
        result['gold_error'] = 'insufficient gold-region pixels'

    # Grey stability: how saturated are grey pixels in each slot?
    for slot in [1, 2]:
        sat = grey_pixels(parsed[slot]['frames'], fmt)
        if sat is not None:
            result[f'grey_mean_sat_slot{slot}'] = round(float(np.mean(sat)), 4)
        else:
            result[f'grey_mean_sat_slot{slot}'] = None

    # Also compare R/G ratio change in gold region (slot 0 vs slot 1)
    if g0 is not None and g1 is not None and r0 is not None and r1 is not None:
        rg_ratio_0 = float(np.mean(r0.astype(float) / (g0.astype(float) + 1)))
        rg_ratio_1 = float(np.mean(r1.astype(float) / (g1.astype(float) + 1)))
        result['gold_rg_ratio_slot0'] = round(rg_ratio_0, 3)
        result['gold_rg_ratio_slot1'] = round(rg_ratio_1, 3)
        result['gold_rg_delta'] = round(rg_ratio_1 - rg_ratio_0, 3)
        # Positive rg_delta means more orange (less green lift); negative = more gold (greener)
        result['gold_rg_direction'] = 'MORE_GOLDEN' if rg_ratio_1 < rg_ratio_0 else 'MORE_ORANGE'

    return result


def parity_verdict(rpl: dict, bench: dict) -> dict:
    """Cross-device parity assessment."""
    rpl_dir = rpl.get('gold_direction', 'UNKNOWN')
    bench_dir = bench.get('gold_direction', 'UNKNOWN')
    rpl_rg = rpl.get('gold_rg_direction', 'UNKNOWN')
    bench_rg = bench.get('gold_rg_direction', 'UNKNOWN')

    # JOB parity: both devices move G in the LIFT direction for gold
    both_lift = rpl_dir == 'LIFT' and bench_dir == 'LIFT'
    # FULL parity: both lift AND move toward more golden (lower R/G ratio)
    both_golden = rpl_rg == 'MORE_GOLDEN' and bench_rg == 'MORE_GOLDEN'

    if both_lift and both_golden:
        verdict = 'JOB_ONLY'
        reason = ('Both devices lift G for gold. Direction match (LIFT). '
                  'Cannot claim FULL parity — different LED types, hardware gamma, '
                  'and bit depth; dump values are not comparable across devices.')
    elif both_lift:
        verdict = 'JOB_ONLY'
        reason = ('Both devices lift G for gold (R/G ratio assessment differs). '
                  'Cannot claim FULL cross-device parity.')
    else:
        verdict = 'FAIL'
        reason = f'Direction mismatch: RPL={rpl_dir}, bench={bench_dir}. JOB parity not met.'

    return {
        'verdict': verdict,
        'reason': reason,
        'rpl_gold_direction': rpl_dir,
        'bench_gold_direction': bench_dir,
        'rpl_delta_g': rpl.get('gold_delta_g'),
        'rpl_delta_g_pct': rpl.get('gold_delta_g_pct'),
        'bench_delta_g': rpl.get('gold_delta_g'),
        'bench_delta_g_pct_actual': bench.get('gold_delta_g_pct'),
        'rpl_delta_g_pct_actual': rpl.get('gold_delta_g_pct'),
        'bench_delta_g_actual': bench.get('gold_delta_g'),
    }


def main():
    dump_dir = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else '.')

    rpl_slots = {
        0: dump_dir / 'rpl_slot0_dump.txt',
        1: dump_dir / 'rpl_slot1_dump.txt',
        2: dump_dir / 'rpl_slot2_dump.txt',
    }
    bench_slots = {
        0: dump_dir / 'bench_slot0_dump.txt',
        1: dump_dir / 'bench_slot1_dump.txt',
        2: dump_dir / 'bench_slot2_dump.txt',
    }

    # Check files exist
    for path in list(rpl_slots.values()) + list(bench_slots.values()):
        if not path.exists():
            print(f'ERROR: missing dump: {path}')
            sys.exit(1)

    print('Scoring RPL (WS2816, rgb16hex)...')
    rpl_score = score_device('RPL_9087A500_WS2816', rpl_slots)

    print('Scoring bench (WS2812, rgb8hex)...')
    bench_score = score_device('BENCH_B489A500_WS2812', bench_slots)

    parity = parity_verdict(rpl_score, bench_score)

    measured = {
        'generated': '2026-08-26',
        'investigation': 'look-parity-rtrace-20260826',
        'stim': 'HSV ramp hue 0-1 at sat=1.0 val=0.55',
        'rpl': rpl_score,
        'bench': bench_score,
        'parity': parity,
    }

    out_path = dump_dir / 'MEASURED.json'
    out_path.write_text(json.dumps(measured, indent=2) + '\n', encoding='utf-8')
    print(f'\nWrote {out_path}')

    print('\n=== SUMMARY ===')
    print(f'RPL  slot0→1 gold ΔG: {rpl_score.get("gold_delta_g", "N/A")} '
          f'({rpl_score.get("gold_delta_g_pct", "N/A")}% of u16 range), '
          f'direction={rpl_score.get("gold_direction", "?")}')
    print(f'Bench slot0→1 gold ΔG: {bench_score.get("gold_delta_g", "N/A")} '
          f'({bench_score.get("gold_delta_g_pct", "N/A")}% of u8 range), '
          f'direction={bench_score.get("gold_direction", "?")}')
    print(f'Parity verdict: {parity["verdict"]}')
    print(f'  {parity["reason"]}')

    return 0


if __name__ == '__main__':
    sys.exit(main())
