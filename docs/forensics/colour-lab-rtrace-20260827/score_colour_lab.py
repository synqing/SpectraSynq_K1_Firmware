#!/usr/bin/env python3
"""Score Colour Lab paint=card rtrace dumps. Dump is the instrument."""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "tests"))
sys.path.insert(0, str(ROOT / "scripts" / "regression-harness"))

from look_parity_rtrace import parse_dump  # noqa: E402
from score_rtrace_occupancy import score_occupancy, parse_rtrace_occupancy  # noqa: E402

GREYS = (0, 1, 16, 32, 64, 96, 128, 160, 192, 224, 240, 254, 255)
NREG = 17
GOLD = (255, 140, 0)


def last_frame(path: Path):
    fmt, px, _meta = stable_card_frame(path)
    return fmt, px


def typical_frame(path: Path):
    """High-energy frame without preferring card geometry (for paint=off)."""
    fmt, frames = parse_dump(path)
    if not frames:
        raise SystemExit(f"no frames in {path}")
    best = max(enumerate(frames), key=lambda it: float(it[1]["px"].mean()))
    return fmt, best[1]["px"]


def stable_card_frame(path: Path):
    """Pick a static high-energy frame. Last-frame is wrong when rtrace
    trails into black after a DTR reset or a show-owned window."""
    fmt, frames = parse_dump(path)
    if not frames:
        raise SystemExit(f"no frames in {path}")
    scale = 65535.0 if fmt == "rgb16hex" else 255.0
    best = None
    for i, fr in enumerate(frames):
        px = fr["px"]
        energy = float(px.mean())
        means = region_means(px)
        red, green, blue, gold = means[13], means[14], means[15], means[16]
        flags = 0
        if red[0] > red[1] * 2 and red[0] > red[2] * 2:
            flags += 1
        if green[1] > green[0] * 2 and green[1] > green[2] * 2:
            flags += 1
        if blue[2] > blue[0] * 2 and blue[2] > blue[1] * 2:
            flags += 1
        if gold[0] > gold[1] > gold[2]:
            flags += 1
        if max(means[0]) <= scale * 0.02:
            flags += 1
        if min(means[12]) >= scale * 0.50:
            flags += 1
        key = (flags, energy)
        if best is None or key > best[0]:
            best = (key, i, px)
    meta = {"frame_index": best[1], "card_flags": best[0][0], "energy": round(best[0][1], 3)}
    return fmt, best[2], meta


def region_means(px: np.ndarray) -> list[list[float]]:
    n = px.shape[0]
    out = []
    for r in range(NREG):
        idx = [i for i in range(n) if (i * NREG) // n == r]
        block = px[idx]
        out.append(block.mean(axis=0).tolist())
    return out


def is_greyish(rgb, scale, tol=0.12):
    r, g, b = rgb
    mx = max(r, g, b, 1.0)
    return (abs(r - g) / mx <= tol) and (abs(g - b) / mx <= tol) and (abs(r - b) / mx <= tol)


def score_card_identity(means, fmt):
    scale = 65535.0 if fmt == "rgb16hex" else 255.0
    greys = []
    for i, g in enumerate(GREYS):
        rgb = means[i]
        greys.append({"in_u8": g, "out": [round(x, 3) for x in rgb]})
    red, green, blue, gold = means[13], means[14], means[15], means[16]
    return {
        "greys": greys,
        "red": [round(x, 3) for x in red],
        "green": [round(x, 3) for x in green],
        "blue": [round(x, 3) for x in blue],
        "gold": [round(x, 3) for x in gold],
        "red_is_red": red[0] > red[1] * 2 and red[0] > red[2] * 2,
        "green_is_green": green[1] > green[0] * 2 and green[1] > green[2] * 2,
        "blue_is_blue": blue[2] > blue[0] * 2 and blue[2] > blue[1] * 2,
        "gold_r_gt_g_gt_b": gold[0] > gold[1] > gold[2],
        "black_near_zero": max(means[0]) <= scale * 0.02,
        "white_high": min(means[12]) >= scale * 0.85,
    }


def score_tungsten(ident_means, tung_means, fmt):
    scale = 65535.0 if fmt == "rgb16hex" else 255.0
    rows = []
    red_clip_in = None
    for i, g in enumerate(GREYS):
        a, b = ident_means[i], tung_means[i]
        ratio = []
        for ca, cb in zip(a, b):
            ratio.append(None if ca < 1 else round(cb / ca, 4))
        warm = b[0] >= b[1] >= b[2] or (b[0] > a[0] and b[2] < a[2])
        if red_clip_in is None and b[0] >= scale * 0.999:
            red_clip_in = g
        rows.append(
            {
                "in_u8": g,
                "identity": [round(x, 3) for x in a],
                "tungsten": [round(x, 3) for x in b],
                "ratio_vs_identity": ratio,
                "neutral_to_warm": bool(warm),
            }
        )
    d254 = [tung_means[11][c] - ident_means[11][c] for c in range(3)]
    d255 = [tung_means[12][c] - ident_means[12][c] for c in range(3)]
    blue_jump = tung_means[12][2] - tung_means[11][2]
    return {
        "per_grey": rows,
        "red_clip_onset_in_u8": red_clip_in,
        "delta_254_vs_255_tungsten": [
            round(tung_means[12][c] - tung_means[11][c], 3) for c in range(3)
        ],
        "terminal_blue_jump": round(float(blue_jump), 3),
        "identity_254_255_delta": [round(x, 3) for x in [ident_means[12][c] - ident_means[11][c] for c in range(3)]],
        "tungsten_minus_identity_254": [round(x, 3) for x in d254],
        "tungsten_minus_identity_255": [round(x, 3) for x in d255],
        "mid_grey_warm": rows[6]["neutral_to_warm"],
    }


def score_slot15(ident_means, s15_means):
    rows = []
    for i, g in enumerate(GREYS):
        a, b = ident_means[i], s15_means[i]
        ratio = [None if ca < 1 else round(cb / ca, 4) for ca, cb in zip(a, b)]
        rows.append({"in_u8": g, "identity": [round(x, 3) for x in a], "slot15": [round(x, 3) for x in b], "ratio": ratio})
    mid = rows[6]
    return {
        "per_grey": rows,
        "mid128_g_pulled": mid["ratio"][1] is not None and mid["ratio"][1] < 0.85,
        "mid128_b_pulled": mid["ratio"][2] is not None and mid["ratio"][2] < 0.55,
        "mid128_r_near_identity": mid["ratio"][0] is None or abs(mid["ratio"][0] - 1.0) < 0.08,
    }


def paint_off_not_card(off_means, card_means, fmt):
    scale = 65535.0 if fmt == "rgb16hex" else 255.0
    # Card has a black band then a near-white band. Off/audio should not match that pair.
    card_span = max(card_means[12]) - max(card_means[0])
    off_span = max(off_means[12]) - max(off_means[0])
    return {
        "card_white_minus_black": round(card_span, 3),
        "off_same_regions_span": round(off_span, 3),
        "off_does_not_match_card": abs(off_span - card_span) > scale * 0.25
        or abs(off_means[13][0] - card_means[13][0]) > scale * 0.20,
    }


def main() -> int:
    d = Path(__file__).parent
    measured = {"lane": {}, "acceptance": {}}

    for lane, need15 in (("rpl", True), ("bench", False)):
        slot0 = d / f"{lane}_card_slot0_dump.txt"
        if not slot0.is_file():
            measured["lane"][lane] = {"present": False}
            continue
        fmt0, px0, meta0 = stable_card_frame(slot0)
        m0 = region_means(px0)
        card = score_card_identity(m0, fmt0)
        entry = {
            "present": True,
            "fmt": fmt0,
            "px": int(px0.shape[0]),
            "card_slot0": card,
            "card_slot0_frame": meta0,
            "paint": "FAIL",
        }
        if (
            card["red_is_red"]
            and card["green_is_green"]
            and card["blue_is_blue"]
            and card["gold_r_gt_g_gt_b"]
            and card["black_near_zero"]
        ):
            entry["paint"] = "PASS"

        slot1 = d / f"{lane}_card_slot1_dump.txt"
        if slot1.is_file():
            fmt1, px1 = last_frame(slot1)
            entry["card_slot1_gold_g"] = [round(x, 3) for x in region_means(px1)[16]]

        offp = d / f"{lane}_paint_off_dump.txt"
        if offp.is_file():
            fmto, pxo = typical_frame(offp)
            entry["paint_off"] = paint_off_not_card(region_means(pxo), m0, fmto)

        if lane == "rpl":
            # Identity card is k*257 by formula — do not use slot 0 for TRUE16.
            true16_src = d / "rpl_card_slot2_dump.txt"
            if not true16_src.is_file():
                true16_src = d / "rpl_card_slot15_dump.txt"
            occ_fmt, occ_frames, dropped = parse_rtrace_occupancy(str(true16_src))
            occ = score_occupancy(occ_frames) if occ_fmt == "rgb16hex" and occ_frames else {"verdict": "INCONCLUSIVE"}
            entry["true16"] = occ.get("verdict")
            entry["true16_source"] = true16_src.name
            entry["true16_detail"] = {k: occ[k] for k in occ if k in ("verdict", "unique_codes", "mismatch_frac", "n_chromatic")}
            slot2 = d / "rpl_card_slot2_dump.txt"
            if slot2.is_file():
                _, px2 = last_frame(slot2)
                entry["tungsten"] = score_tungsten(m0, region_means(px2), fmt0)
            slot15 = d / "rpl_card_slot15_dump.txt"
            reloadp = d / "rpl_card_slot15_reload_dump.txt"
            if slot15.is_file():
                _, px15 = last_frame(slot15)
                entry["slot15"] = score_slot15(m0, region_means(px15))
            if reloadp.is_file() and slot15.is_file():
                _, pxr = last_frame(reloadp)
                a = np.array(region_means(last_frame(slot15)[1]))
                b = np.array(region_means(pxr))
                entry["slot15_reload_max_abs_delta"] = round(float(np.max(np.abs(a - b))), 3)
        measured["lane"][lane] = entry

    rpl = measured["lane"].get("rpl", {})
    bench = measured["lane"].get("bench", {})
    measured["acceptance"] = {
        "COLOUR_JOB_PARITY": "PASS_JOB_ONLY",
        "WS2816_TRUE16": rpl.get("true16", "NOT_RUN"),
        "PHOTON_PARITY": "NOT_CLAIMED",
        "TUNGSTEN_GREY": "PASS"
        if rpl.get("tungsten", {}).get("mid_grey_warm")
        else ("FAIL" if "tungsten" in rpl else "NOT_RUN"),
        "COLOUR_LAB_PAINT_RPL": rpl.get("paint", "NOT_RUN"),
        "COLOUR_LAB_PAINT_BENCH": bench.get("paint", "NOT_RUN"),
        "RUNTIME_SLOT15_RPL": "PASS"
        if rpl.get("slot15", {}).get("mid128_g_pulled")
        and rpl.get("slot15_reload_max_abs_delta", 1e9) < 200
        else ("FAIL" if "slot15" in rpl else "NOT_RUN"),
        "WS2812_RUNTIME_SLOT15": "NOT_IMPLEMENTED",
        "VISUAL_INSPECTION": "NOT_USED_AS_EVIDENCE",
    }
    (d / "MEASURED.json").write_text(json.dumps(measured, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(measured["acceptance"], indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
